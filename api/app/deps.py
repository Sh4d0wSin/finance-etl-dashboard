from typing import Generator
from .db import SessionLocal

from fastapi import Header, HTTPException
from .settings import settings



def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_api_key(x_api_key: str = Header(default=None)):
    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")

