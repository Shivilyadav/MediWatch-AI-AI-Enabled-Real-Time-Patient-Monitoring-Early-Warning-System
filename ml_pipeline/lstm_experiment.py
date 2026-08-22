"""Phase 3: leakage-safe LSTM for the 1-6h prospective sepsis target.

Purpose
-------
Test whether recurrent temporal modelling of the raw hourly vitals improves on the
tabular models (LogReg / RF / XGBoost). This is a *candidate* model; selection happens
in Phase 5 on validation performance. The test set is NOT touched here.

Leakage safety (by construction)
--------------------------------
* Decision rows and labels come from the APPROVED target only
  (`approved_target`): label 1 on rows f..f+5, 0 on rows < f, and rows >= f+6 are
  EXCLUDED. Because every decision row t satisfies t < f+6, a trailing sequence ending
  at t can never contain an onset/post-onset row -> no future/onset leakage.
* Per-timestep inputs are only the raw causal vitals (7 core incl. MAP fallback + 3
  derived), reconstructed with the SHARED Stage-4 functions (`current_core_values`,
  `safe_divide`) -- no manual duplication of feature maths, no rolling/hand-crafted
  temporal features (the LSTM learns temporal structure itself).
* Forward-fill and the missingness mask use only values at or before t. Standardisation
  statistics are computed on TRAIN observed values only.
* Stage-2 seed-42 patient splits are read from disk and never regenerated.
* The epoch is selected on VALIDATION AUPRC and the decision threshold on VALIDATION
  (same `choose_threshold` as Stage 5). No test-set tuning.

Outputs
-------
* ml_pipeline/saved_models/lstm_sepsis.pt   (weights + preprocessing config + threshold)
* ml_pipeline/results/lstm_validation.json  (config, per-epoch validation curve, metrics)
"""

from __future__ import annotations

import copy
import json
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn
from sklearn.metrics import average_precision_score, roc_auc_score

from feature_engineering import (
    read_psv,
    split_patient_ids,
    first_positive_index,
    approved_target,
    current_core_values,
    safe_divide,
)
from train_stage5 import metrics, choose_threshold, SEED

PIPELINE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PIPELINE_ROOT.parent
DATA_ROOT = PIPELINE_ROOT / "data" / "raw" / "physionet"
SPLITS_ROOT = PIPELINE_ROOT / "data" / "splits"
RESULTS = PIPELINE_ROOT / "results"
MODELS = PIPELINE_ROOT / "saved_models"

# 10 raw causal per-timestep inputs (order is the model's input contract).
FEATURE_ORDER = [
    "heart_rate", "spo2", "respiratory_rate", "temperature",
    "systolic_bp", "diastolic_bp", "map",
    "pulse_pressure", "shock_index", "spo2_rr_ratio",
]
N_FEATURES = len(FEATURE_ORDER)
SEQ_LEN = 24            # trailing lookback in hours (>= it is truncated to the last 24)
HIDDEN = 32
DROPOUT = 0.3
EPOCHS = 20
BATCH = 256
LR = 1e-3
WEIGHT_DECAY = 1e-5
FEATURE_VERSION = "raw-core-derived-seq-v1"


def raw_vitals_row(core_row) -> list[float | None]:
    """The 10 causal inputs for one timestep, using the shared Stage-4 definitions."""
    hr, spo2, rr = core_row["heart_rate"], core_row["spo2"], core_row["respiratory_rate"]
    sbp, dbp = core_row["systolic_bp"], core_row["diastolic_bp"]
    pulse_pressure = sbp - dbp if sbp is not None and dbp is not None else None
    return [
        hr, spo2, rr, core_row["temperature"], sbp, dbp, core_row["map"],
        pulse_pressure, safe_divide(hr, sbp), safe_divide(spo2, rr),
    ]


def causal_series(raw_rows):
    """Return (ffilled[T,10], mask[T,10]) using only values at or before each row t."""
    length = len(raw_rows)
    values = np.full((length, N_FEATURES), np.nan, dtype=float)
    for t, row in enumerate(raw_rows):
        for j, value in enumerate(raw_vitals_row(current_core_values(row))):
            if value is not None:
                values[t, j] = value
    ffilled = values.copy()
    mask = (~np.isnan(values)).astype(np.float32)
    last = np.full(N_FEATURES, np.nan)
    for t in range(length):
        observed = ~np.isnan(values[t])
        last[observed] = values[t, observed]
        ffilled[t] = last
    return ffilled, mask


