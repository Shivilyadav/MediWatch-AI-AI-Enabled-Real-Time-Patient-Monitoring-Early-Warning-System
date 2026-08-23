import pandas as pd
import numpy as np
from sklearn.metrics import confusion_matrix, roc_auc_score, average_precision_score

def compute_news2_score(row):
    """Calculate NEWS2 score using available physiological variables"""
    score = 0

    # Heart rate (HR)
    hrs = row['heart_rate']
    if hrs <= 40:
        score += 3
    elif hrs <= 50:
        score += 1
    elif hrs <= 90:
        score += 0
    elif hrs <= 110:
        score += 1
    elif hrs <= 130:
        score += 2
    else:
        score += 3

    # SpO2
    spo2 = row['spo2']
    if spo2 <= 91:
        score += 3
    elif spo2 <= 93:
        score += 1
    else:
        score += 0

    # Temperature (°C)
    temp = row['temperature']
    if temp <= 35.0:
        score += 3
    elif temp <= 36.0:
        score += 1
    elif temp <= 37.9:
        score += 0
    elif temp <= 38.9:
        score += 1
    else:
        score += 2

    # Systolic BP
    sbp = row['systolic_bp']
    if sbp <= 90:
        score += 3
    elif sbp <= 100:
        score += 2
    elif sbp <= 219:
        score += 0
    else:
        score += 3

    # Respiratory Rate (RR)
    rr = row['respiratory_rate']
    if rr <= 8:
        score += 3
    elif rr <= 11:
        score += 1
    elif rr <= 20:
        score += 0
    elif rr <= 24:
        score += 1
    else:
        score += 2

    # NOTE: Level of consciousness (AVPU) and BUN are NOT available in our data
    # These would normally contribute to NEWS2 score but are omitted here

    return score

# Load data
print("Loading training data...")
train_df = pd.read_csv('ml_pipeline/data/processed/train_features.csv')
val_df = pd.read_csv('ml_pipeline/data/processed/validation_features.csv')
test_df = pd.read_csv('ml_pipeline/data/processed/test_features.csv')

print(f"Train: {len(train_df)} rows, {train_df['patient_id'].nunique()} patients")
print(f"Validation: {len(val_df)} rows, {val_df['patient_id'].nunique()} patients")
print(f"Test: {len(test_df)} rows, {test_df['patient_id'].nunique()} patients")

# Compute NEWS2 scores
print("\nComputing NEWS2 scores...")
train_df['news2_score'] = train_df.apply(compute_news2_score, axis=1)
val_df['news2_score'] = val_df.apply(compute_news2_score, axis=1)
test_df['news2_score'] = test_df.apply(compute_news2_score, axis=1)

# Calculate metrics for validation set
print("\n=== NEWS2 Validation Results ===")
y_val_true = val_df['target'].values
y_val_scores = val_df['news2_score'].values

# Try different thresholds to find optimal based on validation
best_f1 = 0
best_threshold = 0
thresholds = range(0, 21)  # NEWS2 score range without consciousness/BUN: 0-20

for threshold in thresholds:
    y_pred = (y_val_scores >= threshold).astype(int)
    if (y_val_true.sum() == 0):  # Handle edge case
        f1 = 0
    else:
        tn, fp, fn, tp = confusion_matrix(y_val_true, y_pred).ravel()
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold

print(f"Best threshold from validation: {best_threshold} (F1={best_f1:.4f})")

# Evaluate on validation with best threshold
y_val_pred = (y_val_scores >= best_threshold).astype(int)
tn, fp, fn, tp = confusion_matrix(y_val_true, y_val_pred).ravel()
auroc_val = roc_auc_score(y_val_true, y_val_scores)
aprc_val = average_precision_score(y_val_true, y_val_scores)
sensitivity_val = tp / (tp + fn) if (tp + fn) > 0 else 0
specificity_val = tn / (tn + fp) if (tn + fp) > 0 else 0
precision_val = tp / (tp + fp) if (tp + fp) > 0 else 0
f1_val = 2 * (precision_val * sensitivity_val) / (precision_val + sensitivity_val) if (precision_val + sensitivity_val) > 0 else 0
accuracy_val = (tp + tn) / (tp + tn + fp + fn)
fpr_val = fp / (tn + fp) if (tn + fp) > 0 else 0

