# -*- coding: utf-8 -*-
import calendar
from datetime import date

from odoo import models, fields, api


class HrRecruitMonthHistory(models.Model):
    _name = "hr.recruit.month_history"
    _description = "Recruitment Monthly History"
    _order = "year desc, month desc, department_id"

    department_id = fields.Many2one(
        'hr.department',
        string="Department",
        required=True,
        index=True,
    )

    year = fields.Integer(string="Year", required=True, index=True)
    month = fields.Integer(string="Month", required=True, index=True)  # 1..12

    date_start = fields.Date(string="Start Date", compute="_compute_period", store=True)
    date_end = fields.Date(string="End Date", compute="_compute_period", store=True)

    # --- Effectifs ---
    headcount_start = fields.Integer(string="Headcount Start", compute="_compute_month_metrics", store=True)
    headcount_end = fields.Integer(string="Headcount End", compute="_compute_month_metrics", store=True)
    headcount_mean = fields.Integer(string="Headcount Mean", compute="_compute_headcount_mean", store=True)

    # --- Départs & turnover ---
    departures_month = fields.Integer(string="Departures", compute="_compute_month_metrics", store=True)
    turnover_month_pct = fields.Float(string="Monthly Turnover (%)", compute="_compute_turnover", store=True)

    # --- Candidats & postes ouverts ---
    applicants_in_progress_month = fields.Integer(
        string="Applicants In Progress",
        compute="_compute_month_metrics",
        store=True,
    )
    postes_ouverts_actuels = fields.Integer(
        string="Open Positions",
        compute="_compute_month_metrics",
        store=True,
    )

    computed_at = fields.Datetime(string="Computed At")

    # ----------------------------
    # Période (bornes du mois)
    # ----------------------------
    @api.depends('year', 'month')
    def _compute_period(self):
        for rec in self:
            if rec.year and rec.month and 1 <= rec.month <= 12:
                last_day = calendar.monthrange(rec.year, rec.month)[1]
                rec.date_start = date(rec.year, rec.month, 1)
                rec.date_end = date(rec.year, rec.month, last_day)
            else:
                rec.date_start = False
                rec.date_end = False

    # ----------------------------
    # Moyenne d'effectif
    # ----------------------------
    @api.depends('headcount_start', 'headcount_end')
    def _compute_headcount_mean(self):
        for rec in self:
            s = float(rec.headcount_start or 0)
            e = float(rec.headcount_end or 0)
            rec.headcount_mean = (s + e) / 2.0 if (s or e) else 0

    # ----------------------------
    # Turnover du mois
    # ----------------------------
    @api.depends('departures_month', 'headcount_mean')
    def _compute_turnover(self):
        for rec in self:
            rec.turnover_month_pct = (rec.departures_month / rec.headcount_mean) if rec.headcount_mean else 0.0

    # ----------------------------
    # KPI mensuels (compute unique)
    # ----------------------------
    @api.depends('department_id', 'date_start', 'date_end')
    def _compute_month_metrics(self):
        Contract = self.env['hr.contract']
        Applicant = self.env['hr.applicant']
        Job = self.env['hr.job']

        for rec in self:
            dep = rec.department_id
            ds, de = rec.date_start, rec.date_end

            # initialisation
            rec.headcount_start = 0
            rec.headcount_end = 0
            rec.departures_month = 0
            rec.applicants_in_progress_month = 0
            rec.postes_ouverts_actuels = 0



            # 1) Effectif début & fin de mois
            ## Compte des contrats du département actifs le jour `ds` (début de mois) :
            rec.headcount_start = Contract.search_count([
                ('employee_id.department_id', '=', dep.id),
                ('date_start', '<=', ds),
                '|', ('date_end', '=', False), ('date_end', '>=', ds),
            ])
            # Compte des contrats du département actifs le jour `de` (fin de mois) :
            rec.headcount_end = Contract.search_count([
                ('employee_id.department_id', '=', dep.id),
                ('date_start', '<=', de),
                '|', ('date_end', '=', False), ('date_end', '>=', de),
            ])

            # 2) Départs du mois = nb de contrats dont date_end ∈ [ds, de]
            rec.departures_month = Contract.search_count([
                ('employee_id.department_id', '=', dep.id),
                ('date_end', '>=', ds),
                ('date_end', '<=', de),
            ])

            # 3) Candidats "en cours"
            # commencé avant fin de mois et pas encore clôturé  ou clôturé après début de mois

            rec.applicants_in_progress_month = Applicant.search_count([
                ('job_id.department_id', '=', dep.id),
                ('create_date', '<', de),
                '|', ('date_closed', '=', False),
                     ('date_closed', '>=', ds),
            ])

            # 4) Postes ouverts
            jobs = Job.search([('department_id', '=', dep.id), ('active', '=', True)])
            rec.postes_ouverts_actuels = sum((job.no_of_recruitment or 0) for job in jobs)

            rec.computed_at = fields.Datetime.now()


