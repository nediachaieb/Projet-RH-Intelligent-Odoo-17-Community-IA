import logging
from typing import Dict

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.model import load_pipeline_and_features, predict_postes
from app.schemas import PredictionRequest

app = FastAPI(title="Recruitment Needs Forecast API")

# Setup du logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Handler pour renvoyer proprement les 422
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logging.error(f"Validation error: {exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

# Variables globales pour le pipeline et les features
pipeline, features = None, []

@app.on_event("startup")
def startup_event():
    global pipeline, features
    try:
        pipeline, features = load_pipeline_and_features()
        logging.info(f"Pipeline chargé avec succès, {len(features)} features attendues")
    except Exception as e:
        logging.critical(f"Échec du chargement des artefacts : {e}")
        raise RuntimeError(f"Impossible de démarrer sans artefacts : {e}")

@app.post("/predict", response_model=Dict[str, int], tags=["Prediction"])
async def predict_endpoint(payload: PredictionRequest):
    """
    Reçoit un payload contenant toutes les colonnes brutes
    construit un DataFrame, et renvoie la prédiction.
    """
    # 1) On construit le DataFrame
    df = pd.DataFrame([payload.dict()])

    # 2) On prédit
    try:
        pred = predict_postes(df, pipeline, features)
        return {"prediction": pred}
    except KeyError as e:
        logging.error(f"Feature manquante ou invalide : {e}")
        raise HTTPException(status_code=422, detail=f"Feature manquante : {e}")
    except Exception as e:
        logging.error(f"Erreur pendant la prédiction : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne : {e}")


