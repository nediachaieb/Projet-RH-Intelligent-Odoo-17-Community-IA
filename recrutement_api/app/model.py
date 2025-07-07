from pathlib import Path
import joblib
import pandas as pd
from typing import Tuple, List, Any

# Chemin absolu vers le dossier contenant preprocessor.pkl, features.txt et pipeline_complete.pkl
MODEL_DIR = Path("model")

def load_pipeline_and_features() -> Tuple[Any, List[str]]:
    """
    Charge :
      - pipeline_complete.pkl : pipeline complet (preprocessor + modèle)
      - features.txt          : liste des colonnes brutes attendues
    """
    pipeline = joblib.load(MODEL_DIR / "pipeline_complete.pkl")
    with open(MODEL_DIR / "features.txt", encoding="utf-8") as f:
        features = [line.strip() for line in f if line.strip()]
    return pipeline, features

def predict_postes(
    input_df: pd.DataFrame,
    pipeline: Any,
    features: List[str]
) -> int:
    """
    1) Sélectionne et réordonne les colonnes brutes selon features.txt
    2) Applique le pipeline (OHE + scaling + modèle)
    3) Renvoie la prédiction comme int
    """
    X = input_df[features]
    y_pred = pipeline.predict(X)
    return int(round(y_pred[0]))
