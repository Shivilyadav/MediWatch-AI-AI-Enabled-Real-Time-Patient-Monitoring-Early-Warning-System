"""Standalone backend <-> FINAL-ML integration tests.

Deliberately dependency-free (stdlib + the backend's own deps), mirroring the style of
ml_pipeline/test_inference.py. FastAPI's TestClient needs `httpx`, which is not a project
dependency, so these tests call the route functions and the ML bridge directly instead of
going over HTTP. The WebSocket handler's per-tick payload builder is exercised through the
same helper the socket loop uses.

Run from the project root:   python backend/test_backend_integration.py
Run from backend/:           python test_backend_integration.py
Both must pass - that is itself the import-robustness test (plan section 6).
"""

from __future__ import annotations

import asyncio
import inspect
import os
import sys

# Make the backend package importable no matter which directory we were launched from.
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

import main
import ml_inference
from ml_inference import MIN_HOURS_FOR_FULL_TEMPORAL, PatientHistoryStore

EXPECTED_MODEL_VERSION = "final-logreg-v1"
EXPECTED_FEATURE_VERSION = "stage4-v2"
EXPECTED_THRESHOLD = 0.36061602358147954
EXPECTED_MODERATE_CUT = 0.36061602358147954
EXPECTED_HIGH_CUT = 0.7542800224324719
EXPECTED_FEATURE_COUNT = 52

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str):
    """Decorator that records pass/fail without aborting the whole run."""
    def wrap(fn):
        try:
            fn()
            RESULTS.append((name, True, ""))
            print(f"  PASS  {name}")
        except AssertionError as exc:
            RESULTS.append((name, False, str(exc)))
            print(f"  FAIL  {name}: {exc}")
        except Exception as exc:  # noqa: BLE001 - report unexpected errors as failures
            RESULTS.append((name, False, f"{type(exc).__name__}: {exc}"))
            print(f"  ERROR {name}: {type(exc).__name__}: {exc}")
        return fn
    return wrap


def sample_vitals(hr=95, spo2=94, sys_bp=112, dia_bp=70, resp=21, temp=38.1):
    """A generator-shaped snapshot (generator key names, including `condition`)."""
    return {
        "heart_rate": hr, "spo2": spo2, "sys_bp": sys_bp, "dia_bp": dia_bp,
        "map": int(round(dia_bp + (sys_bp - dia_bp) / 3.0)),
        "resp_rate": resp, "temp": temp, "condition": "Normal",
    }


# ======================================================================================
print("\n[1] Artifact + model identity")
# ======================================================================================

@check("final_model_v1.pkl loads")
def t_artifact_loads():
    model = ml_inference.get_model()
    assert model is not None
    assert os.path.exists(str(ml_inference.DEFAULT_ARTIFACT)), "artifact path missing"


@check("model loaded once (singleton)")
def t_singleton():
    assert ml_inference.get_model() is ml_inference.get_model()
    assert main.FINAL_MODEL is ml_inference.get_model(), "main.py holds a different instance"


@check("model_version == final-logreg-v1")
def t_model_version():
    got = ml_inference.get_model().model_version
    assert got == EXPECTED_MODEL_VERSION, f"got {got!r}"


@check("feature_version == stage4-v2")
def t_feature_version():
    got = ml_inference.get_model().feature_version
    assert got == EXPECTED_FEATURE_VERSION, f"got {got!r}"


@check("threshold unchanged (0.3606...)")
def t_threshold():
    got = ml_inference.get_model().threshold
    assert abs(got - EXPECTED_THRESHOLD) < 1e-12, f"got {got!r}"
    assert round(got, 4) == 0.3606, f"got {round(got, 4)}"


@check("risk bands unchanged")
def t_bands():
    model = ml_inference.get_model()
    assert abs(model.moderate_cut - EXPECTED_MODERATE_CUT) < 1e-12, model.moderate_cut
    assert abs(model.high_cut - EXPECTED_HIGH_CUT) < 1e-12, model.high_cut


@check("52-feature contract")
def t_feature_count():
    assert len(ml_inference.get_model().features) == EXPECTED_FEATURE_COUNT


