# MediWatch AI — Codex Instructions

This repository contains MediWatch AI, an AI-enabled real-time patient monitoring and early-warning system.

The user is the ML/AI Engineer for the project.

## Before modifying ML code
1. Read `docs/ML_PROJECT_CONTEXT.md`.
2. Inspect the existing repository and current implementation.
3. Preserve existing backend/frontend API contracts unless explicitly instructed otherwise.
4. Never introduce patient-level or temporal data leakage.
5. Never fabricate model metrics.
6. Work incrementally and run tests after major changes.
7. Do not replace learned ML with arbitrary if/else rules.
8. Keep the clinical decision-support nature of the project explicit.

## Planned ML pipeline
The intended progression is:
- dataset audit
- patient-level train/validation/test split
- preprocessing
- temporal/derived feature engineering
- NEWS2 baseline
- Logistic Regression
- Random Forest
- XGBoost
- SHAP explainability
- LSTM temporal model
- model comparison and selection
- real-time backend integration

Do not jump directly to the final model. Complete and validate each stage.

## First task
Start with a data audit only. Report dataset structure, patient count, rows, missingness, class balance, and other relevant facts before changing the training pipeline.