def build_examples(split_name: str):
    """Build causal trailing sequences for every decision row in a split.

    Returns windows (list of [win,10] ffilled arrays with NaN for never-observed),
    masks (list of [win,10]), integer labels, meta (pid,t), and observed-value
    sum/sumsq/count per feature (used ONLY for train standardisation).
    """
    patient_ids = split_patient_ids(SPLITS_ROOT / f"{split_name}_patients.txt")
    windows, masks, labels, meta = [], [], [], []
    obs_sum = np.zeros(N_FEATURES)
    obs_sumsq = np.zeros(N_FEATURES)
    obs_count = np.zeros(N_FEATURES)
    for patient_id in patient_ids:
        raw_rows = read_psv(DATA_ROOT / f"{patient_id}.psv")
        first_positive = first_positive_index(raw_rows)
        ffilled, mask = causal_series(raw_rows)
        observed_values = np.where(mask > 0, ffilled, np.nan)  # observed-at-t only
        obs_sum += np.nansum(observed_values, axis=0)
        obs_sumsq += np.nansum(observed_values ** 2, axis=0)
        obs_count += np.sum(mask > 0, axis=0)
        for t in range(len(raw_rows)):
            target = approved_target(first_positive, t)
            if target is None:
                continue
            start = max(0, t - SEQ_LEN + 1)
            windows.append(ffilled[start:t + 1].copy())
            masks.append(mask[start:t + 1].copy())
            labels.append(int(target))
            meta.append((patient_id, t))
    stats = {"sum": obs_sum, "sumsq": obs_sumsq, "count": obs_count}
    return windows, masks, np.array(labels, dtype=int), meta, stats


def standardization(stats):
    count = np.maximum(stats["count"], 1)
    mean = stats["sum"] / count
    var = np.maximum(stats["sumsq"] / count - mean ** 2, 0.0)
    std = np.sqrt(var)
    std[std < 1e-8] = 1.0
    return mean.astype(np.float32), std.astype(np.float32)


def to_tensors(windows, masks, labels, mean, std):
    """Right-pad to SEQ_LEN; channels = [z-scored ffilled (NaN->0), mask] = 20 dims."""
    n = len(windows)
    features = np.zeros((n, SEQ_LEN, 2 * N_FEATURES), dtype=np.float32)
    lengths = np.zeros(n, dtype=np.int64)
    for i, (window, mask) in enumerate(zip(windows, masks)):
        width = window.shape[0]
        z = (window - mean) / std
        z = np.where(np.isnan(z), 0.0, z).astype(np.float32)
        features[i, :width, :N_FEATURES] = z
        features[i, :width, N_FEATURES:] = mask
        lengths[i] = width
    return (
        torch.from_numpy(features),
        torch.from_numpy(lengths),
        torch.from_numpy(labels.astype(np.float32)),
    )