@check("old model.pkl is never loaded by the backend scoring path")
def t_no_old_model():
    # The bridge and main must not reference the old detector at all.
    assert not hasattr(main, "anomaly_detector"), "main still holds anomaly_detector"
    assert not hasattr(main, "PatientAnomalyDetector"), "main still imports the old detector"
    src = inspect.getsource(ml_inference)
    for banned in ("PatientAnomalyDetector(", "model.pkl'", 'model.pkl"'):
        assert banned not in src, f"ml_inference references {banned}"
    # And the loaded artifact really is the final one.
    assert str(ml_inference.DEFAULT_ARTIFACT).endswith("final_model_v1.pkl")


@check("backend does not recreate the 52 features itself")
def t_no_feature_duplication():
    # Positive proof: the 52-vector is produced by the SHARED stage4-v2 helper. Patch it
    # and confirm the backend's scoring path routes through it exactly once per predict.
    import inference
    original = inference.transform_vitals_to_features
    calls = {"n": 0}

    def counting(readings):
        calls["n"] += 1
        return original(readings)

    inference.transform_vitals_to_features = counting
    try:
        ml_inference.reset_history("BED-FEAT")
        ml_inference.evaluate("BED-FEAT", sample_vitals(), explain=False)
    finally:
        inference.transform_vitals_to_features = original
    assert calls["n"] == 1, f"shared feature helper called {calls['n']} times, expected 1"

    # Negative proof: the backend defines no feature engineering of its own and never
    # imports the feature modules directly (checked against code, not comments).
    for module in (ml_inference, main):
        names = set(dir(module))
        for banned in ("FEATURE_NAMES", "CORE_SOURCES", "engineer_patient_rows_v2",
                       "feature_engineering", "feature_engineering_v2", "pd", "pandas"):
            assert banned not in names, f"{module.__name__} exposes {banned}"


# ======================================================================================
print("\n[2] Vital-name adaptation")
# ======================================================================================

@check("generator keys map to inference keys")
def t_adapt():
    got = ml_inference.adapt_snapshot(sample_vitals())
    assert set(got) == {"heart_rate", "spo2", "systolic_bp", "diastolic_bp",
                        "map", "respiratory_rate", "temperature"}, sorted(got)
    assert "condition" not in got, "condition must not be fed to the model"


@check("adapter preserves values verbatim")
def t_adapt_values():
    raw = sample_vitals(hr=101, spo2=88, sys_bp=95, dia_bp=55, resp=27, temp=39.2)
    got = ml_inference.adapt_snapshot(raw)
    assert got["heart_rate"] == 101 and got["spo2"] == 88
    assert got["systolic_bp"] == 95 and got["diastolic_bp"] == 55
    assert got["respiratory_rate"] == 27 and got["temperature"] == 39.2


@check("unknown generator key is rejected loudly")
def t_adapt_unknown():
    try:
        ml_inference.adapt_snapshot({"heart_rate": 80, "bogus_vital": 1})
    except ValueError:
        return
    raise AssertionError("expected ValueError for an unmapped vital")


# ======================================================================================
print("\n[3] Patient history: isolation, chronology, no future data, bounds")
# ======================================================================================

@check("histories are isolated between beds")
def t_isolation():
    store = PatientHistoryStore()
    store.append("BED-101", {"heart_rate": 60})
    store.append("BED-101", {"heart_rate": 61})
    store.append("BED-102", {"heart_rate": 130})
    a, b = store.window("BED-101"), store.window("BED-102")
    assert len(a) == 2 and len(b) == 1, (len(a), len(b))
    assert [r["heart_rate"] for r in a] == [60, 61]
    assert [r["heart_rate"] for r in b] == [130]
    assert all(r["heart_rate"] != 130 for r in a), "BED-102 data leaked into BED-101"


@check("live backend beds keep separate histories")
def t_isolation_live():
    main.seed_patient_histories()
    ml_inference.evaluate("BED-101", sample_vitals(hr=55), explain=False)
    ml_inference.evaluate("BED-101", sample_vitals(hr=56), explain=False)
    h101 = ml_inference.HISTORY.hours("BED-101")
    h102 = ml_inference.HISTORY.hours("BED-102")
    assert h101 == main.WARMUP_HOURS + 2, h101
    assert h102 == main.WARMUP_HOURS, h102
    tail = ml_inference.HISTORY.window("BED-101")[-2:]
    assert [r["heart_rate"] for r in tail] == [55, 56]


@check("history is chronological and append-only")
def t_chronological():
    store = PatientHistoryStore()
    for hr in (70, 71, 72, 73):
        store.append("BED-X", {"heart_rate": hr})
    assert [r["heart_rate"] for r in store.window("BED-X")] == [70, 71, 72, 73]


