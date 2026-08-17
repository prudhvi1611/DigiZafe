import os
import sys
sys.path.insert(0, "/home/digizafe/.local/lib/python3.12/site-packages")
import argparse
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import mean_absolute_error, mean_squared_error , r2_score
import structlog
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend")))
from ml.features.residual_features import RESIDUAL_FEATURES_V1, SCHEMA_VERSION

logger = structlog.get_logger(__name__)

EVAL_REPORT_TEMPLATE = """# Evaluation Report: {version}

**Date**: {date}
**Schema Version**: {schema_version}

> [!WARNING]
> This evaluation uses entirely SYNTHETIC data for pipeline validation. Performance on this dataset does NOT establish real-world predictive validity. Residual ML must remain disabled by default for production use until defensible real-world or approved benchmark evaluation data exists.

## Metrics
- **Mean Absolute Error (MAE)**: {mae:.4f}
- **Root Mean Squared Error (RMSE)**: {rmse:.4f}
- **R² Score**: {r2:.4f}

## Feature Importance (Proxy via Absolute Correlation to Target)
{feature_importance}

## Family Breakdown
{family_breakdown}
"""

MODEL_CARD_TEMPLATE = """# Model Card: {version}

## General Information
- **Version**: {version}
- **Type**: HistGradientBoostingRegressor (scikit-learn)
- **Input Features**: {num_features} dimensions (Schema: `{schema_version}`)
- **Target Output**: Bounded scalar delta on score

## Intended Use
Provides an optional auxiliary risk adjustment strictly bounded by the `residual_ml_max_abs_delta` parameter. It does not replace the deterministic Privacy & Digital Safety Score (PDSS).

## Ethical & Security Considerations
- **Confidence/Abstention**: The model abstains on schema mismatch, missing inputs, or feature extraction failures. Note: scikit-learn tree regressors do not provide per-prediction confidence intervals out of the box, so confidence is omitted.
- **Fairness & Bias**: Currently evaluated only on synthetic data. Production use requires real-world data evaluation across diverse populations to ensure fair risk scoring without disproportionate disparate impact.
- **Security**: The model artifact is cryptographically verified (SHA-256) on load to prevent arbitrary code execution during joblib deserialization.

## Data
Trained on synthetic research fixtures simulating three scenario families: `low_risk_casual`, `high_risk_target`, and `medium_risk_messy`.
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, default=".artifacts/residual-dataset.csv")
    parser.add_argument("--model", type=str, default="ml/models/residual-risk-v1.joblib")
    parser.add_argument("--version", type=str, default="residual-risk-v1")
    args = parser.parse_args()
    
    df = pd.read_csv(args.dataset)
    model = joblib.load(args.model)
    
    X = df[RESIDUAL_FEATURES_V1]
    y_true = df["target_delta"]
    y_pred = model.predict(X)
    
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    
    # Simple proxy for importance if trees don't expose it cleanly
    correlations = df[RESIDUAL_FEATURES_V1].apply(lambda x: x.corr(df["target_delta"])).abs().sort_values(ascending=False)
    feat_imp_str = "\n".join([f"- `{feat}`: {corr:.3f}" for feat, corr in correlations.items()])
    
    # Family breakdown
    family_breakdown = ""
    for family in df["scenario_family"].unique():
        mask = df["scenario_family"] == family
        if mask.sum() > 0:
            f_mae = mean_absolute_error(y_true[mask], y_pred[mask])
            f_mae_str = f"- **{family}**: MAE = {f_mae:.4f} (n={mask.sum()})\n"
            family_breakdown += f_mae_str
            
    eval_content = EVAL_REPORT_TEMPLATE.format(
        version=args.version,
        date=datetime.utcnow().strftime("%Y-%m-%d"),
        schema_version=SCHEMA_VERSION,
        mae=mae,
        rmse=rmse,
        r2=r2,
        feature_importance=feat_imp_str,
        family_breakdown=family_breakdown
    )
    
    card_content = MODEL_CARD_TEMPLATE.format(
        version=args.version,
        num_features=len(RESIDUAL_FEATURES_V1),
        schema_version=SCHEMA_VERSION
    )
    
    os.makedirs("docs/evaluation", exist_ok=True)
    os.makedirs("docs/model-cards", exist_ok=True)
    
    with open(f"docs/evaluation/{args.version}-evaluation.md", "w") as f:
        f.write(eval_content)
        
    with open(f"docs/model-cards/{args.version}.md", "w") as f:
        f.write(card_content)
        
    logger.info("evaluation_complete", docs=["docs/evaluation", "docs/model-cards"])

if __name__ == "__main__":
    main()
