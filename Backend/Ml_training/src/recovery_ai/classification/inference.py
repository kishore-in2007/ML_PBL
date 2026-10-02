from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class RiskPrediction:
    label: str
    confidence: float
    routed_to_human: bool
    raw_label: str


def predict_risk(
    logits: torch.Tensor,
    class_names: list[str],
    confidence_threshold: float = 0.7,
    human_review_label: str = "needs_clinician_review",
) -> list[RiskPrediction]:
    probabilities = torch.softmax(logits, dim=1)
    confidences, indices = torch.max(probabilities, dim=1)

    predictions: list[RiskPrediction] = []
    for confidence, index in zip(confidences.tolist(), indices.tolist()):
        raw_label = class_names[index]
        routed = confidence < confidence_threshold
        label = human_review_label if routed else raw_label
        predictions.append(
            RiskPrediction(
                label=label,
                confidence=float(confidence),
                routed_to_human=routed,
                raw_label=raw_label,
            )
        )
    return predictions


def should_escalate_from_symptoms(symptom_text: str) -> bool:
    severe_terms = {
        "severe pain",
        "fever",
        "pus",
        "bad smell",
        "bleeding",
        "infected",
        "red streak",
        "dizzy",
    }
    normalized = symptom_text.lower()
    return any(term in normalized for term in severe_terms)
