from __future__ import annotations


def _post_csv(client, filename: str, csv_text: str):
    return client.post(
        "/ingest",
        files={"file": (filename, csv_text.encode("utf-8"), "text/csv")},
    )


def test_ingest_semicolon_eu_amounts(client):
    csv_text = "date;description;amount\n2026-02-01;Coffee;-2,50\n2026-02-02;Salary;1.234,56\n"

    r = _post_csv(client, "test_semicolon_eu.csv", csv_text)
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["rows_received"] == 2
    assert data["rows_inserted"] == 2
    assert data["rows_failed"] == 0

    tx = client.get("/transactions?limit=200").json()
    assert tx["total"] == 2

    amounts = [item["amount"] for item in tx["items"]]
    assert 1234.56 in amounts
    assert -2.5 in amounts


def test_ingest_debit_credit_derives_amount(client):
    csv_text = (
        "booking date,merchant,debit,credit,currency\n"
        "2026-02-04,ATM Withdrawal,100,,\n"
        "2026-02-05,Refund,,25.50,EUR\n"
    )

    r = _post_csv(client, "test_debit_credit.csv", csv_text)
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["rows_received"] == 2
    assert data["rows_inserted"] == 2
    assert data["rows_failed"] == 0

    tx = client.get("/transactions?limit=200").json()
    assert tx["total"] == 2

    by_desc = {item["description"]: item for item in tx["items"]}
    assert by_desc["ATM Withdrawal"]["amount"] == -100.0
    assert by_desc["Refund"]["amount"] == 25.5
    assert by_desc["Refund"]["currency"] == "EUR"


def test_ingest_blank_line_and_idempotent_duplicates(client):
    csv_text = "date,description,amount\n\n2026-02-03,Groceries,-45.10\n"

    r1 = _post_csv(client, "test_comma_blank.csv", csv_text)
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert d1["rows_received"] == 1
    assert d1["rows_inserted"] == 1
    assert d1["rows_failed"] == 0

    r2 = _post_csv(client, "test_comma_blank.csv", csv_text)
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert d2["rows_received"] == 1
    assert d2["rows_inserted"] == 0
    assert d2["rows_skipped_duplicates"] == 1
    assert d2["rows_failed"] == 0
