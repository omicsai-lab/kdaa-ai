"""The fixed, development-stage opportunity catalog shared by every case (Freeze Section
9.2: "candidate catalog of 10 opportunities"; Checkpoint A/B simplification: one fixed
catalog reused across all development cases rather than a per-case catalog).

Everything in this module is *visible* content plus an inference-side ranking mechanism
derived only from that visible content -- it is safe for every comparator (C0-S, C1, C2,
C3, C4) to import. Hidden relevance grading now lives separately, in the truth-only
``opportunity_truth`` module, using an authored required/optional/disqualifying-concept
record per opportunity that is deliberately *not* the same association used here (see
that module's docstring for why the Checkpoint A circularity required decoupling the two,
not just moving the same table).

Each ``description`` packs the beneficiary, problem, and expected output a comparator is
allowed to see (Checkpoint B requirement) as plain, structured text -- kept inside the
existing WP1 ``OpportunityCandidate.description`` field rather than adding new schema
fields, since a plain-text package is sufficient and avoids changing a locked WP1 schema
for a Checkpoint B convenience.
"""

from __future__ import annotations

from kdaa.ontology import Ontology

from .schemas import OpportunityCandidate, PredictedOpportunity

DEV_OPPORTUNITY_CATALOG: tuple[OpportunityCandidate, ...] = (
    OpportunityCandidate(
        opportunity_id="opp-repository",
        title="Publish a maintained reusable repository",
        description=(
            "Beneficiary: other researchers who could reuse this work. Problem: the "
            "capability currently exists only as one-off code. Expected output: a "
            "documented, tested Python package with continuous integration. Context: "
            "best suited when the underlying work already resembles a software artifact."
        ),
    ),
    OpportunityCandidate(
        opportunity_id="opp-living-document",
        title="Create a living methods document",
        description=(
            "Beneficiary: collaborators who need to follow the same procedure. Problem: "
            "the method is not written down anywhere durable. Expected output: a "
            "version-controlled reproducibility document with workflow automation notes. "
            "Context: best suited when the work already emphasizes reproducible research."
        ),
    ),
    OpportunityCandidate(
        opportunity_id="opp-knowledge-base",
        title="Build a structured internal knowledge base",
        description=(
            "Beneficiary: the unit's own future members. Problem: knowledge assets are "
            "scattered across documents and memory. Expected output: an organized "
            "digital platform indexing organizational knowledge. Context: best suited "
            "for units with a large, varied evidence base."
        ),
    ),
    OpportunityCandidate(
        opportunity_id="opp-deployable-product",
        title="Ship a deployable product or tool",
        description=(
            "Beneficiary: external end users. Problem: the capability is a prototype, "
            "not a usable tool. Expected output: a minimum viable product or proof of "
            "concept ready for outside use. Context: best suited when a working "
            "prototype or production system already exists."
        ),
    ),
    OpportunityCandidate(
        opportunity_id="opp-public-content",
        title="Produce public educational content",
        description=(
            "Beneficiary: a general or student audience. Problem: the expertise is not "
            "accessible outside specialist venues. Expected output: a course or "
            "training-program explainer. Context: best suited when the unit already has "
            "a documented curriculum or teaching record."
        ),
    ),
    OpportunityCandidate(
        opportunity_id="opp-grant-proposal",
        title="Draft a grant proposal built on this capability",
        description=(
            "Beneficiary: a funding agency and the unit's future program. Problem: prior "
            "work has not been packaged as fundable preliminary evidence. Expected "
            "output: a proposal citing a completed clinical trial or protocol design. "
            "Context: best suited when the work includes a completed trial or study."
        ),
    ),
    OpportunityCandidate(
        opportunity_id="opp-benchmark-dataset",
        title="Release a benchmark dataset",
        description=(
            "Beneficiary: the broader research community. Problem: a valuable dataset is "
            "not packaged for reuse. Expected output: a versioned resource covering "
            "whole genome sequencing or comparable omics data. Context: best suited when "
            "the work already involves genome-scale data."
        ),
    ),
    OpportunityCandidate(
        opportunity_id="opp-training-course",
        title="Develop a training course",
        description=(
            "Beneficiary: learners inside or outside the unit. Problem: the underlying "
            "method is taught informally, if at all. Expected output: a structured "
            "course or syllabus. Context: best suited when the unit already has a "
            "documented curriculum or training program."
        ),
    ),
    OpportunityCandidate(
        opportunity_id="opp-consulting-service",
        title="Offer a consulting or advisory service",
        description=(
            "Beneficiary: external organizations facing a similar problem. Problem: the "
            "expertise is not offered as a service. Expected output: a formal advisory "
            "engagement drawing on organizational knowledge. Context: best suited when "
            "the unit has broad, applied, cross-project experience."
        ),
    ),
    OpportunityCandidate(
        opportunity_id="opp-methods-paper",
        title="Write a methods paper generalizing the approach",
        description=(
            "Beneficiary: the broader methodological literature. Problem: a useful "
            "causal or statistical model has not been generalized beyond one study. "
            "Expected output: a manuscript suitable for peer review. Context: best "
            "suited when the work already involves a causal model or estimand."
        ),
    ),
)


def rank_opportunities_by_visible_text(
    predicted_concept_labels: list[str],
    catalog: tuple[OpportunityCandidate, ...],
    ontology: Ontology,
) -> list[PredictedOpportunity]:
    """Inference-side opportunity ranking: overlap between concept mentions found in the
    comparator's *own predicted* concept labels and concept mentions found live in each
    opportunity's *own visible* title/description text.

    This never reads ``opportunity_truth`` and has no access to hidden requirement
    records -- it can only ever be as good as (a) what the comparator actually predicted
    and (b) what the visible description happens to say, which is the point: a comparator
    cannot get E4 credit merely by looking up an opportunity_id in an answer table.
    """
    predicted_keys: set[str] = set()
    for label in predicted_concept_labels:
        predicted_keys |= {match.key for match in ontology.match(label)}

    scored: list[tuple[str, int]] = []
    for candidate in catalog:
        visible_text = f"{candidate.title} {candidate.description}"
        opportunity_keys = {match.key for match in ontology.match(visible_text)}
        overlap = len(predicted_keys & opportunity_keys)
        scored.append((candidate.opportunity_id, overlap))
    scored.sort(key=lambda item: (-item[1], item[0]))

    return [
        PredictedOpportunity(
            opportunity_id=opportunity_id,
            rank=rank,
            rationale=f"Visible-text concept overlap with predicted concepts={score}.",
        )
        for rank, (opportunity_id, score) in enumerate(scored, start=1)
    ]
