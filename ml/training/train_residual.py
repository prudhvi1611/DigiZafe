import os
import sys
sys.path.insert(0, "/home/digizafe/.local/lib/python3.12/site-packages")
import argparse
import pandas as pd
import joblib
import hashlib
import structlog
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend")))
from ml.features.residual_features import RESIDUAL_FEATURES_V1, SCHEMA_VERSION

logger = structlog.get_logger(__name__)

def compute_sha256(filepath: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, default=".artifacts/residual-dataset.csv")
    parser.add_argument("--output", type=str, default="ml/models/residual-risk-v1.joblib")
    parser.add_argument("--version", type=str, default="residual-risk-v1")
    args = parser.parse_args()
    
    logger.info("training_residual_ml", dataset=args.dataset, output=args.output)
    
    if not os.path.exists(args.dataset):
        logger.error("dataset_not_found", path=args.dataset)
        sys.exit(1)
        
    df = pd.read_csv(args.dataset)
    
    # Ensure exact column order for training matching inference
    X = df[RESIDUAL_FEATURES_V1]
    y = df["target_delta"]
    
    # Very small, fast model
    model = HistGradientBoostingRegressor(
        max_iter=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42
    )
    
    logger.info("fitting_model...")
    model.fit(X, y)
    
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    joblib.dump(model, args.output)
    
    checksum = compute_sha256(args.output)
    
    logger.info(
        "model_saved", 
        path=args.output, 
        version=args.version, 
        schema_version=SCHEMA_VERSION,
        sha256=checksum
    )
    
    # Optionally print for easy copy-pasting to registry.py
    print(f"\n======================================")
    print(f"MODEL_VERSION: {args.version}")
    print(f"SCHEMA_VERSION: {SCHEMA_VERSION}")
    print(f"SHA256 CHECKSUM: {checksum}")
    print(f"======================================\n")

if __name__ == "__main__":
    main()
