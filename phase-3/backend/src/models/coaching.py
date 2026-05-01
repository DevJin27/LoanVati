"""Feature perturbation coaching for scored applicants."""

from __future__ import annotations

from copy import deepcopy

from src.models.predict import CreditRiskPredictor


def _risk_bucket(score: float) -> str:
    if score < 0.4:
        return "Low"
    if score < 0.6:
        return "Uncertain"
    return "High"


def generate_coaching_tips(
    applicant_row: dict,
    predictor: CreditRiskPredictor,
    max_tips: int = 3,
) -> list[dict]:
    """Find actionable changes that improve the applicant's risk score."""
    features = deepcopy(applicant_row["feature_payload"])
    current_score = float(applicant_row["risk_score"])
    candidates: list[dict] = []

    scenarios = [
        ("credit_amount", "AMT_CREDIT", [0.9, 0.8, 0.7], "Reducing the loan amount"),
        ("annuity", "AMT_ANNUITY", [0.9, 0.8, 0.7], "Reducing the EMI burden"),
    ]

    for public_name, feature_name, multipliers, label in scenarios:
        if feature_name not in features or not features[feature_name]:
            continue
        current_value = float(features[feature_name])
        best_tip: dict | None = None
        for multiplier in multipliers:
            mutated = deepcopy(features)
            mutated[feature_name] = round(current_value * multiplier, 2)
            new_score = float(predictor.predict(mutated)["risk_score"])
            improvement = round(current_score - new_score, 4)
            if improvement <= 0.05:
                continue
            tip = {
                "feature": public_name,
                "current_value": current_value,
                "suggested_value": float(mutated[feature_name]),
                "score_improvement": improvement,
                "human_tip": (
                    f"{label} from Rs {current_value:,.0f} to Rs {mutated[feature_name]:,.0f} "
                    f"could move the applicant from {_risk_bucket(current_score)} toward "
                    f"{_risk_bucket(new_score)} risk."
                ),
            }
            if best_tip is None or tip["score_improvement"] > best_tip["score_improvement"]:
                best_tip = tip
        if best_tip:
            candidates.append(best_tip)

    return sorted(candidates, key=lambda item: item["score_improvement"], reverse=True)[:max_tips]
