import os
import sys
sys.path.insert(0, "/home/digizafe/.local/lib/python3.12/site-packages")
import numpy as np
import pandas as pd
import argparse
import structlog

# Ensure backend imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend")))
from ml.features.residual_features import RESIDUAL_FEATURES_V1, SCHEMA_VERSION

logger = structlog.get_logger(__name__)

SYNTHETIC_GENERATOR_VERSION = "v1.0.0"

def generate_synthetic_data(num_samples: int, seed: int):
    """
    Generates synthetic data for Sprint 12 validation.
    
    LIMITATIONS:
    - This dataset is entirely synthetic and based on manual heuristics.
    - It does not represent real-world user risk distributions.
    - Performance on this dataset does NOT establish real-world predictive validity.
    """
    np.random.seed(seed)
    
    # We will define a few "scenario families" to avoid leakage during splits
    scenario_families = ["low_risk_casual", "high_risk_target", "medium_risk_messy"]
    
    data = []
    
    for i in range(num_samples):
        family = np.random.choice(scenario_families)
        
        if family == "low_risk_casual":
            count_finding_credential = np.random.poisson(1)
            count_finding_identity = np.random.poisson(0.5)
            count_finding_financial = 0
            pdss_confirmed = np.random.uniform(0, 30)
            max_base_severity = np.random.choice([0, 2, 5])
            true_residual_mean = -2.0 # Tends to overstate risk for casual users
            
        elif family == "high_risk_target":
            count_finding_credential = np.random.poisson(5)
            count_finding_identity = np.random.poisson(3)
            count_finding_financial = np.random.poisson(1)
            pdss_confirmed = np.random.uniform(60, 90)
            max_base_severity = np.random.choice([8, 10])
            true_residual_mean = 5.0 # Tends to understate risk for targets
            
        else: # medium_risk_messy
            count_finding_credential = np.random.poisson(3)
            count_finding_identity = np.random.poisson(1)
            count_finding_financial = np.random.poisson(0.5)
            pdss_confirmed = np.random.uniform(30, 60)
            max_base_severity = np.random.choice([5, 8])
            true_residual_mean = 0.0
            
        row = {
            "count_finding_credential": float(count_finding_credential),
            "count_finding_identity": float(count_finding_identity),
            "count_finding_financial": float(count_finding_financial),
            "count_track_confirmed": float(count_finding_credential + count_finding_identity + count_finding_financial),
            "count_track_possible": float(np.random.poisson(2)),
            "sum_base_severity": float(max_base_severity + np.random.exponential(5)),
            "max_base_severity": float(max_base_severity),
            "source_diversity": float(np.random.randint(1, 5)),
            "avg_confidence": float(np.random.uniform(0.6, 1.0)),
            "pdss_score_confirmed": float(pdss_confirmed),
            "pdss_score_possible": float(np.random.uniform(0, 20)),
            
            # Metadata
            "scenario_family": family,
            
            # Target generation function
            # target = heuristic_mean + noise
            "target_delta": np.random.normal(true_residual_mean, 2.0)
        }
        data.append(row)
        
    df = pd.DataFrame(data)
    
    # Ensure all features exist
    for f in RESIDUAL_FEATURES_V1:
        if f not in df.columns:
            df[f] = 0.0
            
    return df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default=".artifacts/residual-dataset.csv")
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    
    logger.info(
        "generating_synthetic_dataset",
        generator_version=SYNTHETIC_GENERATOR_VERSION,
        seed=args.seed,
        schema_version=SCHEMA_VERSION,
        samples=args.samples
    )
    
    df = generate_synthetic_data(args.samples, args.seed)
    
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    df.to_csv(args.output, index=False)
    
    logger.info("synthetic_dataset_saved", path=args.output)
    
    # Write metadata manifest
    manifest_path = args.output.replace(".csv", "-manifest.json")
    manifest = pd.Series({
        "generator_version": SYNTHETIC_GENERATOR_VERSION,
        "seed": args.seed,
        "schema_version": SCHEMA_VERSION,
        "samples": args.samples,
        "limitations": "Synthetic data ONLY. Does not establish real-world predictive validity.",
        "target_function": "true_residual_mean + N(0, 2.0)"
    })
    manifest.to_json(manifest_path, indent=2)
    logger.info("manifest_saved", path=manifest_path)

if __name__ == "__main__":
    main()
