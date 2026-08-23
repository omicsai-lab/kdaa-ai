"""C1 -- generic single-shot LLM (Freeze Section 10, C1).

A strong but generic baseline. The prompt deliberately contains no KDAA terminology,
ontology, provenance requirement, bounded-claim requirement, epistemic states,
attribution rules, assessment dimensions, or human/AI task gates -- only a minimal
evaluation-neutral JSON schema for parseability (Freeze Section 10, C1: "A minimal
evaluation-neutral JSON schema MAY be required for parseability. That schema shall not
introduce KDAA design knowledge.").

C1 receives no per-trace evidence IDs and is not asked to cite evidence (that is C2's
distinguishing feature). Retains every intended attempt via the shared LLM harness (see
``llm_harness.py``); see ``tests/paper_b/test_c1_c2_prompts.py`` for the automated check
that this prompt contains no KDAA design language.

Under the truth-import boundary: must only ever receive an ``InputSnapshot``.
"""

from __future__ import annotations

from kdaa.providers.base import JSONProvider

from ..schemas import PredictionBundle
from ..telemetry import AttemptStatus, ExperimentAttempt
from .llm_common import prediction_from_llm_response
from .llm_harness import build_experiment_attempt, call_llm_with_retries

COMPARATOR_ID = "C1"

SYSTEM_PROMPT = (
    "You are analyzing a description of a person's or team's documented professional "
    "activity. Identify distinct, reusable capabilities and rank a list of candidate "
    "opportunities by how well each one fits those capabilities. Return strict JSON "
    "matching the schema described in the user message. Do not include any text outside "
    "the JSON object."
)


def build_user_prompt(unit_name: str, unit_description: str, evidence_texts: list[str], opportunities: list[tuple[str, str, str]]) -> str:
    evidence_block = "\n".join(f"- {text[:600]}" for text in evidence_texts) or "(no evidence provided)"
    opportunity_block = "\n".join(
        f"{opportunity_id}: {title}. {description}" for opportunity_id, title, description in opportunities
    )
    return (
        f"Focal unit: {unit_name}. {unit_description}\n\n"
        f"Documented evidence:\n{evidence_block}\n\n"
        f"Candidate opportunities (there are exactly {len(opportunities)}; rank ALL of "
        f"them from best fit to worst fit):\n{opportunity_block}\n\n"
        "Return JSON of the form: "
        '{"concepts": [{"label": "short capability name", '
        '"ownership": "focal_unit|shared|organizational|external|unresolved or null"}], '
        '"ranked_opportunity_ids": ["the given opportunity IDs, all of them, best fit first"]}. '
        "Return at most 10 concepts."
    )


def run_c1(
    *,
    provider: JSONProvider,
    unit_name: str,
    unit_description: str,
    evidence_texts: list[str],
    opportunities: list[tuple[str, str, str]],
    case_id: str,
    attempt_number: int = 1,
) -> ExperimentAttempt:
    user_prompt = build_user_prompt(unit_name, unit_description, evidence_texts, opportunities)
    call_result = call_llm_with_retries(
        provider=provider,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        attempt_number=attempt_number,
    )
    prediction: PredictionBundle | None = None
    if call_result.status == AttemptStatus.SUCCESS and call_result.validated is not None:
        prediction = prediction_from_llm_response(
            call_result.validated, case_id=case_id, comparator_id=COMPARATOR_ID
        )
    return build_experiment_attempt(
        case_id=case_id,
        comparator_id=COMPARATOR_ID,
        attempt_number=attempt_number,
        call_result=call_result,
        prediction=prediction,
    )
