"""Truth-leakage validation for Paper B development cases (Freeze Section 9.4).

Deliberately structural, not a free-text substring scan. A true concept's canonical
label or alias overlapping with evidence trace *wording* is not leakage -- it is exactly
what makes a trace supportive of that concept in the first place (a trace titled
"...bioinformatics..." legitimately supporting a true "bioinformatics" concept is normal,
expected data, not a leak). Scanning evidence text for truth-label substrings therefore
produces false positives on realistic data and was rejected during Checkpoint A
development in favor of two structural checks that do not have that problem:

1. **Suspicious metadata keys**: ``UnitBundle.metadata`` must not contain a key shaped
   like the pre-Paper-B anti-pattern this repository's own legacy benchmark generator
   uses (``ground_truth_concepts``, ``ground_truth_asset_keys``, etc. -- see
   ``kdaa.ingestion.synthetic.SyntheticBenchmarkGenerator``) or any key literally equal to
   a true concept's ``concept_id``. This is the realistic failure mode: reusing that
   existing pattern for a Paper B case instead of a separate ``TruthBundle``.
2. **Schema containment**: ``InputSnapshot`` is ``extra="forbid"`` (WP1), so no field
   beyond its declared schema can be smuggled onto it at all -- this is enforced by
   construction, not by this module, and is asserted here only as a documented guarantee
   for tests to exercise directly.

This module is truth-authorized tooling (it imports ``TruthBundle``) and must itself
never be imported by inference-side code -- it is not re-exported from
``kdaa.evaluation.paper_b.__init__`` and is not under an inference boundary prefix.
"""

from __future__ import annotations

from kdaa.models import UnitBundle

from .truth import TruthBundle

_SUSPICIOUS_METADATA_KEY_MARKERS = (
    "ground_truth",
    "true_concept",
    "true_label",
    "true_ownership",
    "hidden_relevance",
    "hidden_truth",
    "truth_bundle",
)


class LeakageError(RuntimeError):
    """Raised when a leakage validator finds truth-only content in an inference-visible
    object."""


def check_no_metadata_leakage(bundle: UnitBundle, truth: TruthBundle) -> list[str]:
    """Return a list of problems (empty if none) if ``UnitBundle.metadata`` contains a
    key shaped like known truth-leakage anti-patterns, or a key literally matching a true
    concept's internal ``concept_id``.
    """
    problems: list[str] = []
    truth_concept_ids = {concept.concept_id for concept in truth.asset_concepts}
    for key in bundle.metadata:
        normalized_key = str(key).lower()
        if any(marker in normalized_key for marker in _SUSPICIOUS_METADATA_KEY_MARKERS):
            problems.append(f"UnitBundle.metadata has a truth-shaped key: {key!r}")
        if key in truth_concept_ids:
            problems.append(f"UnitBundle.metadata key matches a true concept_id: {key!r}")
    return problems


def validate_case_leakage(bundle: UnitBundle, truth: TruthBundle, snapshot: object | None = None) -> None:
    """Raise ``LeakageError`` if any check fails; otherwise return ``None``.

    ``snapshot`` is accepted for call-site convenience (the development pilot always has
    one available) but is not itself scanned: ``InputSnapshot``'s ``extra="forbid"``
    schema already makes it structurally impossible to attach an out-of-schema truth
    field to it, so there is nothing this function could usefully check on it beyond what
    pydantic validation already guarantees at construction time.
    """
    problems = check_no_metadata_leakage(bundle, truth)
    if problems:
        raise LeakageError("; ".join(problems))
