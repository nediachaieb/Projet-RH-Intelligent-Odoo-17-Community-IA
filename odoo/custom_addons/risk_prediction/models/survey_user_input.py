# -*- coding: utf-8 -*-
import logging
from odoo import models, api, fields

_logger = logging.getLogger(__name__)



class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    def write(self, vals):
        # Appel à la méthode parente
        result = super(SurveyUserInput, self).write(vals)
        # Vérification de la fin du questionnaire
        if 'state' in vals and vals['state'] == 'done':
            for record in self:
                if record.state == 'done':
                    _logger.info("Survey %s done → compute category scores", record.id)
                    record._push_scores_to_employee()
        return result

    def _push_scores_to_employee(self):
        self.ensure_one()
        _logger.info("Starting _push_scores_to_employee for survey_user_input %s", self.id)

        # Mapping des labels (categorie) et champs
        label_to_field = {
            'Job Satisfaction': 'job_satisfaction',
            'Work–Life Balance': 'work_life_balance',
            'Leadership Opportunities': 'leadership_opportunities',
            'Innovation Opportunities': 'innovation_opportunities',
            'Company Reputation': 'company_reputation',
            'Employee Recognition': 'employee_recognition',
        }

        # Niveaux qualitatifs
        levels_map = {
            'Job Satisfaction': ['low', 'medium', 'high', 'very_high'],
            'Work–Life Balance': ['poor', 'fair', 'good', 'excellent'],
            'Leadership Opportunities': ['no', 'yes'],
            'Innovation Opportunities': ['no', 'yes'],
            'Company Reputation': ['poor', 'fair', 'good', 'excellent'],
            'Employee Recognition': ['low', 'medium', 'high', 'very_high'],
        }

        # Seuils => x<=25 idx=0 ; 25<x<=50 idx=1 ; 50<x<=75 ; x>75
        ## si binaire : x <= 25 idx = 0 si nn idx=1
        thresholds = [25, 50, 75]

        # 1) Compter les questions par catégorie
        question_counts = {}
        for label in levels_map:
            count = 0
            # Parcours des questions du sondage
            for question in self.survey_id.question_ids:
                if not question.is_page:
                    # Vérifie si la question a cette catégorie
                    for category in question.category_ids:
                        if category.name == label:
                            count += 1
                            break
            question_counts[label] = count
        _logger.info("Defined question counts per category: %s", question_counts)

        # 2) Initialiser totaux et compteurs de réponses
        totals = {} # somme des scores (50+75+..)
        response_counts = {} # nbr de questions repondus
        for label in levels_map:
            totals[label] = 0.0
            response_counts[label] = 0

        # 3) Parcours des réponses
        for line in self.user_input_line_ids:
            # Récupère le label de la catégorie
            cat_label = False
            if line.question_id.category_ids:
                cat_label = line.question_id.category_ids[0].name
            if cat_label not in totals:
                _logger.warning("No valid category for question %s", line.question_id.id)
                continue
            # Récupère le score
            val = line.answer_score or 0.0
            totals[cat_label] += val
            response_counts[cat_label] += 1
            _logger.debug("Adding %s to category %s", val, cat_label)
        _logger.info("Provided response counts per category: %s", response_counts)

        # 4) Calcul des pourcentages et niveaux
        results = {}
        for label in levels_map:
            total = totals[label]
            cnt = response_counts[label]
            pct = total / cnt if cnt > 0 else 0.0
            # niveaux dans le categorie
            lvl_list = levels_map[label]
            # Déterminer l'index du niveau
            idx = len(thresholds)
            for i in range(len(thresholds)):
                if pct <= thresholds[i]:
                    idx = i
                    break
            # Choix du niveau si binaire (yes or no )

            if len(lvl_list) == 2:
                level = lvl_list[1] if idx > 0 else lvl_list[0]
            else:
                level = lvl_list[idx]
            results[label] = {
                'total': total,
                'count': cnt,
                'percentage': pct,
                'level': level,
            }
            _logger.debug(
                "Cat %s → total=%s count=%s pct=%.1f lvl=%s",
                label, total, cnt, pct, level
            )

        # 5) Préparation des mises à jour pour hr.employee
        updates = {} # Contient les champs à mettre à jour dans `hr.employee`.
        for label, data in results.items():
            field_key = label_to_field[label]
            if question_counts[label] > 0:

                updates[field_key] = data['level']

        # 6) Mise à jour de l'employé et message
        employees = self.partner_id.user_ids.mapped('employee_ids')
        if not employees:
            _logger.warning("No employee found for partner %s", self.partner_id.id)
            return {
                'question_counts': question_counts,
                'response_counts': response_counts,
                'results': results,
                'error': 'no_employee',
            }
        emp = employees[0]
        _logger.info("Updating employee %s with scores %s", emp.id, updates)
        emp.sudo().write(updates)


        #  Retour debug
        return {
            'question_counts': question_counts,
            'response_counts': response_counts,
            'results': results,
        }