@check("no future observations are visible to a prediction")
def t_no_future():
    store = PatientHistoryStore()
    seen = []
    for hr in (80, 81, 82):
        window = store.append("BED-Y", {"heart_rate": hr})
        seen.append([r["heart_rate"] for r in window])
    # Each window contains only values appended up to and including that step.
    assert seen == [[80], [80, 81], [80, 81, 82]], seen


@check("stored history is immutable from the outside")
def t_history_copy():
    store = PatientHistoryStore()
    reading = {"heart_rate": 90}
    store.append("BED-Z", reading)
    reading["heart_rate"] = 999                 # mutate caller's dict
    store.window("BED-Z")[0]["heart_rate"] = 1  # mutate returned copy
    assert store.window("BED-Z")[0]["heart_rate"] == 90, "history was mutated externally"


@check("history window is bounded")
def t_bounded():
    store = PatientHistoryStore(max_hours=6)
    for hr in range(100, 120):
        store.append("BED-B", {"heart_rate": hr})
    window = store.window("BED-B")
    assert len(window) == 6, len(window)
    assert window[-1]["heart_rate"] == 119, window[-1]
    assert window[0]["heart_rate"] == 114, window[0]  # oldest evicted


@check("too-small history bound is rejected")
def t_bad_bound():
    try:
        PatientHistoryStore(max_hours=2)
    except ValueError:
        return
    raise AssertionError("expected ValueError for max_hours < min temporal window")


# ======================================================================================
print("\n[4] ML prediction + risk output")
# ======================================================================================

@check("prediction returns the full schema")
def t_predict_schema():
    ml_inference.reset_history("BED-T")
    out = ml_inference.evaluate("BED-T", sample_vitals())
    for key in ("model_version", "feature_version", "probability", "risk_level", "alert",
                "threshold", "risk_bands", "hours_supplied", "features_present",
                "features_total", "disclaimer", "bed_id", "history_hours",
                "history_sufficient", "alert_actionable", "explanations"):
        assert key in out, f"missing {key}"
    assert out["model_version"] == EXPECTED_MODEL_VERSION
    assert out["feature_version"] == EXPECTED_FEATURE_VERSION
    assert out["features_total"] == EXPECTED_FEATURE_COUNT
    assert out["bed_id"] == "BED-T"


@check("probability is a valid, non-fabricated float")
def t_probability():
    ml_inference.reset_history("BED-T")
    out = ml_inference.evaluate("BED-T", sample_vitals(), explain=False)
    p = out["probability"]
    assert isinstance(p, float) and 0.0 <= p <= 1.0, p
    # Must equal the model's own output for the same window (no post-hoc adjustment).
    window = ml_inference.HISTORY.window("BED-T")
    assert abs(ml_inference.get_model().predict(window)["probability"] - p) < 1e-12


@check("risk banding matches the artifact bands")
def t_banding():
    model = ml_inference.get_model()
    assert model.risk_level(0.0) == "LOW"
    assert model.risk_level(EXPECTED_MODERATE_CUT - 1e-9) == "LOW"
    assert model.risk_level(EXPECTED_MODERATE_CUT) == "MODERATE"
    assert model.risk_level(EXPECTED_HIGH_CUT - 1e-9) == "MODERATE"
    assert model.risk_level(EXPECTED_HIGH_CUT) == "HIGH"
    assert model.risk_level(1.0) == "HIGH"


@check("alert flag follows the unchanged threshold")
def t_alert_flag():
    ml_inference.reset_history("BED-T")
    out = ml_inference.evaluate("BED-T", sample_vitals(), explain=False)
    assert out["alert"] == (out["probability"] >= EXPECTED_THRESHOLD)
    assert out["alert_actionable"] == (out["risk_level"] == "HIGH")


@check("explanations are returned with the expected shape")
def t_explanations():
    ml_inference.reset_history("BED-T")
    out = ml_inference.evaluate("BED-T", sample_vitals(), explain=True, top_k=5)
    exps = out["explanations"]
    assert isinstance(exps, list) and len(exps) == 5, len(exps)
    for e in exps:
        assert set(e) == {"feature", "raw_value", "was_imputed",
                          "log_odds_contribution", "direction"}, sorted(e)
        assert e["feature"] in ml_inference.get_model().features
        assert e["direction"] in ("increases risk", "decreases risk")


