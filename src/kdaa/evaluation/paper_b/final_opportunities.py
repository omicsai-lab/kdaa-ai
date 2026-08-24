"""Case-specific visible opportunity catalogs for the final Paper B study (Freeze Section
6 / ``final_experiment_lock.yaml`` ``final_opportunity_design``).

**Correction** (this checkpoint): the first implementation kept the same 10 archetype
descriptions verbatim across every case and only appended a case-ID sentence -- that did
not satisfy "case-specific." This version keeps the same 10 fixed opportunity archetype
*identities* (``opportunity_id``, and the archetype's role/title) but instantiates each
description from context derived only from the case's own *visible* evidence: a
concept-mention theme found by running the ontology matcher over the evidence's own
searchable text (the same operation any comparator could legitimately perform), the
dominant visible trace types, and the focal unit's (visible) unit type. It never reads
``TruthBundle`` or anything from ``opportunity_truth`` -- ``build_case_opportunity_catalog``
takes only a ``UnitBundle`` and an ``Ontology``, so it is structurally incapable of being
influenced by hidden truth (there is no truth parameter to read).

Hidden grading is untouched and lives entirely in ``opportunity_truth``
(``OPPORTUNITY_REQUIREMENTS`` / ``compute_relevance_grade``), keyed by the exact same 10
``opportunity_id`` values used here -- the two mechanisms remain fully decoupled, per the
Checkpoint B E4-circularity fix this must not reintroduce.
"""

from __future__ import annotations

from collections import Counter

from kdaa.models import UnitBundle, UnitType
from kdaa.ontology import Ontology

from .schemas import OpportunityCandidate

_UNIT_TYPE_PHRASES: dict[UnitType, str] = {
    UnitType.RESEARCHER: "individual researcher",
    UnitType.TEAM: "project team",
    UnitType.LAB: "laboratory",
}

# (opportunity_id, title, description_template). Titles are the fixed archetype identity
# (kept from the original 10-archetype design); descriptions are format templates filled
# in per case from _extract_visible_context -- {domain_theme}, {artifact_mix}, and
# {unit_phrase} are the only substitution points, and all three come only from visible
# evidence (see _extract_visible_context).
_ARCHETYPE_TEMPLATES: tuple[tuple[str, str, str], ...] = (
    (
        "opp-repository",
        "Publish a maintained reusable repository",
        "Beneficiary: other researchers who could reuse this {domain_theme} work. Problem: "
        "the capability currently exists only as one-off {artifact_mix} produced by this "
        "{unit_phrase}. Expected output: a documented, tested package covering {domain_theme}. "
        "Context: best suited given the visible {artifact_mix} evidence mix for this case.",
    ),
    (
        "opp-living-document",
        "Create a living methods document",
        "Beneficiary: collaborators who need to follow the same {domain_theme} procedure. "
        "Problem: the method behind this {unit_phrase}'s {artifact_mix} is not written down "
        "anywhere durable. Expected output: a version-controlled document describing the "
        "{domain_theme} workflow. Context: best suited given the visible {artifact_mix} record.",
    ),
    (
        "opp-knowledge-base",
        "Build a structured internal knowledge base",
        "Beneficiary: this {unit_phrase}'s own future members. Problem: {domain_theme} "
        "knowledge is scattered across the visible {artifact_mix}. Expected output: an "
        "organized index of the {unit_phrase}'s {domain_theme} knowledge. Context: best "
        "suited for a case with a varied {artifact_mix} evidence base.",
    ),
    (
        "opp-deployable-product",
        "Ship a deployable product or tool",
        "Beneficiary: external end users of {domain_theme} capability. Problem: the visible "
        "{artifact_mix} shows a prototype, not a usable tool. Expected output: a minimum "
        "viable {domain_theme} product ready for outside use. Context: best suited when a "
        "working prototype already exists in the {artifact_mix} evidence.",
    ),
    (
        "opp-public-content",
        "Produce public educational content",
        "Beneficiary: a general or student audience interested in {domain_theme}. Problem: "
        "this {unit_phrase}'s {domain_theme} expertise is not accessible outside specialist "
        "venues. Expected output: an explainer built from the visible {artifact_mix}. "
        "Context: best suited when the {artifact_mix} already includes a teaching record.",
    ),
    (
        "opp-grant-proposal",
        "Draft a grant proposal built on this capability",
        "Beneficiary: a funding agency and this {unit_phrase}'s future {domain_theme} "
        "program. Problem: the visible {artifact_mix} has not been packaged as fundable "
        "preliminary evidence. Expected output: a proposal citing the {domain_theme} work. "
        "Context: best suited when the {artifact_mix} includes a completed study or protocol.",
    ),
    (
        "opp-benchmark-dataset",
        "Release a benchmark dataset",
        "Beneficiary: the broader {domain_theme} research community. Problem: a valuable "
        "{domain_theme} resource from the visible {artifact_mix} is not packaged for reuse. "
        "Expected output: a versioned {domain_theme} dataset release. Context: best suited "
        "when the {artifact_mix} already involves large-scale data.",
    ),
    (
        "opp-training-course",
        "Develop a training course",
        "Beneficiary: learners inside or outside this {unit_phrase}. Problem: the "
        "{domain_theme} method behind the visible {artifact_mix} is taught informally, if "
        "at all. Expected output: a structured {domain_theme} course or syllabus. Context: "
        "best suited when the {artifact_mix} already documents a curriculum.",
    ),
    (
        "opp-consulting-service",
        "Offer a consulting or advisory service",
        "Beneficiary: external organizations facing a similar {domain_theme} problem. "
        "Problem: this {unit_phrase}'s {domain_theme} expertise, visible in its "
        "{artifact_mix}, is not offered as a service. Expected output: a formal "
        "{domain_theme} advisory engagement. Context: best suited given broad, applied "
        "{artifact_mix} experience.",
    ),
    (
        "opp-methods-paper",
        "Write a methods paper generalizing the approach",
        "Beneficiary: the broader {domain_theme} methodological literature. Problem: the "
        "{domain_theme} approach visible in this {unit_phrase}'s {artifact_mix} has not "
        "been generalized beyond one case. Expected output: a manuscript suitable for peer "
        "review. Context: best suited given the visible {domain_theme} {artifact_mix} record.",
    ),
)

