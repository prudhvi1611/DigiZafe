# Evaluation Report: residual-risk-v1

**Date**: 2026-07-13
**Schema Version**: residual-features-v1

> [!WARNING]
> This evaluation uses entirely SYNTHETIC data for pipeline validation. Performance on this dataset does NOT establish real-world predictive validity. Residual ML must remain disabled by default for production use until defensible real-world or approved benchmark evaluation data exists.

## Metrics
- **Mean Absolute Error (MAE)**: 1.1478
- **Root Mean Squared Error (RMSE)**: 1.4336

## Feature Importance (Proxy via Absolute Correlation to Target)
- `pdss_score_confirmed`: 0.756
- `count_track_confirmed`: 0.672
- `max_base_severity`: 0.658
- `count_finding_identity`: 0.557
- `count_finding_credential`: 0.510
- `count_finding_financial`: 0.464
- `sum_base_severity`: 0.391
- `pdss_score_possible`: 0.041
- `count_track_possible`: 0.028
- `source_diversity`: 0.014
- `avg_confidence`: 0.003

## Family Breakdown
- **medium_risk_messy**: MAE = 1.2006 (n=327)
- **high_risk_target**: MAE = 1.1210 (n=323)
- **low_risk_casual**: MAE = 1.1233 (n=350)