@check("history accrual populates more real features")
def t_history_improves_features():
    ml_inference.reset_history("BED-H")
    first = ml_inference.evaluate("BED-H", sample_vitals(hr=90), explain=False)
    for hr in (92, 94, 96, 98):
        last = ml_inference.evaluate("BED-H", sample_vitals(hr=hr), explain=False)
    assert first["history_hours"] == 1 and first["history_sufficient"] is False
    assert last["history_hours"] == MIN_HOURS_FOR_FULL_TEMPORAL
    assert last["history_sufficient"] is True
    assert last["features_present"] > first["features_present"], \
        (first["features_present"], last["features_present"])


@check("read-only scoring does not advance the virtual clock")
def t_commit_false():
    ml_inference.reset_history("BED-C")
    ml_inference.evaluate("BED-C", sample_vitals(), commit=True, explain=False)
    before = ml_inference.HISTORY.hours("BED-C")
    out = ml_inference.evaluate("BED-C", sample_vitals(), commit=False, explain=False)
    assert ml_inference.HISTORY.hours("BED-C") == before, "commit=False mutated history"
    assert out["history_hours"] == before + 1, "uncommitted reading was not scored"


@check("multiple patients score concurrently without cross-talk")
def t_multi_patient():
    ml_inference.reset_history()
    beds = ["BED-101", "BED-102", "BED-103", "BED-104"]
    for step in range(3):
        for i, bed in enumerate(beds):
            ml_inference.evaluate(bed, sample_vitals(hr=70 + i * 10 + step), explain=False)
    for i, bed in enumerate(beds):
        window = ml_inference.HISTORY.window(bed)
        assert len(window) == 3, (bed, len(window))
        assert [r["heart_rate"] for r in window] == [70 + i * 10 + s for s in range(3)]


@check("output is labelled research-only, not clinical")
def t_disclaimer():
    ml_inference.reset_history("BED-T")
    out = ml_inference.evaluate("BED-T", sample_vitals(), explain=False)
    assert out["clinical_use"] is False
    assert "NOT a clinical" in out["disclaimer"]


# ======================================================================================
print("\n[5] REST endpoints")
# ======================================================================================

@check("GET /api/model/info reports the final artifact")
def t_ep_model_info():
    info = main.get_model_info()
    assert info["model_version"] == EXPECTED_MODEL_VERSION
    assert info["feature_version"] == EXPECTED_FEATURE_VERSION
    assert abs(info["threshold"] - EXPECTED_THRESHOLD) < 1e-12
    assert info["features_total"] == EXPECTED_FEATURE_COUNT


@check("GET /api/patients keeps its shape and gains ML fields")
def t_ep_patients():
    main.seed_patient_histories()
    rows = main.get_patients()
    assert len(rows) == 4, len(rows)
    for row in rows:
        for key in ("id", "name", "age", "gender", "admission_type", "doctor",
                    "vitals", "analysis"):
            assert key in row, f"missing legacy key {key}"
        # legacy vitals payload untouched
        for vk in ("heart_rate", "spo2", "sys_bp", "dia_bp", "map", "resp_rate",
                   "temp", "condition"):
            assert vk in row["vitals"], f"missing vital {vk}"
        a = row["analysis"]
        assert a["model_version"] == EXPECTED_MODEL_VERSION
        assert a["risk_level"] in ("LOW", "MODERATE", "HIGH")
        assert 0.0 <= a["probability"] <= 1.0


@check("GET /api/patients is side-effect free")
def t_ep_patients_readonly():
    main.seed_patient_histories()
    before = {p["id"]: ml_inference.HISTORY.hours(p["id"]) for p in main.PATIENTS_DB}
    main.get_patients()
    main.get_patients()
    after = {p["id"]: ml_inference.HISTORY.hours(p["id"]) for p in main.PATIENTS_DB}
    assert before == after, (before, after)


@check("GET /api/patients/{bed_id} returns detail + explanations")
def t_ep_patient_detail():
    main.seed_patient_histories()
    row = main.get_patient("bed-102")  # case-insensitive lookup preserved
    assert row["id"] == "BED-102"
    assert row["analysis"]["model_version"] == EXPECTED_MODEL_VERSION
    assert len(row["analysis"]["explanations"]) > 0


@check("GET /api/patients/{bed_id} still 404s for unknown beds")
def t_ep_patient_404():
    from fastapi import HTTPException
    try:
        main.get_patient("BED-999")
    except HTTPException as exc:
        assert exc.status_code == 404, exc.status_code
        return
    raise AssertionError("expected HTTPException(404)")