class SepsisLSTM(nn.Module):
    def __init__(self, n_in=2 * N_FEATURES, hidden=HIDDEN, dropout=DROPOUT):
        super().__init__()
        self.lstm = nn.LSTM(n_in, hidden, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(hidden, 1)

    def forward(self, x, lengths):
        packed = nn.utils.rnn.pack_padded_sequence(
            x, lengths.cpu(), batch_first=True, enforce_sorted=False
        )
        _, (h_n, _) = self.lstm(packed)
        return self.head(self.dropout(h_n[-1])).squeeze(1)


def predict_probs(model, features, lengths):
    model.eval()
    outputs = []
    with torch.no_grad():
        for b in range(0, len(features), BATCH):
            logits = model(features[b:b + BATCH], lengths[b:b + BATCH])
            outputs.append(torch.sigmoid(logits))
    return torch.cat(outputs).numpy()


def main():
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    torch.set_num_threads(4)
    RESULTS.mkdir(exist_ok=True)
    MODELS.mkdir(exist_ok=True)

    train_windows, train_masks, train_y, _, train_stats = build_examples("train")
    val_windows, val_masks, val_y, _, _ = build_examples("validation")
    mean, std = standardization(train_stats)

    Xtr, Ltr, ytr = to_tensors(train_windows, train_masks, train_y, mean, std)
    Xva, Lva, _ = to_tensors(val_windows, val_masks, val_y, mean, std)
    n_train = len(ytr)
    n_pos = int(train_y.sum())
    pos_weight = float((n_train - n_pos) / n_pos)

    print(f"train sequences={n_train} positives={n_pos} pos_weight={pos_weight:.4f}")
    print(f"validation sequences={len(val_y)} positives={int(val_y.sum())}")
    print(f"max seq len(cap)={SEQ_LEN} input_channels={2 * N_FEATURES}")

    model = SepsisLSTM()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([pos_weight], dtype=torch.float32))
    generator = torch.Generator().manual_seed(SEED)

    best = {"auprc": -1.0, "epoch": -1, "state": None}
    curve = []
    start_time = time.perf_counter()
    for epoch in range(1, EPOCHS + 1):
        model.train()
        permutation = torch.randperm(n_train, generator=generator)
        epoch_loss = 0.0
        for b in range(0, n_train, BATCH):
            idx = permutation[b:b + BATCH]
            optimizer.zero_grad()
            logits = model(Xtr[idx], Ltr[idx])
            loss = loss_fn(logits, ytr[idx])
            loss.backward()
            optimizer.step()
            epoch_loss += float(loss) * len(idx)
        val_prob = predict_probs(model, Xva, Lva)
        val_auprc = float(average_precision_score(val_y, val_prob))
        val_auroc = float(roc_auc_score(val_y, val_prob))
        curve.append({"epoch": epoch, "train_loss": round(epoch_loss / n_train, 6),
                      "val_auprc": round(val_auprc, 6), "val_auroc": round(val_auroc, 6)})
        print(f"epoch {epoch:2d} train_loss={epoch_loss / n_train:.4f} "
              f"val_auprc={val_auprc:.4f} val_auroc={val_auroc:.4f}")
        if val_auprc > best["auprc"]:
            best = {"auprc": val_auprc, "epoch": epoch, "state": copy.deepcopy(model.state_dict())}
    train_seconds = time.perf_counter() - start_time

    model.load_state_dict(best["state"])
    val_prob = predict_probs(model, Xva, Lva)
    threshold, val_metrics, meets = choose_threshold(val_y, val_prob)

    bundle = {
        "state_dict": best["state"],
        "architecture": {"type": "LSTM", "input_channels": 2 * N_FEATURES, "hidden": HIDDEN,
                         "layers": 1, "dropout": DROPOUT, "head": "Linear(hidden,1)+sigmoid"},
        "feature_order": FEATURE_ORDER,
        "seq_len": SEQ_LEN,
        "standardization": {"mean": mean.tolist(), "std": std.tolist()},
        "channel_layout": "[z-scored ffilled value (10), observed mask (10)]",
        "threshold": threshold,
        "pos_weight": round(pos_weight, 6),
        "feature_version": FEATURE_VERSION,
        "seed": SEED,
        "best_epoch": best["epoch"],
        "epochs_trained": EPOCHS,
        "framework": "pytorch",
        "torch_version": torch.__version__,
    }
    torch.save(bundle, MODELS / "lstm_sepsis.pt")

    report = {
        "model": "lstm",
        "feature_version": FEATURE_VERSION,
        "leakage_safe": True,
        "seed": SEED,
        "architecture": bundle["architecture"],
        "sequence": {"lookback_hours": SEQ_LEN, "channels": 2 * N_FEATURES,
                     "per_timestep_inputs": FEATURE_ORDER,
                     "imputation": "causal forward-fill + missingness mask; z-scored on train-observed values"},
        "training": {"epochs": EPOCHS, "batch_size": BATCH, "lr": LR, "weight_decay": WEIGHT_DECAY,
                     "pos_weight": round(pos_weight, 6), "optimizer": "Adam",
                     "loss": "BCEWithLogits(pos_weight)", "train_seconds": round(train_seconds, 3),
                     "epoch_selected_on": "validation AUPRC", "best_epoch": best["epoch"]},
        "counts": {"train_sequences": n_train, "train_positives": n_pos,
                   "validation_sequences": int(len(val_y)), "validation_positives": int(val_y.sum())},
        "validation_curve": curve,
        "threshold": threshold,
        "threshold_sensitivity_constraint_met": meets,
        "validation_metrics": val_metrics,
    }
    (RESULTS / "lstm_validation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"\nbest epoch={best['epoch']} threshold={threshold:.4f} meets_sens_constraint={meets}")
    print("validation:", {k: val_metrics[k] for k in ("auroc", "auprc", "sensitivity", "specificity", "precision", "f1")})
    print("saved", MODELS / "lstm_sepsis.pt")
    print("wrote", RESULTS / "lstm_validation.json")


if __name__ == "__main__":
    main()
