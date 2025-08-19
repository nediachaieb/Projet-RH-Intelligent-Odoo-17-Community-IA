# Recruitment Prediction API

API FastAPI pour prédire le nombre de recrutements à prévoir, basée sur un modèle ML (XGBRegressor) entraîné avec des features RH + historiques.

## Lancer l'API

pip install -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port 8050

