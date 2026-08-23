"""C2 -- generic evidence-linked LLM (Freeze Section 10, C2; protocol clarification PC-02).

Receives the same complete normalized evidence as C1, with stable trace IDs, and is asked
to cite those IDs for its candidate claims. It receives no KDAA ontology, bounded-claim
rules, attribution rules, epistemic state machine, assessment dimensions, or task/gate
planning structure -- the only difference from C1 is evidence-ID citation.

Not implemented: ``C2-RAG`` (selective retrieval) -- optional per PC-02 and not needed for
Checkpoint B; C2 here receives the complete evidence set, matching the primary C2
definition exactly.

Under the truth-import boundary: must only ever receive an ``InputSnapshot``.
"""

from __future__ import annotations

from kdaa.providers.base import JSONProvider

from ..schemas import PredictionBundle
from ..telemetry import AttemptStatus, ExperimentAttempt
from .llm_common import prediction_from_llm_response
from .llm_harness import build_experiment_attempt, call_llm_with_retries

COMPARATOR_ID = "C2"

SYSTEM_PROMPT = (
    "You are analyzing a description of a person's or team's documented professional "
    "activity. Each piece of evidence has a stable ID. Identify distinct, reusable "
    "capabilities, citing the evidence IDs that support each one, and rank a list of "
    "candidate opportunities by how well each one fits those capabilities. Return strict "
    "JSON matching the schema described in the user message. Do not include any text "
    "outside the JSON object."
)


def build_user_prompt(
    unit_name: str,
    unit_description: str,
    evidence_items: list[tuple[str, str]],
    opportunities: list[tuple[str, str, str]],
) -> str:
    evidence_block = "\n".join(f"[{trace_id}] {text[:600]}" for trace_id, text in evidence_items) or (
        "(no evidence provided)"
    )
    opportunity_block = "\n".join(
        f"{opportunity_id}: {title}. {description}" for opportunity_id, title, description in opportunities
    )
    return (
        f"Focal unit: {unit_name}. {unit_description}\n\n"
        f"Documented evidence (each item's stable ID is in brackets):\n{evidence_block}\n\n"
        f"Candidate opportunities (there are exactly {len(opportunities)}; rank ALL of "
        f"them from best fit to worst fit):\n{opportunity_block}\n\n"
        "Return JSON of the form: "
        '{"concepts": [{"label": "short capability name", '
        '"evidence_ids": ["the bracketed IDs of evidence that actually supports this"], '
        '"ownership": "focal_unit|shared|organizational|external|unresolved or null"}], '
        '"ranked_opportunity_ids": ["the given opportunity IDs, all of them, best fit first"]}. '
        "Only cite evidence IDs that were actually given to you. Return at most 10 concepts."
    )


def run_c2(
    *,
    provider: JSONProvider,
    unit_name: str,
    unit_description: str,
    evidence_items: list[tuple[str, str]],
    opportunities: list[tuple[str, str, str]],
    case_id: str,
    attempt_number: int = 1,
) -> ExperimentAttempt:
    user_prompt = build_user_prompt(unit_name, unit_description, evidence_items, opportunities)
    call_result = call_llm_with_retries(
        provider=provider,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        attempt_number=attempt_number,
    )
    prediction: PredictionBundle | None = None
    if call_result.status == AttemptStatus.SUCCESS and call_result.validated is not None:
        valid_trace_ids = {trace_id for trace_id, _ in evidence_items}
        prediction = prediction_from_llm_response(
            call_result.validated,
            case_id=case_id,
            comparator_id=COMPARATOR_ID,
            valid_trace_ids=valid_trace_ids,
        )
    return build_experiment_attempt(
        case_id=case_id,
        comparator_id=COMPARATOR_ID,
        attempt_number=attempt_number,
        call_result=call_result,
        prediction=prediction,
    )
