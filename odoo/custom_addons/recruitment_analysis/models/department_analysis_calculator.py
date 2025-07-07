# -*- coding: utf-8 -*-
import calendar
import logging
from datetime import date, datetime
import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
API_URL = "http://fastapirecrut:8050/predict"
TIMEOUT = 15  # secondes


class DepartmentAnalysisCalculator(models.Model):
    _name = "department.analysis.calculator"
    _description = "Recruitment Need Calculator"
    name = fields.Char(string="Department Analysis", compute="_compute_name", store=True)

    @api.depends('department_id', 'analysis_month', 'analysis_year')
    def _compute_name(self):
        for rec in self:
            if rec.department_id and rec.analysis_month and rec.analysis_year:
                month_name = calendar.month_name[int(rec.analysis_month)]
                rec.name = f"{rec.department_id.name} - {month_name} {rec.analysis_year}"
            else:
                rec.name = _("Nouvelle analyse")

    # ------------------------------------------------------------
    # 1. CHAMPS DE CONTEXTE & PÉRIODE
    # ------------------------------------------------------------
    department_id = fields.Many2one(
        "hr.department", string="Department", required=True
    )
    analysis_month = fields.Selection(
        [(str(m), str(m)) for m in range(1, 13)],
        string="Analysis Month",
        required=True
    )
    analysis_year = fields.Integer(
        string="Analysis Year",
        required=True,
        default=lambda self: datetime.now().year,store=True
    )
    date_from = fields.Date(
        compute="_compute_analysis_period", store=True
    )
    date_to = fields.Date(
        compute="_compute_analysis_period", store=True
    )
    #le numéro du trimestre (1 à 4)
    quarter_num = fields.Integer(string="Quarter", compute="_compute_calendar_indicators")

    # ------------------------------------------------------------
    # 2. KPI DE BASE
    # ------------------------------------------------------------
    departs_confirmes = fields.Integer(
        string="Confirmed Departures", store=True
    )
    candidats_en_cours = fields.Integer(
        string="Active Candidates", store=True
    )
    postes_ouverts_actuels = fields.Integer(
        string="Open Positions", store=True
    )
    effectif_actuel = fields.Integer(
        string="Current Headcount", store=True
    )
    turnover_month_pct = fields.Float(
        string="Monthly Turnover Rate", store=True
    )

    # ------------------------------------------------------------
    # 3. MOYENNES GLISSANTES (SUR 4 TRIMESTRES)
    # ------------------------------------------------------------
    departs_confirmes_rolling_mean = fields.Float(
        string="Avg-Confirmed Departures",
        compute="_compute_rolling_means",
        store=True,
    )
    candidats_en_cours_rolling_mean = fields.Float(
        string="Avg-Active Candidates",
        compute="_compute_rolling_means",
        store=True,
    )
    postes_ouverts_actuels_rolling_mean = fields.Float(
        string="Avg-Open Positions",
        compute="_compute_rolling_means",
        store=True,
    )
    effectif_actuel_rolling_mean = fields.Float(
        string="Avg-Current Headcount",
        compute="_compute_rolling_means",
        store=True,
    )
    turnover_month_pct_rolling_mean = fields.Float(
        string="Avg-Monthly Attrition",
        compute="_compute_rolling_means",
        store=True,
    )

    # ------------------------------------------------------------
    # 4. LAGS (valeurs décalées) TRIMESTRIELS (1→4 trimestres précédents)
    # ------------------------------------------------------------
    departs_confirmes_lag_1 = fields.Float(store=True)
    departs_confirmes_lag_2 = fields.Float(store=True)
    departs_confirmes_lag_3 = fields.Float(store=True)
    departs_confirmes_lag_4 = fields.Float(store=True)
    #----------------------------------------------
    candidats_en_cours_lag_1 = fields.Float(store=True)
    candidats_en_cours_lag_2 = fields.Float(store=True)
    candidats_en_cours_lag_3 = fields.Float(store=True)
    candidats_en_cours_lag_4 = fields.Float(store=True)
    #---------------------------------------------------
    postes_ouverts_actuels_lag_1 = fields.Float(store=True)
    postes_ouverts_actuels_lag_2 = fields.Float(store=True)
    postes_ouverts_actuels_lag_3 = fields.Float(store=True)
    postes_ouverts_actuels_lag_4 = fields.Float(store=True)
    #---------------------------------------------------

    effectif_actuel_lag_1 = fields.Float(store=True)
    effectif_actuel_lag_2 = fields.Float(store=True)
    effectif_actuel_lag_3 = fields.Float(store=True)
    effectif_actuel_lag_4 = fields.Float(store=True)
    #---------------------------------------------------
    turnover_month_pct_lag_1 = fields.Float(store=True)
    turnover_month_pct_lag_2 = fields.Float(store=True)
    turnover_month_pct_lag_3 = fields.Float(store=True)
    turnover_month_pct_lag_4 = fields.Float(store=True)

    # ------------------------------------------------------------
    # 5. SORTIE DU MODÈLE
    # ------------------------------------------------------------
    predicted_need = fields.Float(string="Predicted Need", readonly=True)

    # ============================================================
    # MÉTHODE 1 : calcul de la période d’analyse
    # ============================================================
    @api.depends("analysis_month", "analysis_year")
    def _compute_analysis_period(self):
        for rec in self:
            if rec.analysis_month and rec.analysis_year:
                try:
                    month = int(rec.analysis_month)
                    year = rec.analysis_year
                    rec.date_from = date(year, month, 1)
                    #dernier jour du mois
                    last_day = calendar.monthrange(year, month)[1]
                    rec.date_to = date(year, month, last_day)
                except Exception as e:
                    _logger.error(" Erreur dans _compute_analysis_period: %s", e)
                    rec.date_from = rec.date_to = False
            else:
                rec.date_from = rec.date_to = False

    # ============================================================
    # MÉTHODE 2 : calcul du numéro de trimestre
    # ============================================================
    @api.depends("analysis_month")
    def _compute_calendar_indicators(self):
        for rec in self:
            if rec.analysis_month:
                month = int(rec.analysis_month)
                rec.quarter_num = (month - 1) // 3 + 1
            else:
                rec.quarter_num = False

    # ============================================================
    # MÉTHODE 3 : calcul des indicateurs de base
    # ============================================================
    @api.depends("department_id", "date_from", "date_to")
    def _compute_basic_metrics(self):
        #Accède aux modèles Odoo pour les employés, contrats, candidats, postes et évaluations
        Employee = self.env["hr.employee"]
        Contract = self.env["hr.contract"]
        Applicant = self.env["hr.applicant"]
        Job = self.env["hr.job"]
        Eval = self.env["historique.evaluation"]

        for rec in self:
            # initialisation à zéro
            rec.departs_confirmes = 0
            rec.candidats_en_cours = 0
            rec.postes_ouverts_actuels = 0
            rec.effectif_actuel = 0
            rec.turnover_month_pct = 0.0

            # headcount : nombre d’employés
            employees = Employee.search([
                ('department_id', '=', rec.department_id.id)
            ])
            rec.effectif_actuel = len(employees)


            # Départs confirmés (contrats terminés + attrition risquée)
            ended_contracts = Contract.search_count([
                ("employee_id.department_id", "=", rec.department_id.id),
                 ("date_end", ">=", rec.date_from),
                 ("date_end", "<=", rec.date_to),
                ("state", "=", "close")
            ])
            risky_attrition = Eval.search_count([
                ("employee_id.department_id", "=", rec.department_id.id),
                ("date", ">=", rec.date_from),
                ("date", "<=", rec.date_to),
                ("pred_risk", "=", "high"),
            ])
            rec.departs_confirmes = ended_contracts + risky_attrition
            # turnover rate
            if rec.effectif_actuel > 0:
                rec.turnover_month_pct = (
                    rec.departs_confirmes / rec.effectif_actuel
                )

            # active candidates
            #cherche les poste de depart
            jobs = Job.search([
                ('department_id', '=', rec.department_id.id)
            ])
            rec.candidats_en_cours = Applicant.search_count([
                ('job_id', 'in', jobs.ids),
                ('application_status', '=', 'ongoing')
            ])

            # open positions : somme des recrutements prévus
            total_open = 0
            for job in jobs:
                total_open += job.no_of_recruitment or 0
            rec.postes_ouverts_actuels = total_open

    # ============================================================
    # MÉTHODE 4 : calcul des moyennes glissantes
    # ============================================================
    @api.depends("department_id", "quarter_num", "analysis_year")
    def _compute_rolling_means(self):
        """Calcule les moyennes glissantes sur 4 trimestres via boucles."""
        History = self.env["department.analysis.history"]
        metrics = [
            'departs_confirmes',
            'candidats_en_cours',
            'postes_ouverts_actuels',
            'effectif_actuel',
            'turnover_month_pct'
        ]

        for rec in self:
            # si info manquante, on remet toutes les moyennes à zéro
            if not (rec.department_id and rec.quarter_num and rec.analysis_year):
                for metric in metrics:
                    setattr(rec, f"{metric}_rolling_mean", 0.0)
                continue

            # construire la liste des 4 trimestres précédents
            lags = []
            current_q, current_y = rec.quarter_num, rec.analysis_year
            for _ in range(4):
                if current_q > 1:
                    current_q -= 1
                else:
                    current_q = 4
                    current_y -= 1
                lags.append((current_q, current_y))

            # récupérer chaque historique un par un
            records = []
            for q, y in lags:
                hist = History.search([
                    ('department_id', '=', rec.department_id.id),
                    ('quarter_num', '=', q),
                    ('analysis_year', '=', y)
                ], limit=1)
                if hist:
                    records.append(hist)

            # calculer et assigner la moyenne par métrique
            if records:
                count = len(records)
                for metric in metrics:
                    total = sum(getattr(r, metric) for r in records)
                    setattr(rec, f"{metric}_rolling_mean", total / count)
            else:
                for metric in metrics:
                    setattr(rec, f"{metric}_rolling_mean", 0.0)

    # ============================================================
    # MÉTHODE 5 : calcul des lags trimestriels
    # ============================================================
    @api.depends('department_id', 'quarter_num', 'analysis_year')
    def _compute_history_features_by_quarter(self):
        """Calcule les valeurs de lag Q1→Q4 via boucle."""
        History = self.env["department.analysis.history"]
        metrics = [
            'departs_confirmes',
            'candidats_en_cours',
            'postes_ouverts_actuels',
            'effectif_actuel',
            'turnover_month_pct'
        ]

        for rec in self:
            current_q, current_y = rec.quarter_num, rec.analysis_year

            # pour chaque lag i de 1 à 4
            for i in range(1, 5):
                # déterminer trimestre/année précédents
                if current_q > 1:
                    prev_q, prev_y = current_q - 1, current_y
                else:
                    prev_q, prev_y = 4, current_y - 1

                # requête de l’historique pour ce lag
                hist = History.search([
                    ('department_id', '=', rec.department_id.id),
                    ('quarter_num', '=', prev_q),
                    ('analysis_year', '=', prev_y)
                ], limit=1)

                # assigner tous les metrics dynamiquement
                for metric in metrics:
                    value = getattr(hist, metric) if hist else 0.0
                    setattr(rec, f"{metric}_lag_{i}", value)

                # préparer l’itération suivante
                current_q, current_y = prev_q, prev_y

    # ============================================================
    # MÉTHODE 6 : ACTION DE PRÉDICTION + HISTORISATION
    # ============================================================
    def action_calculate_prediction(self):
        self.ensure_one()
        # Calcul des KPI de base et rolling means
        self._compute_basic_metrics()
        self._compute_rolling_means()

        if not (self.department_id and self.date_from and self.date_to):
            raise UserError(_("Données manquantes : département ou dates non définis"))

        # Calcul des lags
        self._compute_history_features_by_quarter()

        # Préparation du payload à envoyer à l’API
        base = {
            'department': self.department_id.name,
            'departs_confirmes': self.departs_confirmes,
            'candidats_en_cours': self.candidats_en_cours,
            'postes_ouverts_actuels': self.postes_ouverts_actuels,
            'effectif_actuel': self.effectif_actuel,
            'turnover_month_pct': self.turnover_month_pct,
            'quarter_num': self.quarter_num,
            'annee': self.analysis_year,
        }
        # ajouter rolling means
        for metric in [
            'departs_confirmes', 'candidats_en_cours',
            'postes_ouverts_actuels', 'effectif_actuel',
            'turnover_month_pct'
        ]:
            base[f"{metric}_rolling_mean"] = getattr(self, f"{metric}_rolling_mean")

        # ajouter les lags dynamiquement
        for i in range(1, 5):
            for metric in [
                'departs_confirmes', 'candidats_en_cours',
                'postes_ouverts_actuels', 'effectif_actuel',
                'turnover_month_pct'
            ]:
                base[f"{metric}_lag_{i}"] = getattr(self, f"{metric}_lag_{i}") or 0.0

        # appel à l’API externe
        try:
            _logger.debug("Payload API : %s", base)
            resp = requests.post(API_URL, json=base, timeout=TIMEOUT)
            resp.raise_for_status()
            self.predicted_need = int(resp.json().get('prediction', 0))
            _logger.info("Prédiction reçue : %s", self.predicted_need)
        except Exception as e:
            _logger.error("Échec de la prédiction : %s", str(e))
            raise UserError(_("Échec de la prédiction : %s") % str(e))

        # historiser le résultat
        self.action_save_history()

    # ============================================================
    # MÉTHODE 7 : SAUVEGARDE EN HISTORIQUE
    # ============================================================
    def action_save_history(self):
        self.ensure_one()
        History = self.env["department.analysis.history"]

        # préparation des valeurs à écrire
        vals = {
            'department_id': self.department_id.id,
            'analysis_month': self.analysis_month,
            'analysis_year': self.analysis_year,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'quarter_num': self.quarter_num,
            'predicted_need': self.predicted_need,

        }
        # ajouter KPI de base + rolling means + lags
        for field_name in [
            'departs_confirmes', 'candidats_en_cours', 'postes_ouverts_actuels',
            'effectif_actuel', 'turnover_month_pct'
        ]:
            vals[field_name] = getattr(self, field_name)
            vals[f"{field_name}_rolling_mean"] = getattr(self, f"{field_name}_rolling_mean")

        for i in range(1, 5):
            for metric in [
                'departs_confirmes', 'candidats_en_cours',
                'postes_ouverts_actuels', 'effectif_actuel',
                'turnover_month_pct'
            ]:
                vals[f"{metric}_lag_{i}"] = getattr(self, f"{metric}_lag_{i}") or 0.0

        # création ou mise à jour
        existing = History.search([
            ('department_id', '=', self.department_id.id),
            ('analysis_month', '=', self.analysis_month),
            ('analysis_year', '=', self.analysis_year)
        ], limit=1)
        if existing:
            existing.write(vals)
            _logger.info(
                "Historique mis à jour : %s / %s-%s",
                self.department_id.name, self.analysis_month, self.analysis_year
            )
        else:
            History.create([vals])
            _logger.info(
                "Nouvel historique créé : %s / %s-%s",
                self.department_id.name, self.analysis_month, self.analysis_year
            )