from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from sqlalchemy import text, select, func, Date as SA_Date
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

import csv
import io
import re
import hashlib

from decimal import Decimal, InvalidOperation
from sqlalchemy.exc import IntegrityError

from .deps import get_db, require_api_key





import pandas as pd



from .db import engine

from .models import Transaction
from .categorizer import categorize


from .schemas import (
    HealthResponse,
    IngestResult,
    TransactionPage,
    CategorySummary,
    TimeBucket,
)








app = FastAPI(title="Finance ETL Dashboard API")


_DELIMITERS = [",", ";", "\t", "|"]


def _detect_delimiter(text: str) -> str:
    sample = text[:10_000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="".join(_DELIMITERS))
        return dialect.delimiter
    except Exception:
        # fallback heuristic
        return ";" if sample.count(";") > sample.count(",") else ","


def _read_csv_bytes(content: bytes) -> pd.DataFrame:
    # utf-8-sig handles BOM that some bank exports include
    text = content.decode("utf-8-sig", errors="replace")
    sep = _detect_delimiter(text)
    return pd.read_csv(
        io.StringIO(text),
        sep=sep,
        dtype=str,              # keep raw strings; we parse ourselves
        skip_blank_lines=True,
    )

def _strip_and_drop_empty_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    # strip whitespace in every cell
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    # treat empty strings as NA so we can drop truly empty rows
    df = df.replace({"": pd.NA})
    before = len(df)
    df = df.dropna(how="all")
    return df, before - len(df)

def _parse_date_value(v) -> date:
    if v is None or (isinstance(v, float) and pd.isna(v)) or (isinstance(v, str) and not v.strip()):
        raise ValueError("missing date")

    s = str(v).strip()

    # If it's ISO-like (YYYY-MM-DD), parse strictly as ISO to avoid day/month flips
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return date.fromisoformat(s)

    # Otherwise, try EU first then fallback
    try:
        return pd.to_datetime(s, errors="raise", dayfirst=True).date()
    except Exception:
        return pd.to_datetime(s, errors="raise", dayfirst=False).date()
    

def _parse_amount_value(v) -> Decimal:

    if v is None: 
        raise ValueError("missing amount")
    
    s = str(v).strip()
    if not s:
        raise ValueError("missing amount")
    
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1].strip()
    
    s = s.replace("\u00a0", "").replace(" ", "")

    s = re.sub(r"[^0-9,\.\-\+']", "", s)


    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            # comma decimal: "1.234,56" -> "1234.56"
            s = s.replace(".", "").replace(",", ".")
        else:
            # dot decimal: "1,234.56" -> "1234.56"
            s = s.replace(",", "")
    elif "," in s:
        # assume comma is decimal: "-23,50" -> "-23.50"
        s = s.replace(".", "").replace(",", ".")
    else:
        # remove thousands commas if any
        s = s.replace(",", "")

    # remove apostrophe thousands separators: 1'234.56
    s = s.replace("'", "")

    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValueError(f"could not parse amount: {v}") from None



def _parse_amount_optional(v) -> Decimal:
    """Like _parse_amount_value, but blank/None becomes 0.00 (useful for debit/credit columns)."""
    if v is None or pd.isna(v):
        return Decimal(0.00)
    s = str(v).strip()
    if s == "" or s.lower() == "nan":
        return Decimal(0.00)
    return _parse_amount_value(s)




def _tx_hash(d: date, desc: str, amt: Decimal, account: str | None, currency: str | None) -> str:
    # <-- added helper (used by ingest)
    key = f"{d.isoformat()}|{desc}|{amt}|{account or ''}|{currency or ''}".encode("utf-8")
    return hashlib.sha256(key).hexdigest()