@check("POST /api/simulate scores and advances that bed only")
def t_ep_simulate():
    main.seed_patient_histories()
    before_101 = ml_inference.HISTORY.hours("BED-101")
    before_102 = ml_inference.HISTORY.hours("BED-102")
    out = main.simulate_condition(main.SimulationRequest(bed_id="BED-101",
                                                        condition="Hypoxia"))
    assert out["status"] == "success"
    assert out["new_condition"] == "Hypoxia"
    assert out["analysis"]["model_version"] == EXPECTED_MODEL_VERSION
    assert ml_inference.HISTORY.hours("BED-101") == before_101 + 1
    assert ml_inference.HISTORY.hours("BED-102") == before_102, "simulate touched another bed"
    assert main.PATIENTS_DB[0]["generator"].condition == "Hypoxia"


@check("POST /api/simulate 404s for unknown beds")
def t_ep_simulate_404():
    from fastapi import HTTPException
    try:
        main.simulate_condition(main.SimulationRequest(bed_id="BED-999", condition="Fever"))
    except HTTPException as exc:
        assert exc.status_code == 404, exc.status_code
        return
    raise AssertionError("expected HTTPException(404)")


@check("alerts are generated from the final-model path")
def t_ep_alerts_generated():
    main.ALERTS_HISTORY.clear()
    main.seed_patient_histories()
    # Drive an aggressive deterioration to try to reach the HIGH band.
    for bed in ("BED-101", "BED-102", "BED-103", "BED-104"):
        for cond in ("Hypoxia", "Tachycardia", "Fever", "Hypoxia"):
            main.simulate_condition(main.SimulationRequest(bed_id=bed, condition=cond))
    alerts = main.get_alerts()
    assert isinstance(alerts, list)
    assert len(alerts) <= 50, "alert log must stay capped at 50"
    for alert in alerts:
        for key in ("alert_id", "bed_id", "patient_name", "timestamp", "risk_level",
                    "flags", "vitals", "acknowledged"):
            assert key in alert, f"alert missing legacy key {key}"
        assert alert["model_version"] == EXPECTED_MODEL_VERSION
        assert alert["risk_level"] == "HIGH", alert["risk_level"]
        assert alert["acknowledged"] is False
    print(f"        (generated {len(alerts)} alert(s) at the HIGH band)")


@check("POST /api/alerts/acknowledge works, unknown id 404s")
def t_ep_ack():
    from fastapi import HTTPException
    main.ALERTS_HISTORY.clear()
    main.ALERTS_HISTORY.insert(0, {"alert_id": "ALT-TEST", "acknowledged": False})
    out = main.acknowledge_alert(main.AlertAckRequest(alert_id="ALT-TEST"))
    assert out["status"] == "acknowledged"
    assert main.ALERTS_HISTORY[0]["acknowledged"] is True
    try:
        main.acknowledge_alert(main.AlertAckRequest(alert_id="NOPE"))
    except HTTPException as exc:
        assert exc.status_code == 404
        return
    raise AssertionError("expected HTTPException(404)")


# ======================================================================================
print("\n[6] WebSocket telemetry")
# ======================================================================================

@check("telemetry vitals payload has waveform-compatible shape + ML analysis")
def t_ws_payload():
    main.seed_patient_histories()
    payload = main.build_vitals_payload(commit_hour=False)
    assert set(payload) == {p["id"] for p in main.PATIENTS_DB}, sorted(payload)
    for bed_id, entry in payload.items():
        assert set(entry) == {"vitals", "analysis"}, sorted(entry)
        assert entry["analysis"]["bed_id"] == bed_id
        assert entry["analysis"]["model_version"] == EXPECTED_MODEL_VERSION
        assert entry["analysis"]["risk_level"] in ("LOW", "MODERATE", "HIGH")


@check("telemetry commits one virtual hour only on a boundary")
def t_ws_cadence():
    main.seed_patient_histories()
    before = ml_inference.HISTORY.hours("BED-101")
    main.build_vitals_payload(commit_hour=False)
    main.build_vitals_payload(commit_hour=False)
    assert ml_inference.HISTORY.hours("BED-101") == before, "non-boundary tick committed"
    main.build_vitals_payload(commit_hour=True)
    assert ml_inference.HISTORY.hours("BED-101") == before + 1, "boundary tick did not commit"
    assert main.VIRTUAL_HOUR_SECONDS > 1.0, "virtual hour must be slower than the 1Hz tick"


