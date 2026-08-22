import glob
import os
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "raw", "physionet"))
MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "model.pkl"))

FEATURES = ["HR", "O2Sat", "Temp", "SBP", "MAP", "DBP", "Resp"]

def load_physionet_data(max_files=1000):
    """
    Parses PhysioNet 2019 PSV files for vital parameters and sepsis risk label.
    """
    psv_files = glob.glob(os.path.join(DATA_DIR, "**", "*.psv"), recursive=True)
    if not psv_files:
        # Fallback search in data/
        fallback_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
        psv_files = glob.glob(os.path.join(fallback_dir, "**", "*.psv"), recursive=True)

    print(f"Found {len(psv_files)} PSV patient files.")
    if not psv_files:
        raise FileNotFoundError("No .psv files found in ml_pipeline/data/raw/physionet/. Please run download_physionet.py first.")

    psv_files = psv_files[:max_files]
    data_list = []

    for fpath in psv_files:
        try:
            df = pd.read_csv(fpath, sep='|')
            subset = df[FEATURES + ["SepsisLabel"]].dropna(how='all', subset=FEATURES)
            if not subset.empty:
                data_list.append(subset)
        except Exception:
            continue

    if not data_list:
        raise ValueError("Could not parse valid data rows from PSV files.")

    combined_df = pd.concat(data_list, ignore_index=True)
    combined_df = combined_df.fillna(combined_df.median())
    
    X = combined_df[FEATURES]
    y = combined_df["SepsisLabel"]
    
    return X, y

def train():
    print("Loading PhysioNet 2019 dataset...")
    X, y = load_physionet_data(max_files=2000)
    print(f"Dataset shape: {X.shape}, Positive sepsis instances: {y.sum()}")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    print("Training RandomForest model on real ICU telemetry...")
    clf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, class_weight="balanced")
    clf.fit(X_train, y_train)

    preds = clf.predict(X_test)
    probs = clf.predict_proba(X_test)[:, 1]

    print("\nClassification Report:")
    print(classification_report(y_test, preds))
    print(f"ROC-AUC Score: {roc_auc_score(y_test, probs):.4f}")

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(clf, f)
    print(f"Model saved successfully to {MODEL_PATH}")

if __name__ == "__main__":
    train()