@app.get("/health", response_model = HealthResponse)
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/ingest", response_model = IngestResult)
async def ingest_csv(file: UploadFile = File(...), db: Session = Depends(get_db), _auth = Depends(require_api_key)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    content = await file.read()

    try:
        df = _read_csv_bytes(content)
        df, skipped_empty = _strip_and_drop_empty_rows(df)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read CSV: {e}")

    # --- Normalize columns ---
    df.columns = [c.strip().lower() for c in df.columns]

    # Accept a few common column names
    col_map = {}
    for c in df.columns:
        if c in {"date", "transaction date", "booking date", "buchungstag", "valuta"}:
            col_map[c] = "date"
        elif c in {"description", "merchant", "details", "text", "purpose", "verwendungszweck", "name"}:
            col_map[c] = "description"
        elif c in {"amount", "value", "betrag", "umsatz"}:
            col_map[c] = "amount"
        elif c in {"debit", "withdrawal", "outflow"}:
            col_map[c] = "debit"
        elif c in {"credit", "deposit", "inflow"}:
            col_map[c] = "credit"
        elif c in {"category"}:
            col_map[c] = "category"
        elif c in {"account"}:
            col_map[c] = "account"
        elif c in {"currency", "währung"}:
            col_map[c] = "currency"

    df = df.rename(columns=col_map)

    required = {"date", "description"}
    if not required.issubset(df.columns):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must contain columns {sorted(required)} (found: {list(df.columns)})",
        )

    # amount can come from "amount" OR from debit/credit
    if "amount" not in df.columns and not ({"debit", "credit"} & set(df.columns)):
        raise HTTPException(
            status_code=400,
            detail="CSV must contain 'amount' or at least one of 'debit'/'credit'",
        )

    # --- Parse types ---
    errors = []
    inserted = 0
    skipped_duplicates = 0

    for idx, row in df.iterrows():
        try:
            tx_date = _parse_date_value(row["date"])
            desc = str(row["description"]).strip()
            #amt = _parse_amount_value(row["amount"])

            amount_present = "amount" in df.columns and pd.notna(row.get("amount"))
            amount_nonempty = amount_present and str(row.get("amount")).strip() not in {"", "nan", "NaN", "None"}

            if amount_nonempty:
                amt = _parse_amount_value(row["amount"])
            else:
                # fall back to credit - debit if available
                if "credit" in df.columns or "debit" in df.columns:
                    amt = _parse_amount_optional(row.get("credit")) - _parse_amount_optional(row.get("debit"))
                else:
                    raise ValueError("no usable amount (amount is empty and no debit/credit columns)")

            cat = str(row["category"]).strip() if "category" in df.columns and pd.notna(row["category"]) else categorize(desc)
            account = str(row["account"]).strip() if "account" in df.columns and pd.notna(row["account"]) else None
            currency = str(row["currency"]).strip() if "currency" in df.columns and pd.notna(row["currency"]) else None

            h = _tx_hash(tx_date, desc, amt, account, currency)
            try:
                # Savepoint per row in case of duplicate rejection
                with db.begin_nested():
                    db.add(Transaction(
                        date=tx_date,
                        description=desc,
                        amount = amt,
                        transaction_hash=h,
                        category=cat or "Uncategorized",
                        account=account,
                        currency=currency,

                    ))
                    db.flush()
                inserted += 1
            except IntegrityError:
                skipped_duplicates +=1
        except Exception as e:
            errors.append({"row": int(idx), "error": str(e)})

    db.commit()

    return {
        "filename": file.filename,
        "rows_received": int(len(df)),
        "rows_inserted": int(inserted),
        "rows_skipped_empty": int(skipped_empty),
        "rows_skipped_duplicates": int(skipped_duplicates),
        "rows_failed": int(len(errors)),
        "sample_errors": errors[:5],
    }


@app.get("/transactions", response_model = TransactionPage) 
def list_transactions(
    db: Session = Depends(get_db),
    _auth=Depends(require_api_key),
    limit: int = 50,
    offset: int = 0,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    merchant_contains: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
):  
    # --- guardrails ---
    limit = max(1, min(limit, 200))   # 1..200
    offset = max(0, offset)           # >=0


    q = select(Transaction)

    if start_date:
        q = q.where(Transaction.date >= start_date)
    if end_date:
        q = q.where(Transaction.date <= end_date)
    if category:
        q = q.where(Transaction.category == category)
    if merchant_contains:
        q = q.where(Transaction.description.ilike(f"%{merchant_contains}%"))
    if min_amount is not None:
        q = q.where(Transaction.amount >= min_amount)
    if max_amount is not None:
        q = q.where(Transaction.amount <= max_amount)

    total = db.execute(select(func.count()).select_from(q.subquery())).scalar_one()

    rows = (
        db.execute(
            q.order_by(Transaction.date.desc(), Transaction.id.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )

    return TransactionPage(
        limit=limit,
        offset=offset,
        total=int(total),
        items=rows,
    )


@app.get("/summary/by-category", response_model = list[CategorySummary])
def summary_by_category(db: Session = Depends(get_db), _auth=Depends(require_api_key)):
    q = (
        select(Transaction.category, func.sum(Transaction.amount).label("total"))
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount), Transaction.category)
    )
    rows = db.execute(q).all()
    return [{"category": c, "total": float(t)} for c, t in rows]


@app.get("/summary/over-time", response_model = list[TimeBucket])
def summary_over_time(db: Session = Depends(get_db), _auth=Depends(require_api_key), granularity: str = "day"):
    if granularity not in {"day", "month"}:
        raise HTTPException(status_code=400, detail="granularity must be 'day' or 'month'")

    if granularity == "day":
        bucket = Transaction.date
    else:
        bucket = func.date_trunc("month", Transaction.date).cast(SA_Date)

    q = (
        select(bucket.label("bucket"), func.sum(Transaction.amount).label("total"))
        .group_by("bucket")
        .order_by("bucket")
    )
    rows = db.execute(q).all()
    return [{"bucket": b.isoformat(), "total": float(t)} for b, t in rows]