@check("waveform generation still works at 60Hz shape")
def t_ws_waveforms():
    gen = main.PATIENTS_DB[0]["generator"]
    for i in range(5):
        t = i * 0.016
        assert isinstance(gen.generate_ecg_sample(t), float)
        assert isinstance(gen.generate_ppg_sample(t), float)


@check("telemetry packet is JSON-serialisable end to end")
def t_ws_packet_json():
    import json
    main.seed_patient_histories()
    packet = {
        "t": 1.0,
        "waveforms": {p["id"]: {"ecg": round(p["generator"].generate_ecg_sample(1.0), 4),
                                "ppg": round(p["generator"].generate_ppg_sample(1.0), 4)}
                      for p in main.PATIENTS_DB},
        "vitals": main.build_vitals_payload(commit_hour=False),
    }
    text = json.dumps(packet)
    assert '"waveforms"' in text and '"vitals"' in text
    assert EXPECTED_MODEL_VERSION in text


@check("websocket handler accepts, streams and cleans up on disconnect")
def t_ws_handler():
    from fastapi import WebSocketDisconnect

    class FakeWebSocket:
        """Minimal duck-typed WebSocket: yields a few packets then disconnects."""
        def __init__(self, packet_budget=3):
            self.accepted = False
            self.packets = []
            self.budget = packet_budget

        async def accept(self):
            self.accepted = True

        async def send_json(self, packet):
            self.packets.append(packet)
            if len(self.packets) >= self.budget:
                raise WebSocketDisconnect(code=1000)

    ws = FakeWebSocket()
    before = len(main.ACTIVE_WEBSOCKETS)
    asyncio.run(main.telemetry_websocket(ws))
    assert ws.accepted, "handler did not accept the socket"
    assert len(ws.packets) == 3, len(ws.packets)
    first = ws.packets[0]
    assert set(first) == {"t", "waveforms", "vitals"}, sorted(first)
    assert set(first["waveforms"]) == {p["id"] for p in main.PATIENTS_DB}
    assert len(main.ACTIVE_WEBSOCKETS) == before, "socket not removed on disconnect"


# ======================================================================================
print("\n[7] Import robustness + legacy behaviour")
# ======================================================================================

@check("ml_pipeline paths resolved from __file__, not the CWD")
def t_paths():
    assert os.path.isdir(ml_inference.ML_PIPELINE_DIR), ml_inference.ML_PIPELINE_DIR
    assert ml_inference.ML_PIPELINE_DIR in sys.path
    assert ml_inference.PROJECT_ROOT in sys.path
    assert os.path.isabs(ml_inference.ML_PIPELINE_DIR)


@check("importing the backend does not load the old pickle")
def t_no_pickle_load():
    # ml_pipeline/__init__ imports the old detector CLASS, but model.pkl is only read in
    # PatientAnomalyDetector.__init__ - which the backend never calls.
    import ml_pipeline
    assert hasattr(ml_pipeline, "PatientAnomalyDetector")
    assert "anomaly_detector" not in dir(main)


@check("legacy roster and generators are intact")
def t_legacy_roster():
    assert [p["id"] for p in main.PATIENTS_DB] == ["BED-101", "BED-102", "BED-103", "BED-104"]
    assert main.PATIENTS_DB[0]["name"] == "Sarah Connor"
    for p in main.PATIENTS_DB:
        assert isinstance(p["generator"], main.VitalSignalGenerator)


@check("app routes are all still registered")
def t_routes():
    paths = {getattr(r, "path", None) for r in main.app.routes}
    for expected in ("/api/patients", "/api/patients/{bed_id}", "/api/simulate",
                     "/api/alerts", "/api/alerts/acknowledge", "/ws/telemetry",
                     "/api/model/info"):
        assert expected in paths, f"route {expected} missing"


# ======================================================================================
passed = sum(1 for _, ok, _ in RESULTS if ok)
failed = [(n, m) for n, ok, m in RESULTS if not ok]
print("\n" + "=" * 72)
print(f"BACKEND INTEGRATION: {passed} passed, {len(failed)} failed "
      f"(launched from {os.getcwd()})")
if failed:
    for name, msg in failed:
        print(f"  FAILED: {name} -> {msg}")
print("=" * 72)
sys.exit(1 if failed else 0)
