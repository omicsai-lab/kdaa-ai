"""C3 -- KDAA deterministic adapter (Freeze Section 10, C3).

Reuses the existing production ``KDAAPipeline`` unchanged (deterministic mode) and maps
its valid output into the WP1 evaluation-neutral schema via ``kdaa_common.adapt_kdaa_run``
(shared with C4). This is a thin translation layer, not a reimplementation: no discovery,
scoring, or opportunity logic is duplicated or redesigned here.

Opportunity ranking uses ``opportunity_catalog.rank_opportunities_by_visible_text``
(Checkpoint B E4 fix), not a hidden lookup table shared with truth generation -- see that
module's docstring and ``kdaa.evaluation.paper_b.opportunity_truth``.

This module is under the truth-import boundary (see ``kdaa.evaluation.paper_b.boundary``):
it must only ever receive a ``UnitBundle``/``InputSnapshot``, never a ``TruthBundle``.
"""

from __future__ import annotations

from datetime import date

from kdaa.config import KDAAConfig
from kdaa.models import UnitBundle
from kdaa.ontology import Ontology
from kdaa.pipeline import KDAAPipeline

from ..schemas import InputSnapshot, PredictionBundle
from .kdaa_common import adapt_kdaa_run

COMPARATOR_ID = "C3"


def run_c3(
    bundle: UnitBundle,
    snapshot: InputSnapshot,
    ontology: Ontology,
    *,
    as_of_date: date,
) -> PredictionBundle:
    """Run the unmodified production deterministic pipeline and adapt its output.

    ``snapshot`` is used only for its opportunity catalog (the exact 10 IDs to rank) and
    to confirm the case_id; the evidence itself comes from ``bundle`` because the
    production pipeline requires a real ``UnitBundle``, not the evaluation-neutral
    ``InputSnapshot``.
    """
    config = KDAAConfig(mode="deterministic", as_of_date=as_of_date)
    pipeline = KDAAPipeline(config, ontology=ontology)
    run, _ = pipeline.analyze(bundle)
    return adapt_kdaa_run(run, snapshot, ontology, comparator_id=COMPARATOR_ID)