print(f"Validation Results (threshold={best_threshold}):")
print(f"  AUROC: {auroc_val:.4f}")
print(f"  AUPRC: {aprc_val:.4f}")
print(f"  Sensitivity: {sensitivity_val:.4f}")
print(f"  Specificity: {specificity_val:.4f}")
print(f"  Precision: {precision_val:.4f}")
print(f"  F1-Score: {f1_val:.4f}")
print(f"  Accuracy: {accuracy_val:.4f}")
print(f"  False Positive Rate: {fpr_val:.4f}")
print(f"  Confusion Matrix: TN={tn}, FP={fp}, FN={fn}, TP={tp}")

# Evaluate on test set with frozen threshold
print("\n=== NEWS2 Test Results (frozen threshold) ===")
y_test_true = test_df['target'].values
y_test_scores = test_df['news2_score'].values
y_test_pred = (y_test_scores >= best_threshold).astype(int)
tn_test, fp_test, fn_test, tp_test = confusion_matrix(y_test_true, y_test_pred).ravel()
auroc_test = roc_auc_score(y_test_true, y_test_scores)
aprc_test = average_precision_score(y_test_true, y_test_scores)
sensitivity_test = tp_test / (tp_test + fn_test) if (tp_test + fn_test) > 0 else 0
specificity_test = tn_test / (tn_test + fp_test) if (tn_test + fp_test) > 0 else 0
precision_test = tp_test / (tp_test + fp_test) if (tp_test + fp_test) > 0 else 0
f1_test = 2 * (precision_test * sensitivity_test) / (precision_test + sensitivity_test) if (precision_test + sensitivity_test) > 0 else 0
accuracy_test = (tp_test + tn_test) / (tp_test + tn_test + fp_test + fn_test)
fpr_test = fp_test / (tn_test + fp_test) if (tn_test + fp_test) > 0 else 0

print(f"Test Results (threshold={best_threshold}):")
print(f"  AUROC: {auroc_test:.4f}")
print(f"  AUPRC: {aprc_test:.4f}")
print(f"  Sensitivity: {sensitivity_test:.4f}")
print(f"  Specificity: {specificity_test:.4f}")
print(f"  Precision: {precision_test:.4f}")
print(f"  F1-Score: {f1_test:.4f}")
print(f"  Accuracy: {accuracy_test:.4f}")
print(f"  False Positive Rate: {fpr_test:.4f}")
print(f"  Confusion Matrix: TN={tn_test}, FP={fp_test}, FN={fn_test}, TP={tp_test}")
print(f"  Positive samples in test: {y_test_true.sum()}")

# Save results
import json
results = {
    'news2': {
        'best_threshold': int(best_threshold),
        'validation': {
            'auroc': float(auroc_val),
            'auprc': float(aprc_val),
            'sensitivity': float(sensitivity_val),
            'specificity': float(specificity_val),
            'precision': float(precision_val),
            'f1': float(f1_val),
            'accuracy': float(accuracy_val),
            'fpr': float(fpr_val),
            'confusion_matrix': {
                'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp)
            }
        },
        'test': {
            'auroc': float(auroc_test),
            'auprc': float(aprc_test),
            'sensitivity': float(sensitivity_test),
            'specificity': float(specificity_test),
            'precision': float(precision_test),
            'f1': float(f1_test),
            'accuracy': float(accuracy_test),
            'fpr': float(fpr_test),
            'confusion_matrix': {
                'tn': int(tn_test), 'fp': int(fp_test), 'fn': int(fn_test), 'tp': int(tp_test)
            }
        }
    }
}

with open('ml_pipeline/results/news2_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print("\nResults saved to ml_pipeline/results/news2_results.json")