from __future__ import annotations

from datetime import date
from pydantic import BaseModel


class TransactionOut(BaseModel):
    id: int
    date: date
    description: str
    amount: float
    category: str
    account: str | None
    currency: str | None

    model_config = {"from_attributes": True}


class TransactionPage(BaseModel):
    limit: int
    offset: int
    total: int
    items: list[TransactionOut]


class CategorySummary(BaseModel):
    category: str
    total: float

class TimeBucket(BaseModel):
    bucket: date
    total: float

class IngestResult(BaseModel):
    filename: str
    rows_received: int
    rows_inserted: int
    rows_skipped_empty: int
    rows_skipped_duplicates: int
    rows_failed: int
    sample_errors: list[dict]

class HealthResponse(BaseModel):
    status: str







