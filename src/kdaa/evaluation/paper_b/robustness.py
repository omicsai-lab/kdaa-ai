"""Essential development robustness perturbations only (Checkpoint B Section 10): R1, R2,
R3. R4 (opportunity-context reversal) is not implemented this checkpoint (optional, and
skipped to keep scope tight per the "do not implement more robustness families" guardrail).

Each perturbation transforms a case's evidence ``UnitBundle`` before re-running a
comparator; the caller compares the perturbed run's predictions/scores against the
unperturbed baseline run for the same case (mirroring the existing
``kdaa.evaluation.robustness`` v0.1 pattern, generalized to Paper B's evaluation-neutral
scoring instead of raw asset signatures).
"""

from __future__ import annotations

import re
from datetime import date

from kdaa.ingestion.synthetic import NOISE_BLUEPRINTS
from kdaa.models import ContributionRole, EvidenceTrace, SourceKind, UnitBundle


def r1_exact_duplicate(bundle: UnitBundle) -> UnitBundle:
    """R1a -- add an exact duplicate of the first trace (same normalized content, no
    stronger source identity). Measures whether claims/support/ranking inflate."""
    if not bundle.traces:
        return bundle
    duplicate = bundle.traces[0].model_copy(update={"id": f"{bundle.traces[0].id}-r1-exact-dup"})
    return bundle.model_copy(update={"traces": [*bundle.traces, duplicate]})


def r1_source_equivalent_duplicate(bundle: UnitBundle) -> UnitBundle:
    """R1b -- add a source-record-equivalent duplicate (same strong source_record_id,
    different wording/title) of the first trace."""
    if not bundle.traces:
        return bundle
    original = bundle.traces[0].model_copy(update={"source_record_id": "robustness-r1-strong-source-id"})
    equivalent = original.model_copy(
        update={"id": f"{original.id}-r1-source-equiv", "title": f"{original.title} (alternate segment)"}
    )
    traces = list(bundle.traces)
    traces[0] = original
    traces.append(equivalent)
    return bundle.model_copy(update={"traces": traces})


def r2_substantial_irrelevant_evidence(bundle: UnitBundle, *, n_noise: int = 5) -> UnitBundle:
    """R2 -- inject a substantial amount of irrelevant administrative evidence (the
    documented "OR substantial irrelevant evidence" alternative to a contradictory trace).
    Measures E1/E2 change and claim/ranking stability under noise."""
    noise_traces: list[EvidenceTrace] = []
    for index in range(n_noise):
        blueprint = NOISE_BLUEPRINTS[index % len(NOISE_BLUEPRINTS)]
        noise_traces.append(
            EvidenceTrace(
                id=f"{bundle.unit.id}-r2-noise-{index:02d}",
                unit_id=bundle.unit.id,
                trace_type=blueprint["trace_type"],
                title=str(blueprint["title"]),
                description=str(blueprint.get("description", "")),
                source_kind=SourceKind.SYNTHETIC,
                source_name="KDAA Paper B robustness generator",
                event_date=date(2024, 1, 1),
                contribution_role=ContributionRole.PARTICIPANT,
            )
        )
    return bundle.model_copy(update={"traces": [*bundle.traces, *noise_traces]})


# Held-out paraphrases for term phrases that actually occur in the development
# generator's output (verified against kdaa.ontology.Ontology.match on generated
# evidence -- an earlier version of this list used plausible-sounding phrases that never
# actually appeared in generated text, silently making R3 a no-op; see
# tests/paper_b/test_robustness.py::test_r3_actually_changes_matchable_terms and the
# Checkpoint B report for that discovered-and-fixed defect). Replacements are
# deliberately not the ontology's own declared terms (kdaa.resources.ontology.yaml), so
# a shifted case tests whether the system degrades gracefully when evidence uses
# synonyms the concept vocabulary was not authored with.
_SURFACE_SHIFT_SUBSTITUTIONS: dict[str, str] = {
    "agentic ai": "autonomous multi-step AI system",
    "bioinformatics": "computational life-science analysis",
    "reproducibility": "independent replicability",
    "clinical trials": "controlled treatment studies",
    "clinical trial": "controlled treatment study",
    "genomics": "whole-genome profiling",
    "generative ai": "large-scale generative modeling",
    "research computing": "scientific infrastructure computing",
}


def r3_ontology_surface_shift(bundle: UnitBundle) -> UnitBundle:
    """R3 -- replace canonical ontology term phrases with held-out synonyms/paraphrases
    not in the production concept vocabulary's own term list. Measures graceful
    degradation in E1/E2 under surface-form shift.

    Shifts every field ``EvidenceTrace.searchable_text`` draws on (title, description,
    abstract, content, keywords, topics) -- an earlier version shifted only title/
    description and left keywords untouched, so the original matchable term still leaked
    through ``searchable_text`` and this perturbation was silently a no-op for concept
    recognition; see the Checkpoint B report and
    ``tests/paper_b/test_robustness.py::test_r3_actually_changes_matchable_terms``.
    """

    def shift(text: str) -> str:
        shifted = text
        for old, new in _SURFACE_SHIFT_SUBSTITUTIONS.items():
            shifted = re.sub(re.escape(old), new, shifted, flags=re.IGNORECASE)
        return shifted

    def shift_list(values: list[str]) -> list[str]:
        return [shift(value) for value in values]

    shifted_traces = [
        trace.model_copy(
            update={
                "title": shift(trace.title),
                "description": shift(trace.description),
                "abstract": shift(trace.abstract),
                "content": shift(trace.content),
                "keywords": shift_list(trace.keywords),
                "topics": shift_list(trace.topics),
            }
        )
        for trace in bundle.traces
    ]
    return bundle.model_copy(update={"traces": shifted_traces})
