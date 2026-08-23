# MediWatch AI — Stage 3 Target Definition and Temporal Label Analysis

**Scope:** analysis only. No label column, model, backend, frontend, `model.py`, or `model.pkl` was changed.

## Dataset temporal resolution

The 1,000 PSV records contain 38,890 rows. Each row is one hour of ICU data: within every patient file, `ICULOS` increases by exactly one at every observed row transition (37,890/37,890 transitions). Records can begin after ICU hour 1, so `ICULOS` is the appropriate time coordinate rather than assuming row zero is ICU admission.

Official PhysioNet Challenge documentation states that predictions are made for each hourly time window using current and past—not future—data, and that training labels are shifted six hours ahead to support early prediction. The challenge defines clinical onset separately using Sepsis-3 criteria; it is not provided as a separate PSV column. [PhysioNet Challenge 2019 documentation](https://physionet.org/content/challenge-2019/1.0.0/).

## Observed label behavior

There are 71 positive patients and 674 positive rows. For all 71 positive records, `SepsisLabel=1` forms one contiguous, terminal run:

- 62 records contain an observed `0 → 1` transition; 9 begin with `SepsisLabel=1`.
- Positive runs contain 6–10 readings (median 10).
- First positive row index ranges from 0 to 265 (median 39).
- Time from first positive label to record end ranges from 5 to 9 hours (median 9).
- There are 4,029 observed negative rows before the first positive row across positive patients.
- 62/71 records have at least one pre-first-positive observation; 56/71 have at least six.

This behavior matches the documented six-hour label shift. It does **not** establish that a `1` at a row is the exact clinical onset: the first positive label is the available *six-hours-before-onset proxy* under the documented convention.

## Positive-record statistics

`P-001` through `P-071` are anonymized, deterministic labels for the positive PSV records sorted by source path. `first/last row` are zero-based row indices; `pre-1` is the count of negative rows before the first positive; `first→end` is elapsed hours because the data are hourly.

| Record | First row | Last row | Positive rows | Pre-1 | Total rows | First→end (h) | First/last ICULOS |
|---|---:|---:|---:|---:|---:|---:|---:|
| P-001 | 248 | 257 | 10 | 248 | 258 | 9 | 249/258 |
| P-002 | 24 | 33 | 10 | 24 | 34 | 9 | 26/35 |
| P-003 | 5 | 14 | 10 | 5 | 15 | 9 | 6/15 |
| P-004 | 125 | 133 | 9 | 125 | 134 | 8 | 126/134 |
| P-005 | 9 | 18 | 10 | 9 | 19 | 9 | 14/23 |
| P-006 | 21 | 30 | 10 | 21 | 31 | 9 | 22/31 |
| P-007 | 3 | 12 | 10 | 3 | 13 | 9 | 6/15 |
| P-008 | 63 | 72 | 10 | 63 | 73 | 9 | 64/73 |
| P-009 | 15 | 24 | 10 | 15 | 25 | 9 | 18/27 |
| P-010 | 0 | 8 | 9 | 0 | 9 | 8 | 1/9 |
| P-011 | 0 | 7 | 8 | 0 | 8 | 7 | 1/8 |
| P-012 | 4 | 13 | 10 | 4 | 14 | 9 | 5/14 |
| P-013 | 19 | 27 | 9 | 19 | 28 | 8 | 21/29 |
| P-014 | 94 | 103 | 10 | 94 | 104 | 9 | 95/104 |
| P-015 | 51 | 60 | 10 | 51 | 61 | 9 | 52/61 |
| P-016 | 13 | 22 | 10 | 13 | 23 | 9 | 14/23 |
| P-017 | 59 | 68 | 10 | 59 | 69 | 9 | 61/70 |
| P-018 | 87 | 96 | 10 | 87 | 97 | 9 | 89/98 |
| P-019 | 55 | 64 | 10 | 55 | 65 | 9 | 56/65 |
| P-020 | 75 | 83 | 9 | 75 | 84 | 8 | 76/84 |
| P-021 | 71 | 80 | 10 | 71 | 81 | 9 | 73/82 |
| P-022 | 13 | 22 | 10 | 13 | 23 | 9 | 15/24 |
| P-023 | 0 | 7 | 8 | 0 | 8 | 7 | 2/9 |
| P-024 | 9 | 17 | 9 | 9 | 18 | 8 | 10/18 |
| P-025 | 0 | 8 | 9 | 0 | 9 | 8 | 1/9 |
| P-026 | 52 | 61 | 10 | 52 | 62 | 9 | 55/64 |
| P-027 | 90 | 99 | 10 | 90 | 100 | 9 | 91/100 |
| P-028 | 32 | 40 | 9 | 32 | 41 | 8 | 34/42 |
| P-029 | 84 | 93 | 10 | 84 | 94 | 9 | 85/94 |
| P-030 | 88 | 97 | 10 | 88 | 98 | 9 | 90/99 |
| P-031 | 54 | 63 | 10 | 54 | 64 | 9 | 55/64 |
| P-032 | 55 | 63 | 9 | 55 | 64 | 8 | 56/64 |
| P-033 | 2 | 11 | 10 | 2 | 12 | 9 | 3/12 |
| P-034 | 137 | 146 | 10 | 137 | 147 | 9 | 138/147 |
| P-035 | 34 | 43 | 10 | 34 | 44 | 9 | 35/44 |
| P-036 | 2 | 10 | 9 | 2 | 11 | 8 | 3/11 |
| P-037 | 139 | 147 | 9 | 139 | 148 | 8 | 141/149 |
| P-038 | 28 | 37 | 10 | 28 | 38 | 9 | 35/44 |
| P-039 | 49 | 57 | 9 | 49 | 58 | 8 | 51/59 |
| P-040 | 1 | 10 | 10 | 1 | 11 | 9 | 2/11 |
| P-041 | 204 | 213 | 10 | 204 | 214 | 9 | 205/214 |
| P-042 | 0 | 7 | 8 | 0 | 8 | 7 | 1/8 |
| P-043 | 40 | 49 | 10 | 40 | 50 | 9 | 43/52 |
| P-044 | 83 | 91 | 9 | 83 | 92 | 8 | 84/92 |
| P-045 | 19 | 28 | 10 | 19 | 29 | 9 | 20/29 |
| P-046 | 80 | 89 | 10 | 80 | 90 | 9 | 81/90 |
| P-047 | 265 | 270 | 6 | 265 | 271 | 5 | 266/271 |
| P-048 | 26 | 35 | 10 | 26 | 36 | 9 | 27/36 |
| P-049 | 78 | 87 | 10 | 78 | 88 | 9 | 79/88 |
| P-050 | 0 | 7 | 8 | 0 | 8 | 7 | 1/8 |
| P-051 | 94 | 103 | 10 | 94 | 104 | 9 | 95/104 |
| P-052 | 25 | 34 | 10 | 25 | 35 | 9 | 26/35 |
| P-053 | 18 | 26 | 9 | 18 | 27 | 8 | 19/27 |
| P-054 | 29 | 38 | 10 | 29 | 39 | 9 | 30/39 |
| P-055 | 52 | 60 | 9 | 52 | 61 | 8 | 53/61 |
| P-056 | 0 | 8 | 9 | 0 | 9 | 8 | 1/9 |
| P-057 | 32 | 40 | 9 | 32 | 41 | 8 | 33/41 |
| P-058 | 0 | 7 | 8 | 0 | 8 | 7 | 1/8 |
| P-059 | 109 | 117 | 9 | 109 | 118 | 8 | 110/118 |
| P-060 | 191 | 200 | 10 | 191 | 201 | 9 | 192/201 |
| P-061 | 56 | 65 | 10 | 56 | 66 | 9 | 57/66 |
| P-062 | 89 | 97 | 9 | 89 | 98 | 8 | 90/98 |
| P-063 | 17 | 26 | 10 | 17 | 27 | 9 | 18/27 |
| P-064 | 39 | 48 | 10 | 39 | 49 | 9 | 42/51 |
| P-065 | 134 | 143 | 10 | 134 | 144 | 9 | 135/144 |
| P-066 | 208 | 217 | 10 | 208 | 218 | 9 | 209/218 |
| P-067 | 6 | 15 | 10 | 6 | 16 | 9 | 7/16 |
| P-068 | 105 | 113 | 9 | 105 | 114 | 8 | 106/114 |
| P-069 | 89 | 97 | 9 | 89 | 98 | 8 | 90/98 |
| P-070 | 31 | 40 | 10 | 31 | 41 | 9 | 32/41 |
| P-071 | 0 | 7 | 8 | 0 | 8 | 7 | 1/8 |

## Actual timeline examples

The following anonymized records show actual `ICULOS:SepsisLabel` values around the first positive (`t0`). They all have a visible transition; no patient identifier is exposed.

```text
P-001 (t0 = ICULOS 249)
t-10 239:0 | t-9 240:0 | t-8 241:0 | t-7 242:0 | t-6 243:0
t-5 244:0  | t-4 245:0 | t-3 246:0 | t-2 247:0 | t-1 248:0
t0   249:1 | t+1 250:1 | t+2 251:1 | t+3 252:1 | t+4 253:1

P-004 (t0 = ICULOS 126)
t-10 116:0 | t-9 117:0 | t-8 118:0 | t-7 119:0 | t-6 120:0
t-5 121:0  | t-4 122:0 | t-3 123:0 | t-2 124:0 | t-1 125:0
t0   126:1 | t+1 127:1 | t+2 128:1 | t+3 129:1 | t+4 130:1

P-008 (t0 = ICULOS 64)
t-10 54:0 | t-9 55:0 | t-8 56:0 | t-7 57:0 | t-6 58:0
t-5 59:0  | t-4 60:0 | t-3 61:0 | t-2 62:0 | t-1 63:0
t0   64:1 | t+1 65:1 | t+2 66:1 | t+3 67:1 | t+4 68:1
```

## Candidate target definitions

Let patient rows be indexed by hourly time `t`, let `L(t)` be the supplied `SepsisLabel`, and let `f` be the first row for which `L(f)=1`. Under the documented six-hour shift, define the **onset proxy** `τ = f + 6 hours`. This is an inferred benchmark time, not an independently observed clinical event timestamp.

### A. Current-label target

**Definition:** `y_A(t)=L(t)`.

- Positive samples: all 674 supplied positive rows from 71 patients.
- Negative samples: all 38,216 supplied zero-label rows.
- Leakage: labels are outcomes and may use future event knowledge during offline target creation, which is valid; leakage occurs only if the label, future values, or non-causal transformations enter features. The current target itself does not prevent post-onset information from being represented as positive.
- Early-warning meaning: incomplete. Of 674 positive rows, 426 are in the inferred 1–6-hour pre-onset window and 248 are at/on or after the inferred onset proxy. A model can score well by recognizing already septic/post-onset physiology.
- Sample availability: plentiful relative to the alternatives, but still only 71 positive patients and severe row imbalance.

### B. Future-event target

**Definition:** for each septic patient, `y_B(t)=1` iff `0 < τ-t ≤ 6 hours`; equivalently, for hourly rows, `t ∈ {f, f+1, ..., f+5}`. For non-septic patients, `y_B(t)=0`. For septic patients, rows at `t ≥ τ` are **excluded**, not labeled negative, because the future event has already occurred.

- Positive samples: exactly 426 (six per positive patient) from 71 patients, before applying any history-availability exclusion.
- Negative samples: all rows from non-septic patients plus eligible pre-window rows from septic patients. Post-onset rows are excluded.
- Leakage: target construction needs the future clinical outcome, as every supervised future-event target does; it must be done offline. Features at time `t` may use only measurements at or before `t`, and must never include `L`, `f`, `τ`, future imputation, or future aggregates.
- Early-warning meaning: yes, as a benchmark definition, because every positive represents an inferred onset in the following 1–6 hours.
- Sample availability: 62 positive patients have at least one recorded pre-first-positive observation; 56 have at least six. If a six-hour historical feature window is required before the warning period, the clean subset is 56 patients / 336 B-positive samples. The remaining 15 positive patients have fewer than six pre-first-positive observations, including 9 records that begin positive.

### C. Warning-window before first positive label

**Definition:** `y_C(t)=1` iff `f-6 ≤ t < f`; if fewer than six prior rows are recorded, use the available rows only. This yields `sum(min(6, f)) = 353` positives from 62 patients.

- Positive samples: the six immediately preceding rows where available; 353 total across 62 patients. The 9 records beginning positive contribute none.
- Negative samples: non-septic rows and septic-patient rows before the warning window; all first-positive and later rows should be excluded to avoid treating potentially septic/onset states as negatives.
- Leakage: the future first-positive time is used only to construct the offline target. As with B, causal features are required; no feature may encode future labels or measurements.
- Early-warning meaning: this is more ambitious than the requested approximately-six-hour horizon. Given `τ=f+6`, this window represents inferred onset 7–12 hours away, not 1–6 hours away.
- Sample availability: smaller (353 positives / 62 patients), so variance will be high, especially in the 10-positive-patient test split.

## Recommendation

Use **candidate B** for the next approved implementation stage: a prospective 1–6-hour future-event target based on the official label-shift convention, with post-onset rows excluded from target training and lead-time evaluation. Preserve `SepsisLabel` unchanged as a source column and create no target yet.

Algorithmically, for a positive patient with first supplied positive row `f`, infer `τ=f+6h`; assign `y=1` exactly on valid hourly rows `t` satisfying `0 < τ-t ≤ 6h`; assign `y=0` to valid non-septic rows and septic rows strictly before that positive window; exclude rows at/after `τ`. For an initial temporal-model experiment, require at least six observed rows before `f`, yielding an expected 56 positive patients and 336 positive target samples. For instantaneous-feature baselines, all 71 patients and 426 target positives may be retained, while explicitly flagging the 9 records that begin positive as limited-history cases.

## Is a six-hour claim defensible?

It is defensible only as a **PhysioNet 2019 benchmark claim**: the official training labels are documented as shifted six hours ahead, and the dataset is hourly. It is not evidence that the system predicts independently adjudicated clinical sepsis six hours early in a new clinical setting. The true onset timestamp is inferred from labels rather than available as a separate field, there are only 71 positive patients (10 in the fixed test split), and 9 positive records have no observed pre-label context. Any eventual product wording must remain “predicted risk/early warning; requires clinical assessment.”

## Approval-required assumptions

1. Approve use of `τ=f+6h` as an **official-label-derived onset proxy**, not a direct clinical onset field.
2. Approve the discrete horizon convention `0 < τ-t ≤ 6h` (six hourly positive rows, `f` through `f+5`).
3. Approve exclusion—not negative relabeling—of inferred onset/post-onset rows.
4. Choose whether the first baseline may retain all 426 B-positive samples or must restrict to the six-hour-history subset (336 samples / 56 patients).
5. Approve that the final result be described as a PhysioNet benchmark early-warning evaluation, not a clinically validated six-hour prediction claim.
