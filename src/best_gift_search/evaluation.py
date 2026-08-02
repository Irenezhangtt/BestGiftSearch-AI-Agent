from __future__ import annotations

from statistics import mean

from .models import Evaluation, Recommendation, SearchIntent


def evaluate(intent: SearchIntent, recommendations: list[Recommendation]) -> Evaluation:
    """Deterministic Rubrics-as-Rewards baseline for offline/CI evaluation."""
    if not recommendations:
        return Evaluation(relevance=0, budget_fit=0, diversity=0, explainability=0, overall=0, passed=False, notes=["No recommendations returned"])
    relevance = mean(item.score for item in recommendations)
    budget_fit = 100 * sum(item.total_cost <= intent.budget for item in recommendations) / len(recommendations)
    diversity = 100 * len({item.product.category for item in recommendations}) / len(recommendations)
    explainability = 100 * sum(bool(item.reasons) for item in recommendations) / len(recommendations)
    overall = round(.4 * relevance + .25 * budget_fit + .15 * diversity + .2 * explainability, 1)
    notes = []
    if budget_fit < 75: notes.append("Fewer than 75% of results fit the delivered-cost budget")
    if diversity < 50: notes.append("Result categories are too similar")
    if relevance < 55: notes.append("Average relevance is below target")
    if not notes: notes.append("Recommendation set meets the MVP quality rubric")
    return Evaluation(relevance=round(relevance, 1), budget_fit=round(budget_fit, 1), diversity=round(diversity, 1), explainability=round(explainability, 1), overall=overall, passed=overall >= 65 and budget_fit >= 50, notes=notes)