_FALLBACK_DOMAIN_THEME = "general professional"
_FALLBACK_ARTIFACT_MIX = "documented records"


def _extract_visible_context(evidence_bundle: UnitBundle, ontology: Ontology) -> dict[str, str]:
    """Derive template substitutions from *visible* evidence only -- the same information
    any comparator (including a generic LLM) already has access to. Never reads
    ``TruthBundle`` or any concept key authored on the truth side."""
    combined_text = "\n".join(trace.searchable_text for trace in evidence_bundle.traces)
    matches = ontology.match(combined_text)  # already sorted by (-count, label)
    top_labels = [match.label for match in matches[:2]]
    domain_theme = " and ".join(label.lower() for label in top_labels) if top_labels else _FALLBACK_DOMAIN_THEME

    trace_type_counts = Counter(trace.trace_type.value for trace in evidence_bundle.traces)
    top_trace_types = [trace_type for trace_type, _ in trace_type_counts.most_common(2)]
    artifact_mix = (
        " and ".join(trace_type.replace("_", " ") for trace_type in top_trace_types)
        if top_trace_types
        else _FALLBACK_ARTIFACT_MIX
    )

    unit_phrase = _UNIT_TYPE_PHRASES.get(evidence_bundle.unit.unit_type, "focal unit")
    return {"domain_theme": domain_theme, "artifact_mix": artifact_mix, "unit_phrase": unit_phrase}


def build_case_opportunity_catalog(evidence_bundle: UnitBundle, *, ontology: Ontology) -> tuple[OpportunityCandidate, ...]:
    """Exactly 10 visible opportunities, materially instantiated from ``evidence_bundle``'s
    own visible content -- never from hidden truth, which this function has no access to."""
    context = _extract_visible_context(evidence_bundle, ontology)
    return tuple(
        OpportunityCandidate(
            opportunity_id=opportunity_id,
            title=title,
            description=description_template.format(**context),
        )
        for opportunity_id, title, description_template in _ARCHETYPE_TEMPLATES
    )
