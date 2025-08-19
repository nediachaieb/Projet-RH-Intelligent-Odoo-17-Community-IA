
# 🚀 Projet RH Intelligent : Odoo 17 Community + IA (FastAPI & Machine Learning)

## 📌 Contexte

Ce projet démontre comment transformer **Odoo 17 Community** en une plateforme **RH intelligente** en intégrant des services **IA / Machine Learning** via **FastAPI** et **Docker**.

Trois axes stratégiques ont été développés :

1. 🔍 **Détection du risque de départ des employés** (Attrition Prediction)
2. 📊 **Prévision des besoins en recrutement** (Workforce Forecasting)
3. 🤝 **Matching intelligent entre CVs et postes** (AI Matching)

Chaque fonctionnalité est implémentée comme un **microservice FastAPI** et **connectée directement à Odoo** via des modules personnalisés.

---

## 🧠 IA intégrée dans Odoo (Sprint par Sprint)

### 🔹 Sprint 1 : Risk Prediction (Attrition)

* 📊 **Modèle IA** : XGBoost (SMOTE + Optuna tuning)
* 🎯 Objectif : prédire le niveau de risque (`Low`, `Medium`, `High`) pour chaque employé
* 🔗 API : `POST /predict` via FastAPI
* ✅ **Intégration Odoo** :

  * Barre de progression colorée **dans la fiche employé**
  * Niveau de risque enregistré automatiquement dans le champ `predicted_risk`

**Exemple JSON :**

```json
{
  "age": 34,
  "years_at_company": 5,
  "job_role": "Software Engineer",
  "monthly_income": 3500,
  "distance_from_home": 12,
  "number_of_promotions": 1,
  "number_of_dependents": 2,
  "job_level": "Mid",
  "company_size": "Medium",
  "education_level": "Bachelor’s Degree",
  "marital_status": "Married",
  "overtime": "No",
  "remote_work": "Yes",
  "leadership_opportunities": "No",
  "innovation_opportunities": "Yes",
  "gender": "Female",
  "company_reputation": "Good",
  "employee_recognition": "High",
  "work_life_balance": "Excellent",
  "job_satisfaction": "High",
  "performance_rating": "Average"
}
```

---

### 🔹 Sprint 2 : Recruitment Analysis (Prévision des effectifs)

* 📊 **Modèles IA** : RandomForest, XGBoost, LightGBM, GradientBoost (comparaison R²)
* 🎯 Objectif : prédire le nombre de **postes à lancer** par département et trimestre
* 🔗 API : `POST /predict` via FastAPI
* ✅ **Intégration Odoo** :

  * Module `recruitment_analysis`
  * Résultats stockés dans `department.analysis.history`
  * Tableaux de suivi accessibles depuis le menu RH

**Exemple JSON :**

```json
{
  "annee": 2025,
  "quarter_num": 2,
  "department": "IT",
  "departs_confirmes": 3,
  "candidats_en_cours": 4,
  "postes_ouverts_actuels": 2,
  "effectif_actuel": 45,
  "turnover_month_pct": 0.08,
  "departs_confirmes_rolling_mean": 2.5,
  "candidats_en_cours_rolling_mean": 3.2,
  "postes_ouverts_actuels_rolling_mean": 1.8,
  "effectif_actuel_rolling_mean": 44,
  "turnover_month_pct_rolling_mean": 0.07,
  "departs_confirmes_lag_1": 2,
  "candidats_en_cours_lag_1": 3,
  "postes_ouverts_actuels_lag_1": 1,
  "effectif_actuel_lag_1": 46,
  "turnover_month_pct_lag_1": 0.06
}
```

---

### 🔹 Sprint 3 : CV Matching

* 📊 **Approche IA** : NLP (TF-IDF / Similarité Cosine) avec nettoyage PDF/HTML
* 🎯 Objectif : comparer une **description de poste** avec plusieurs CVs et retourner un score de similarité
* 🔗 API : `POST /match/multiple` via FastAPI
* ✅ **Intégration Odoo** :

  * Module `hr_employee_ai_matching`
  * Bouton *Lancer le matching* dans les postes
  * Résultats affichés dans `hr.matching.result` avec score (%) trié

**Exemple JSON :**

```json
{
  "job_description": "We are looking for a Data Scientist with skills in Python and Machine Learning...",
  "cvs": [
    { "name": "Alice_CV.pdf", "text": "Alice has 5 years experience in Python and Deep Learning..." },
    { "name": "Bob_CV.pdf", "text": "Bob is an engineer specialized in SQL and data visualization..." }
  ]
}
```

---

## 🛠️ Architecture technique

```mermaid
flowchart LR
    subgraph Odoo[Odoo 17 Community]
      RP[risk_prediction] -->|/predict| FastAPI1
      RA[recruitment_analysis] -->|/predict| FastAPI2
      CVM[hr_employee_ai_matching] -->|/match/multiple| FastAPI3
    end

    subgraph FastAPI
      FastAPI1[XGBoost Classifier]:::ml
      FastAPI2[Time Series Models]:::ml
      FastAPI3[CV Matching NLP]:::ml
    end

    classDef ml fill=#d9f,stroke=#333,stroke-width=1px;
```

---

## ⚡ Lancement rapide

```bash
# Cloner le projet
git clone https://github.com/username/Project_odoo_17_IA.git
cd Project_odoo_17_IA

# Démarrer avec Docker
docker-compose up --build
```

* 🔹 Odoo → `http://localhost:8069`
* 🔹 Risk API → `http://localhost:8020/predict`
* 🔹 Recruitment API → `http://localhost:8050/predict`
* 🔹 Matching API → `http://localhost:8045/match/multiple`

---

## 📂 Structure du projet

```
Project_odoo_17_IA-main
│── odoo/custom_addons/
│   ├── risk_prediction/          # Sprint 1 (Attrition)
│   ├── recruitment_analysis/     # Sprint 2 (Prévision RH)
│   └── hr_employee_ai_matching/  # Sprint 3 (Matching CVs)
│── risk_api/                     # FastAPI - Risk Prediction
│── recrutement_api/              # FastAPI - Recruitment Forecast
│── matching_api/                 # FastAPI - CV Matching
│── ML_Risque de depart/          # Notebooks Sprint 1
│── ML_prévision des effectifs/   # Notebooks Sprint 2
│── logs/ odoo-source/ Dockerfile docker-compose.yml
```

---
🛠️ Stack Technique

ERP : Odoo 17 Community + PostgreSQL

ML & Data : scikit-learn, XGBoost, LightGBM, Optuna, Imbalanced-learn

APIs : FastAPI, Pydantic, Uvicorn

Déploiement : Docker & Docker Compose

Parsing CVs : PyMuPDF (fitz), BeautifulSoup

👥 Auteurs

Projet PFE – ESSAT Gabès (2025)
Encadré par : [Dr Nacim Yanes ]
Développé par : [Nadia chaieb ]
## 🎯 Conclusion

✅ Détection proactive du **risque de départ**
✅ Anticipation des **besoins de recrutement**
✅ Recommandation intelligente de **candidats adaptés**

👉 Ce projet montre qu’**Odoo 17 Community**, enrichi par des services **IA via FastAPI**, peut devenir un **véritable moteur décisionnel RH**.

-