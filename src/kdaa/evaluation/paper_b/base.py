"""Shared strict base model for Paper B evaluation-layer schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictEvalModel(BaseModel):
    """Base for Paper B evaluation-layer records: unknown fields are rejected and
    assignment is re-validated, mirroring the strictness of the production ``StrictModel``
    in ``kdaa.models`` without coupling the evaluation layer to it.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)
