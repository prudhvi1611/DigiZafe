# Model Card: residual-risk-v1

## General Information
- **Version**: residual-risk-v1
- **Type**: HistGradientBoostingRegressor (scikit-learn)
- **Input Features**: 11 dimensions (Schema: `residual-features-v1`)
- **Target Output**: Bounded scalar delta on score

## Intended Use
Provides an optional auxiliary risk adjustment strictly bounded by the `residual_ml_max_abs_delta` parameter. It does not replace the deterministic Privacy & Digital Safety Score (PDSS).

## Ethical & Security Considerations
- **Confidence/Abstention**: The model abstains on schema mismatch, missing inputs, or feature extraction failures. Note: scikit-learn tree regressors do not provide per-prediction confidence intervals out of the box, so confidence is omitted.
- **Fairness & Bias**: Currently evaluated only on synthetic data. Production use requires real-world data evaluation across diverse populations to ensure fair risk scoring without disproportionate disparate impact.
- **Security**: The model artifact is cryptographically verified (SHA-256) on load to prevent arbitrary code execution during joblib deserialization.

## Data
Trained on synthetic research fixtures simulating three scenario families: `low_risk_casual`, `high_risk_target`, and `medium_risk_messy`.
