Employee Attrition Prediction API
API FastAPI pour prédire le niveau de risque d'attrition des employés à l'aide d'un modèle XGBoost multiclasse. Intégrée avec Odoo via l'endpoint /predict.
Structure du projet
fastapi_risk_api/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── model.py
│   ├── schemas.py
├── model/
│   ├── final_model.pkl
│   ├── label_encoder.pkl
├── data/
│   └── train_with_risk.csv
├── requirements.txt
├── README.md
├── train_model.py



Créez un environnement virtuel :python -m venv venv
source venv/bin/activate  # Linux/Mac



Installez les dépendances :pip install -r requirements.txt

Exécution de l'API

Lancez l'API :uvicorn app.main:app --host 0.0.0.0 --port 8020


Accédez à la documentation interactive : http://localhost:8020/docs

Endpoints

POST /predict : Prédit le Risk_Level pour un employé.
Exemple de requête :
  {
  "age": 30,
  "gender": "Male",
  "years_at_company": 5,
  "job_role": "Technology",
  "monthly_income": 5000.0,
  "work_life_balance": "Good",
  "job_satisfaction": "High",
  "performance_rating": "Average",
  "number_of_promotions": 2,
  "overtime": "Yes",
  "distance_from_home": 12,
  "education_level": "Bachelor’s Degree",
  "marital_status": "Single",
  "number_of_dependents": 1,
  "job_level": "Mid",
  "company_size": "Medium",
  "company_tenure": 6,
  "remote_work": "Yes",
  "leadership_opportunities": "No",
  "innovation_opportunities": "Yes",
  "company_reputation": "Good",
  "employee_recognition": "High"
}

Réponse :{"prediction": "Low"}

