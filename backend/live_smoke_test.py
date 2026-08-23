"""Live end-to-end smoke test: boots a real uvicorn server and exercises HTTP + WebSocket.

Complements test_backend_integration.py (which calls route functions directly). This one
proves the app actually serves over the network from whichever directory it was launched
in. Uses only stdlib urllib plus `websockets`/`uvicorn`, which are already backend deps -
no pytest/httpx required.

Usage:  python live_smoke_test.py <launch_dir_label> [port]
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

LABEL = sys.argv[1] if len(sys.argv) > 1 else "unknown"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8021
BASE = f"http://127.0.0.1:{PORT}"

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

EXPECTED_MODEL_VERSION = "final-logreg-v1"
EXPECTED_FEATURE_VERSION = "stage4-v2"

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, msg: str = "") -> None:
    results.append((name, ok, msg))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f": {msg}" if msg and not ok else ""))


def get_json(path: str):
    with urllib.request.urlopen(BASE + path, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode())


def post_json(path: str, body: dict):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode())


def wait_for_server(proc: subprocess.Popen, timeout=90.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(BASE + "/api/model/info", timeout=3):
                return True
        except Exception:
            time.sleep(0.6)
    return False


async def ws_probe():
    """Collect telemetry packets until we see one carrying a vitals payload."""
    import websockets
    out = {"packets": 0, "vitals_packet": None, "waveform_beds": None}
    async with websockets.connect(f"ws://127.0.0.1:{PORT}/ws/telemetry") as ws:
        deadline = time.time() + 25
        while time.time() < deadline:
            packet = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            out["packets"] += 1
            if out["waveform_beds"] is None:
                out["waveform_beds"] = sorted(packet.get("waveforms", {}))
            if packet.get("vitals"):
                out["vitals_packet"] = packet
                break
    return out


def main() -> int:
    print(f"\n=== LIVE SMOKE TEST (launched from: {LABEL}, cwd={os.getcwd()}) ===")
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1",
         "--port", str(PORT), "--log-level", "warning"],
        cwd=BACKEND_DIR, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        if not wait_for_server(proc):
            out = ""
            if proc.poll() is not None:
                out = proc.stdout.read() if proc.stdout else ""
            record("server boots", False, f"did not start. output:\n{out[-2000:]}")
            return 1
        record("server boots and serves /api/model/info", True)

        # --- model identity over HTTP ---
        status, info = get_json("/api/model/info")
        record("GET /api/model/info -> 200", status == 200, str(status))
        record(f"model_version == {EXPECTED_MODEL_VERSION}",
               info.get("model_version") == EXPECTED_MODEL_VERSION, str(info.get("model_version")))
        record(f"feature_version == {EXPECTED_FEATURE_VERSION}",
               info.get("feature_version") == EXPECTED_FEATURE_VERSION, str(info.get("feature_version")))
        record("threshold == 0.3606", round(info.get("threshold", 0), 4) == 0.3606,
               str(info.get("threshold")))
        record("features_total == 52", info.get("features_total") == 52,
               str(info.get("features_total")))

        # --- roster ---
        status, patients = get_json("/api/patients")
        record("GET /api/patients -> 200 with 4 beds",
               status == 200 and len(patients) == 4, f"{status}, n={len(patients)}")
        p0 = patients[0]
        record("legacy patient keys intact",
               all(k in p0 for k in ("id", "name", "age", "gender", "admission_type",
                                     "doctor", "vitals", "analysis")), sorted(p0))
        record("legacy vitals keys intact",
               all(k in p0["vitals"] for k in ("heart_rate", "spo2", "sys_bp", "dia_bp",
                                               "map", "resp_rate", "temp", "condition")),
               sorted(p0["vitals"]))
        a0 = p0["analysis"]
        record("analysis carries final-model fields",
               a0.get("model_version") == EXPECTED_MODEL_VERSION
               and a0.get("feature_version") == EXPECTED_FEATURE_VERSION
               and 0.0 <= a0.get("probability", -1) <= 1.0
               and a0.get("risk_level") in ("LOW", "MODERATE", "HIGH"),
               json.dumps({k: a0.get(k) for k in
                           ("model_version", "probability", "risk_level")}))
        record("no legacy old-model fields leak through",
               not any(k in a0 for k in ("is_anomaly", "detected_flags", "risk_score",
                                         "sepsis_probability")), sorted(a0))
        record("analysis is labelled non-clinical",
               a0.get("clinical_use") is False and "NOT a clinical" in a0.get("disclaimer", ""))

        # --- detail + explanations ---
        status, detail = get_json("/api/patients/BED-102")
        exps = detail.get("analysis", {}).get("explanations", [])
        record("GET /api/patients/BED-102 -> 200", status == 200, str(status))
        record("detail returns explanations", len(exps) > 0, f"n={len(exps)}")
        record("explanation shape correct",
               bool(exps) and set(exps[0]) == {"feature", "raw_value", "was_imputed",
                                               "log_odds_contribution", "direction"},
               sorted(exps[0]) if exps else "none")

        try:
            get_json("/api/patients/BED-999")
            record("unknown bed -> 404", False, "no error raised")
        except urllib.error.HTTPError as exc:
            record("unknown bed -> 404", exc.code == 404, str(exc.code))

        # --- history isolation over HTTP ---
        _, before = get_json("/api/patients/BED-101")
        _, other_before = get_json("/api/patients/BED-103")
        h101_before = before["analysis"]["history_hours"]
        h103_before = other_before["analysis"]["history_hours"]
        for _ in range(3):
            post_json("/api/simulate", {"bed_id": "BED-101", "condition": "Hypoxia"})
        _, after = get_json("/api/patients/BED-101")
        _, other_after = get_json("/api/patients/BED-103")
        record("simulate advances only the target bed's history",
               after["analysis"]["history_hours"] == h101_before + 3
               and other_after["analysis"]["history_hours"] == h103_before,
               f"101:{h101_before}->{after['analysis']['history_hours']} "
               f"103:{h103_before}->{other_after['analysis']['history_hours']}")

        status, sim = post_json("/api/simulate", {"bed_id": "BED-103", "condition": "Fever"})
        record("POST /api/simulate -> 200 with ML analysis",
               status == 200 and sim["analysis"]["model_version"] == EXPECTED_MODEL_VERSION,
               str(status))
        record("simulate applied the condition", sim["new_condition"] == "Fever")

        # --- alerts ---
        status, alerts = get_json("/api/alerts")
        record("GET /api/alerts -> 200 list", status == 200 and isinstance(alerts, list),
               f"{status}, n={len(alerts)}")
        if alerts:
            ok = all(a.get("model_version") == EXPECTED_MODEL_VERSION for a in alerts)
            record("alerts carry final-model provenance", ok)
            status, ack = post_json("/api/alerts/acknowledge",
                                    {"alert_id": alerts[0]["alert_id"]})
            record("POST /api/alerts/acknowledge -> 200",
                   status == 200 and ack["status"] == "acknowledged", str(status))
        else:
            record("alerts list empty (no HIGH-band events this run)", True)
        try:
            post_json("/api/alerts/acknowledge", {"alert_id": "NOPE"})
            record("unknown alert id -> 404", False, "no error raised")
        except urllib.error.HTTPError as exc:
            record("unknown alert id -> 404", exc.code == 404, str(exc.code))

        # --- websocket ---
        probe = asyncio.run(ws_probe())
        record("WS /ws/telemetry streams packets", probe["packets"] > 0,
               f"n={probe['packets']}")
        record("WS waveforms cover all 4 beds",
               probe["waveform_beds"] == ["BED-101", "BED-102", "BED-103", "BED-104"],
               str(probe["waveform_beds"]))
        vp = probe["vitals_packet"]
        record("WS delivers a vitals tick", vp is not None)
        if vp:
            entry = vp["vitals"]["BED-101"]
            record("WS packet shape {t, waveforms, vitals}",
                   set(vp) == {"t", "waveforms", "vitals"}, sorted(vp))
            record("WS vitals entry has vitals + analysis",
                   set(entry) == {"vitals", "analysis"}, sorted(entry))
            record("WS analysis is from the final model",
                   entry["analysis"]["model_version"] == EXPECTED_MODEL_VERSION
                   and entry["analysis"]["feature_version"] == EXPECTED_FEATURE_VERSION,
                   entry["analysis"].get("model_version"))
            record("WS risk level valid",
                   entry["analysis"]["risk_level"] in ("LOW", "MODERATE", "HIGH"),
                   entry["analysis"].get("risk_level"))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()

    passed = sum(1 for _, ok, _ in results if ok)
    failed = [(n, m) for n, ok, m in results if not ok]
    print("\n" + "=" * 72)
    print(f"LIVE SMOKE ({LABEL}): {passed} passed, {len(failed)} failed")
    for name, msg in failed:
        print(f"  FAILED: {name} -> {msg}")
    print("=" * 72)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
