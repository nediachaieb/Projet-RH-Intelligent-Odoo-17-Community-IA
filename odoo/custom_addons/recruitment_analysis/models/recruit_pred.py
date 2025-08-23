# -*- coding: utf-8 -*-
import calendar
import logging
from datetime import date

import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

API_URL = "http://fastapirecrut:8050/predict"
TIMEOUT = 15  # seconds


class HrRecruitAnalysis(models.Model):
    _name = "hr.recruit.analysis"
    _description = "Recruitment Analysis (UI + API + States)"
    _order = "annee desc, quarter_num desc, department_id"

    # ---------------------------
    # Contexte / clé
    # ---------------------------
    department_id = fields.Many2one('hr.department', required=True, index=True)
    annee = fields.Integer(required=True, index=True, string="Year")
    quarter_num = fields.Integer(required=True, string="Quarter")  # 1..4
    date_from = fields.Date(compute="_compute_quarter_bounds", store=True)
    date_to = fields.Date(compute="_compute_quarter_bounds", store=True)

    @api.constrains('quarter_num')
    def _check_quarter_num(self):
        for r in self:
            if r.quarter_num not in (1, 2, 3, 4):
                raise ValidationError(_("quarter_num must be in 1..4."))


    @api.depends('annee', 'quarter_num')
    def _compute_quarter_bounds(self):
        for r in self:
            if not (r.annee and r.quarter_num in (1, 2, 3, 4)):
                r.date_from = r.date_to = False
                continue
            first_month = (int(r.quarter_num) - 1) * 3 + 1
            last_month = first_month + 2
            last_day = calendar.monthrange(r.annee, last_month)[1]
            r.date_from = date(r.annee, first_month, 1)
            r.date_to = date(r.annee, last_month, last_day)
    # ---------------------------
    # États & timestamps
    # ---------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('computed', 'Computed'),
        ('predicted', 'Predicted'),
        ('saved', 'Saved'),
        ('error', 'Error'),
    ], default='draft')

    computed_at = fields.Datetime()
    predicted_at = fields.Datetime()
    saved_at = fields.Datetime()

    # lien vers la ligne trimestre utilisée
    history_q_id = fields.Many2one('hr.recruit.quarter_history', string="Quarter History", index=True)

    # ---------------------------
    # KPI & Features (copiés depuis quarter_history)
    # ---------------------------
    departs_confirmes = fields.Integer(store=True)
    candidats_en_cours = fields.Integer(store=True)
    postes_ouverts_actuels = fields.Integer(store=True)
    effectif_actuel = fields.Integer(store=True)
    turnover_month_pct = fields.Float(store=True)

    departs_confirmes_rolling_mean = fields.Float(store=True)
    candidats_en_cours_rolling_mean = fields.Float(store=True)
    postes_ouverts_actuels_rolling_mean = fields.Float(store=True)
    effectif_actuel_rolling_mean = fields.Float(store=True)
    turnover_month_pct_rolling_mean = fields.Float(store=True)

    departs_confirmes_lag_1 = fields.Integer(store=True)
    departs_confirmes_lag_2 = fields.Integer(store=True)
    departs_confirmes_lag_3 = fields.Integer(store=True)
    departs_confirmes_lag_4 = fields.Integer(store=True)

    candidats_en_cours_lag_1 = fields.Integer(store=True)
    candidats_en_cours_lag_2 = fields.Integer(store=True)
    candidats_en_cours_lag_3 = fields.Integer(store=True)
    candidats_en_cours_lag_4 = fields.Integer(store=True)

    postes_ouverts_actuels_lag_1 = fields.Integer(store=True)
    postes_ouverts_actuels_lag_2 = fields.Integer(store=True)
    postes_ouverts_actuels_lag_3 = fields.Integer(store=True)
    postes_ouverts_actuels_lag_4 = fields.Integer(store=True)

    effectif_actuel_lag_1 = fields.Integer(store=True)
    effectif_actuel_lag_2 = fields.Integer(store=True)
    effectif_actuel_lag_3 = fields.Integer(store=True)
    effectif_actuel_lag_4 = fields.Integer(store=True)

    turnover_month_pct_lag_1 = fields.Float(store=True)
    turnover_month_pct_lag_2 = fields.Float(store=True)
    turnover_month_pct_lag_3 = fields.Float(store=True)
    turnover_month_pct_lag_4 = fields.Float(store=True)

    # ---------------------------
    # Résultat ML minimal
    # ---------------------------
    prediction_value = fields.Integer(string="Predicted Need (Q+1)")

    # ===========================
    # Actions
    # ===========================
    def _copy_from_quarter(self, q):
        metrics = [
            'departs_confirmes', 'candidats_en_cours', 'postes_ouverts_actuels',
            'effectif_actuel', 'turnover_month_pct'
        ]
        for m in metrics:
            setattr(self, m, getattr(q, m, 0.0) or 0.0)
            setattr(self, f"{m}_rolling_mean", getattr(q, f"{m}_rolling_mean", 0.0) or 0.0)
        for i in range(1, 5):
            for m in metrics:
                setattr(self, f"{m}_lag_{i}", getattr(q, f"{m}_lag_{i}", 0.0) or 0.0)

    def action_compute(self):
        """1) calcule TOUTES les features dans le modèle trimestriel ,
        2) copie les features ici,
        3) passe en 'computed'."""
        QHist = self.env['hr.recruit.quarter_history']
        for r in self:
            if not (r.department_id and r.annee and r.quarter_num in (1, 2, 3, 4)):
                raise UserError(_("Please fill Department, Year and Quarter."))

            q = QHist.search([
                ('department_id', '=', r.department_id.id),
                ('annee', '=', r.annee),
                ('quarter_num', '=', r.quarter_num),
            ], limit=1)
            if not q:
                q = QHist.create({
                    'department_id': r.department_id.id,
                    'annee': r.annee,
                    'quarter_num': r.quarter_num,
                })

            # Agrège depuis le mensuel vers le trimestriel
            q.action_compute_quarter()

            # Copie les features du trimestriel vers l'analyse
            r._copy_from_quarter(q)

            # Écritures groupées
            r.write({
                'history_q_id': q.id,
                'computed_at': fields.Datetime.now(),
                'state': 'computed',
            })
        return True

    def _build_payload(self):
        self.ensure_one()
        base_metrics = [
            'departs_confirmes', 'candidats_en_cours', 'postes_ouverts_actuels',
            'effectif_actuel', 'turnover_month_pct',
        ]
        payload = {
            'annee': self.annee or 0,
            'quarter_num': self.quarter_num or 0,
            'department': self.department_id.name or '',
        }
        for m in base_metrics:
            payload[m] = getattr(self, m) or 0.0
            payload[f"{m}_rolling_mean"] = getattr(self, f"{m}_rolling_mean") or 0.0
            for i in range(1, 5):
                payload[f"{m}_lag_{i}"] = getattr(self, f"{m}_lag_{i}") or 0.0
        return payload

    def action_predict(self):
        """Appel API -> prediction_value ; passe en 'predicted' ou 'error' (simple)."""
        for r in self:
            try:
                resp = requests.post(API_URL, json=r._build_payload(), timeout=TIMEOUT)
                pred = (resp.json().get('prediction') if resp else 0) or 0.0
                r.prediction_value = pred
                r.predicted_at = fields.Datetime.now()
                r.state = 'predicted'
            except Exception:
                r.state = 'error'
                raise UserError(_("La prédiction a échoué."))
        return True

    def action_save(self):
        """Écrit la prédiction sur la ligne trimestre (predicted_need_next) et passe en 'saved'."""
        for r in self:
            if r.state not in ('predicted', 'saved'):
                raise UserError(_("No prediction to save."))
            if not r.history_q_id:
                raise UserError(_("No quarter_history linked. Compute first."))

            r.history_q_id.write({'predicted_need_next': r.prediction_value or 0.0})
            r.write({
                'saved_at': fields.Datetime.now(),
                'state': 'saved',
            })
        return True

    def action_reset_to_draft(self):
        """Revient en draft : on vide la prédiction (les KPI restent tels quels).
        Côté UI, les KPI seront masqués uniquement en draft (modifiers XML).
        """
        for r in self:
            r.write({
                'prediction_value': 0.0,
                'predicted_at': False,
                'state': 'draft',
            })
        return True
