from __future__ import annotations


def _ingest(client, csv_text: str):
    """Helper: ingest a CSV and assert success."""
    r = client.post(
        "/ingest",
        files={"file": ("test.csv", csv_text.encode(), "text/csv")},
    )
    assert r.status_code == 200, r.text
    return r.json()


SAMPLE_CSV = (
    "date,description,amount\n"
    "2026-01-01,Aldi Grocery,-23.50\n"
    "2026-01-15,Netflix,-12.99\n"
    "2026-02-01,Uber Ride,-8.40\n"
)

def test_transactions_filter_by_category(client):
    _ingest(client, SAMPLE_CSV)
    r = client.get("/transactions?category=Groceries")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["description"] == "Aldi Grocery"


def test_transactions_filter_by_date_range(client):
    _ingest(client, SAMPLE_CSV)
    r = client.get("/transactions?start_date=2026-01-10&end_date=2026-01-31")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["description"] == "Netflix"


def test_transactions_filter_by_merchant(client):
    _ingest(client, SAMPLE_CSV)
    r = client.get("/transactions?merchant_contains=uber")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["description"] == "Uber Ride"


def test_summary_by_category(client):
    _ingest(client, SAMPLE_CSV)
    r = client.get("/summary/by-category")
    assert r.status_code == 200
    data = {row["category"]: row["total"] for row in r.json()}
    assert data["Groceries"] == -23.50
    assert data["Subscriptions"] == -12.99
    assert data["Transport"] == -8.40


def test_summary_over_time_by_day(client):
    _ingest(client, SAMPLE_CSV)
    r = client.get("/summary/over-time?granularity=day")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3


def test_ingest_rejects_non_csv(client):
    r = client.post(
        "/ingest",
        files={"file": ("data.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 400
    assert "csv" in r.json()["detail"].lower()


def test_ingest_missing_columns(client):
    csv_text = "date,foo\n2026-01-01,bar\n"
    r = client.post(
        "/ingest",
        files={"file": ("test.csv", csv_text.encode(), "text/csv")},
    )
    assert r.status_code == 400
    assert "description" in r.json()["detail"].lower()
