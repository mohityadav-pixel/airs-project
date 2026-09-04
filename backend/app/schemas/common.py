"""Shared response envelopes.

``DataProvenance`` is deliberately attached to *every* data-bearing response.
The AIRS product promise is that a user can always tell whether a number was
measured, forecast, simulated or written by a language model — that guarantee
is enforced here, in the type system, not by convention.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class DataKind(str, Enum):
    observed = "observed"      # measured by a monitoring station
    predicted = "predicted"    # ML forecast
    simulated = "simulated"    # what-if scenario output
    estimated = "estimated"    # model-based attribution (e.g. source split)
    ai_generated = "ai_generated"  # LLM prose grounded on the above


class SourceMode(str, Enum):
    live = "live"
    cached = "cached"
    demo = "demo"


class DataProvenance(BaseModel):
    kind: DataKind
    mode: SourceMode = SourceMode.live
    source: str = Field(description="Human-readable origin, e.g. 'WAQI / AQICN'.")
    observed_at: datetime | None = None
    generated_at: datetime | None = None
    note: str | None = None
    is_stale: bool = False


class Envelope(BaseModel, Generic[T]):
    data: T
    provenance: DataProvenance


class Message(BaseModel):
    message: str