class HrRecruitQuarterHistory(models.Model):
    _name = "hr.recruit.quarter_history"
    _description = "Recruitment Quarterly History (features ML)"
    _order = "annee desc, quarter_num desc, department_id"

    # ---------------------------
    # Clé & période
    # ---------------------------
    department_id = fields.Many2one("hr.department", string="Department", required=True, index=True)
    annee = fields.Integer(string="Year", required=True, index=True)
    quarter_num = fields.Integer(string="Quarter", required=True, index=True)

    quarter_start = fields.Date(string="Quarter Start", compute="_compute_quarter_bounds", store=True)
    quarter_end = fields.Date(string="Quarter End", compute="_compute_quarter_bounds", store=True)

    computed_at = fields.Datetime(string="Computed At")

    # ---------------------------
    # Base Q (simple features)
    # ---------------------------
    departs_confirmes = fields.Integer(string="Confirmed Departures")
    candidats_en_cours = fields.Integer(string="Candidates In Progress (Avg)")
    postes_ouverts_actuels = fields.Integer(string="Open Positions (Avg)")
    effectif_actuel = fields.Integer(string="Current Headcount (Avg)")
    turnover_month_pct = fields.Float(string="Monthly Turnover (%) (Avg)")

    # ---------------------------
    # Moy de 4 trimestres
    # ---------------------------
    departs_confirmes_rolling_mean = fields.Float(string="Departures - Rolling Mean")
    candidats_en_cours_rolling_mean = fields.Float(string="Candidates In Progress - Rolling Mean")
    postes_ouverts_actuels_rolling_mean = fields.Float(string="Open Positions - Rolling Mean")
    effectif_actuel_rolling_mean = fields.Float(string="Headcount - Rolling Mean")
    turnover_month_pct_rolling_mean = fields.Float(string="Monthly Turnover (%) - Rolling Mean")

    # ---------------------------
    # Exact lags Q-1..Q-4
    # ---------------------------
    departs_confirmes_lag_1 = fields.Integer(string="Departures Q-1")
    departs_confirmes_lag_2 = fields.Integer(string="Departures Q-2")
    departs_confirmes_lag_3 = fields.Integer(string="Departures Q-3")
    departs_confirmes_lag_4 = fields.Integer(string="Departures Q-4")

    candidats_en_cours_lag_1 = fields.Integer(string="Candidates In Progress Q-1")
    candidats_en_cours_lag_2 = fields.Integer(string="Candidates In Progress Q-2")
    candidats_en_cours_lag_3 = fields.Integer(string="Candidates In Progress Q-3")
    candidats_en_cours_lag_4 = fields.Integer(string="Candidates In Progress Q-4")

    postes_ouverts_actuels_lag_1 = fields.Integer(string="Open Positions Q-1")
    postes_ouverts_actuels_lag_2 = fields.Integer(string="Open Positions Q-2")
    postes_ouverts_actuels_lag_3 = fields.Integer(string="Open Positions Q-3")
    postes_ouverts_actuels_lag_4 = fields.Integer(string="Open Positions Q-4")

    effectif_actuel_lag_1 = fields.Integer(string="Headcount Q-1")
    effectif_actuel_lag_2 = fields.Integer(string="Headcount Q-2")
    effectif_actuel_lag_3 = fields.Integer(string="Headcount Q-3")
    effectif_actuel_lag_4 = fields.Integer(string="Headcount Q-4")

    turnover_month_pct_lag_1 = fields.Float(string="Monthly Turnover (%) Q-1")
    turnover_month_pct_lag_2 = fields.Float(string="Monthly Turnover (%) Q-2")
    turnover_month_pct_lag_3 = fields.Float(string="Monthly Turnover (%) Q-3")
    turnover_month_pct_lag_4 = fields.Float(string="Monthly Turnover (%) Q-4")

    # ---------------------------
    # Prediction & UI
    # ---------------------------
    predicted_need_next = fields.Integer(string="Predicted Need Q+1")

    show_lags = fields.Boolean(string="Show History (Lags)")

    # ===========================
    # Computes légers (période / dept)
    # ===========================

    # Calcule les dates de début/fin du trimestre
    @api.depends('annee', 'quarter_num')
    def _compute_quarter_bounds(self):
        for rec in self:
            if not rec.annee or rec.quarter_num not in (1, 2, 3, 4):
                rec.quarter_start = False
                rec.quarter_end = False
                continue
            first_month = (int(rec.quarter_num) - 1) * 3 + 1
            last_month = first_month + 2
            last_day = calendar.monthrange(rec.annee, last_month)[1]
            rec.quarter_start = date(rec.annee, first_month, 1)
            rec.quarter_end = date(rec.annee, last_month, last_day)

    # ===========================
    # Action: calculer
    # ===========================

    # mapping trimestre -> mois
    QUARTER_MONTHS = {
        1: (1, 2, 3),       # Q1 -> Jan, Feb, Mar
        2: (4, 5, 6),       # Q2 -> Apr, May, Jun
        3: (7, 8, 9),       # Q3 -> Jul, Aug, Sep
        4: (10, 11, 12),    # Q4 -> Oct, Nov, Dec
    }

    def _sum_months(self, months_recs, field_name):
        """Somme des valeurs mensuelles d'un champ donné."""
        total = 0
        for m in months_recs:
            val = getattr(m, field_name, 0) or 0
            total += val
        return total
        # Pour écrire du code plus générique, et éviter de dupliquer la logique on utilise getattr(obj(comme hr.recruit.month_history), "field", default)

    def _avg_months(self, months_recs, field_name):
        """Moyenne trimestrielle simple : somme / 3 mois."""
        return self._sum_months(months_recs, field_name) / 3.0

    def action_compute_quarter(self):
        """
        Cumule les 3 mois de hr.recruit.month_history :
          - Base Q : départs = total ; autres indicateurs = moyenne des 3 mois
          - Lags Q-1..Q-4 : valeurs des 4 trimestres précédents
          - Rolling means : moyenne calculée sur les 4 trimestres existants
        """
        Month = self.env['hr.recruit.month_history']
        QHist = self.env['hr.recruit.quarter_history']

        # métriques trimestrielles "base"
        base_metrics = [
            'departs_confirmes',
            'candidats_en_cours',
            'postes_ouverts_actuels',
            'effectif_actuel',
            'turnover_month_pct',
        ]

        for rec in self:
            # ==========
            # 1) les mois du trimestre  # exple months =(1, 2, 3)
            # ==========
            months = self.QUARTER_MONTHS[rec.quarter_num]

            # 2) chercher les lignes mensuelles du trimestre
            months_recs = Month.search([
                ('department_id', '=', rec.department_id.id),
                ('year', '=', rec.annee),
                ('month', 'in', months),
            ], order="year, month")

            # 3) Base Q
            rec.departs_confirmes = self._sum_months(months_recs, 'departures_month')
            rec.candidats_en_cours = self._avg_months(months_recs, 'applicants_in_progress_month')
            rec.postes_ouverts_actuels = self._avg_months(months_recs, 'postes_ouverts_actuels')
            rec.effectif_actuel = self._avg_months(months_recs, 'headcount_mean')
            rec.turnover_month_pct = self._avg_months(months_recs, 'turnover_month_pct')
            # ==========
            # 4) Lags Q-1..Q-4 :construire la liste (quarter,year) contiendra les 4 trimestres précédents

            # ==========
            # si (q,y)=(3, 2025) alors prev_list: [(2, 2025), (1, 2025), (4, 2024), (3, 2024)]
            prev_list = []
            q = int(rec.quarter_num)
            y = int(rec.annee)
            for _i in range(4):
                if q > 1:
                    q -= 1
                else:
                    q = 4
                    y -= 1
                prev_list.append((q, y))

            # Récupérer les lignes correspondantes depuis hr.recruit.quarter_history
            prev_recs = []
            for pq, py in prev_list:
                h = QHist.search([
                    ('department_id', '=', rec.department_id.id),
                    ('annee', '=', py),
                    ('quarter_num', '=', pq),
                ], limit=1)
                prev_recs.append(h if h else None)

            # Remplir les lags via boucles
            # enumerate(prev_recs, start=1) parcourt la liste prev_recs en donnant à la fois l’index (1,2,3,4)et l’élément.

            for idx, h in enumerate(prev_recs, start=1):

                for mname in base_metrics:
                    if h and h.id:
                        val = float(getattr(h, mname, 0.0) or 0.0)
                    else:
                        val = 0.0
                    setattr(rec, f"{mname}_lag_{idx}", val)
            # donc _lag_1 à _lag_4), et h pour lire la valeur de la métrique sur l’enregistrement trouvé.

            # 5) Rolling means = moyenne des Q existants parmi Q-1..Q-4
            for mname in base_metrics:
                vals = []
                for h in prev_recs:
                    if h and h.id:
                        vals.append(float(getattr(h, mname, 0.0) or 0.0))
                if vals:
                    avg_val = sum(vals) / float(len(vals))
                else:
                    avg_val = 0.0
                setattr(rec, f"{mname}_rolling_mean", avg_val)
                #On écrit sur rec le champ de moyenne glissante de la métrique (ex. headcount_end_rolling_mean) avec la moyenne calculée.

            # 6) Timestamp
            rec.computed_at = fields.Datetime.now()

        return True
         #recs = “records” enregistrements ,prev "previous" précédent.
