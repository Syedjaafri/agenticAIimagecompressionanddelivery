from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "training_data.csv"
MODEL_PATH = ROOT / "models" / "compression_model.joblib"
METRICS_PATH = ROOT / "models" / "model_metrics.json"

NUMERIC = [
    "width", "height", "megapixels", "original_kb", "brightness", "contrast",
    "complexity", "sharpness", "minimum_similarity", "network_mbps", "max_attachment_kb"
]
CATEGORICAL = ["intended_use"]
TARGET = "target_quality"


def create_starter_data(rows: int = 1400, seed: int = 42) -> pd.DataFrame:
    """Create disclosed synthetic starter records for pipeline demonstration."""
    rng = np.random.default_rng(seed)
    uses = np.array(["Mobile sharing", "Website", "Email", "Cloud storage", "High-quality archive"])
    use_bias = {"Mobile sharing": -10, "Website": -4, "Email": 0, "Cloud storage": 4, "High-quality archive": 12}

    data = []
    for _ in range(rows):
        width = int(rng.integers(400, 5000))
        height = int(rng.integers(400, 4000))
        megapixels = width * height / 1_000_000
        original_kb = float(np.clip(megapixels * rng.uniform(130, 700), 30, 12000))
        brightness = float(rng.uniform(35, 225))
        contrast = float(rng.uniform(15, 95))
        complexity = float(rng.uniform(3, 85))
        sharpness = float(rng.uniform(50, 7000))
        intended_use = str(rng.choice(uses))
        minimum_similarity = float(rng.uniform(0.82, 0.98))
        network_mbps = float(rng.choice([0.256, 1.0, 5.0, 10.0]))
        max_attachment_kb = float(rng.choice([250, 500, 1024, 2048, 5120]))

        score = 44
        score += 170 * (minimum_similarity - 0.85)
        score += use_bias[intended_use]
        score += min(complexity / 7, 10)
        score += min(contrast / 18, 5)
        score += min(megapixels / 3, 6)
        if max_attachment_kb < original_kb * 0.25:
            score -= 8
        if network_mbps <= 0.256:
            score -= 4
        target = float(np.clip(score + rng.normal(0, 2.2), 30, 90))

        data.append({
            "width": width, "height": height, "megapixels": megapixels,
            "original_kb": original_kb, "brightness": brightness,
            "contrast": contrast, "complexity": complexity, "sharpness": sharpness,
            "minimum_similarity": minimum_similarity, "network_mbps": network_mbps,
            "max_attachment_kb": max_attachment_kb, "intended_use": intended_use,
            "target_quality": target,
        })
    return pd.DataFrame(data)


def train_and_save() -> dict:
    ROOT.joinpath("data").mkdir(exist_ok=True)
    ROOT.joinpath("models").mkdir(exist_ok=True)
    df = create_starter_data()
    df.to_csv(DATA_PATH, index=False)

    X = df[NUMERIC + CATEGORICAL]
    y = df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    preprocessor = ColumnTransformer([
        ("numeric", StandardScaler(), NUMERIC),
        ("category", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    ])
    model = RandomForestRegressor(n_estimators=220, max_depth=14, random_state=42, n_jobs=-1)
    pipeline = Pipeline([("preprocessor", preprocessor), ("model", model)])
    pipeline.fit(X_train, y_train)
    predictions = pipeline.predict(X_test)

    metrics = {
        "mae": float(mean_absolute_error(y_test, predictions)),
        "r2": float(r2_score(y_test, predictions)),
        "training_rows": int(len(X_train)),
        "testing_rows": int(len(X_test)),
        "data_type": "synthetic starter demonstration data",
    }
    joblib.dump(pipeline, MODEL_PATH)
    import json
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    print(train_and_save())
