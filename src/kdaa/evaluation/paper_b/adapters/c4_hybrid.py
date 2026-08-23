"""C4 -- KDAA hybrid adapter (Freeze Section 10, C4).

Reuses the existing production ``KDAAPipeline`` unchanged (``mode="hybrid"``, which
already merges deterministic and LLM-assisted discovery via ``_merge_assets`` -- see
``kdaa.pipeline``) with an explicit shared provider, and maps its output via the same
``kdaa_common.adapt_kdaa_run`` helper C3 uses. No production code is modified or
redesigned.

Production ``discover_with_llm`` does not retry on failure, so this adapter wraps the
pipeline call in the same retry/failure-classification policy as C1/C2
(``llm_harness.classify_exception``, max 2 automatic retries) at the adapter level only --
this does not change production pipeline behavior for any other caller.

If C4 remains conservative and every discovered asset's ``ownership_state`` is
``UNRESOLVED`` (WP2's current, deliberate default -- no ownership-inference rule exists
yet), that is preserved here unchanged; no ownership inference is added to make E3 look
better (Checkpoint B Section 4 guardrail).

Under the truth-import boundary: must only ever receive a ``UnitBundle``/``InputSnapshot``.
"""

from __future__ import annotations

import time
import uuid
from datetime import date

from kdaa.config import KDAAConfig
from kdaa.models import UnitBundle
from kdaa.ontology import Ontology
from kdaa.pipeline import KDAAPipeline
from kdaa.providers.base import JSONProvider

from ..schemas import InputSnapshot
from ..telemetry import AttemptStatus, ExperimentAttempt, ResourceUsage
from .kdaa_common import adapt_kdaa_run
from .llm_harness import MAX_AUTOMATIC_RETRIES, classify_exception

COMPARATOR_ID = "C4"


def run_c4(
    bundle: UnitBundle,
    snapshot: InputSnapshot,
    ontology: Ontology,
    provider: JSONProvider,
    *,
    as_of_date: date,
    attempt_number: int = 1,
    max_retries: int = MAX_AUTOMATIC_RETRIES,
) -> ExperimentAttempt:
    status = AttemptStatus.OTHER_FAILURE
    error_message = ""
    prediction = None
    attempts_made = 0
    started = time.monotonic()

    config = KDAAConfig(mode="hybrid", as_of_date=as_of_date)
    while attempts_made <= max_retries:
        attempts_made += 1
        try:
            pipeline = KDAAPipeline(config, ontology=ontology, provider=provider)
            run, _ = pipeline.analyze(bundle)
            prediction = adapt_kdaa_run(run, snapshot, ontology, comparator_id=COMPARATOR_ID)
            status = AttemptStatus.SUCCESS
            error_message = ""
            break
        except Exception as exc:  # noqa: BLE001 -- deliberately broad, classified below
            status = classify_exception(exc)
            error_message = str(exc)
            prediction = None
            continue

    latency = time.monotonic() - started
    resource_usage = ResourceUsage(
        provider="dev-provider",
        model_identifier=getattr(provider, "model_name", ""),
        attempt_number=attempt_number,
        latency_seconds=latency,
    )
    return ExperimentAttempt(
        attempt_id=str(uuid.uuid4()),
        case_id=snapshot.case_id,
        comparator_id=COMPARATOR_ID,
        attempt_number=attempt_number,
        status=status,
        prediction=prediction,
        error_message=error_message,
        resource_usage=resource_usage,
    )
