import os
import requests
import pandas as pd
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")

st.set_page_config(page_title="Finance ETL Dashboard", layout="wide")
st.title("Finance ETL Dashboard")
st.caption("Upload a CSV → ingest into Postgres → explore spend summaries.")


def api_get(path: str, params: dict | None = None):
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    r = requests.get(f"{API_BASE_URL}{path}", params=params, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()


def api_post_file(path: str, uploaded_file):
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
    r = requests.post(f"{API_BASE_URL}{path}", files=files, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()


st.sidebar.header("Connection")
st.sidebar.write(f"API: `{API_BASE_URL}`")

try:
    health = api_get("/health")
    st.sidebar.success(f"API connected ✅ {health}")
except Exception as e:
    st.sidebar.error("API not reachable ❌")
    st.sidebar.code(str(e))
    st.stop()

st.sidebar.divider()
st.sidebar.header("Ingest")

uploaded = st.sidebar.file_uploader("Upload transactions CSV", type=["csv"])
if uploaded is not None:
    if st.sidebar.button("Ingest CSV", type="primary"):
        with st.spinner("Uploading and ingesting..."):
            try:
                result = api_post_file("/ingest", uploaded)
                st.sidebar.success("Ingest complete ✅")
                st.sidebar.json(result)
            except Exception as e:
                st.sidebar.error("Ingest failed ❌")
                st.sidebar.code(str(e))

st.sidebar.divider()
st.sidebar.header("Demo")

if st.sidebar.button("Load demo dataset"):
    try:
        with open("/data/sample_transactions.csv", "rb") as f:
            content = f.read()
        files = {"file": ("sample_transactions.csv", content, "text/csv")}
        headers = {"X-API-Key": API_KEY} if API_KEY else {}
        r = requests.post(f"{API_BASE_URL}/ingest", files=files, headers=headers, timeout=60)
        r.raise_for_status()
        st.sidebar.success("Demo data ingested ✅")
        st.sidebar.json(r.json())
        st.rerun()
    except Exception as e:
        st.sidebar.error("Failed to load demo data ❌")
        st.sidebar.code(str(e))

col1, col2 = st.columns(2)

with col1:
    st.subheader("Spend by category")
    try:
        by_cat = api_get("/summary/by-category")
        df_cat = pd.DataFrame(by_cat)

        if df_cat.empty:
            st.info("No data yet. Upload a CSV in the sidebar.")
        else:
            df_cat["total_abs"] = df_cat["total"].abs()
            st.bar_chart(df_cat.set_index("category")["total_abs"])
            st.dataframe(df_cat, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error("Failed to load category summary")
        st.code(str(e))

with col2:
    st.subheader("Spend over time")
    gran = st.selectbox("Granularity", ["day", "month"], index=1)
    try:
        over_time = api_get("/summary/over-time", params={"granularity": gran})
        df_time = pd.DataFrame(over_time)

        if df_time.empty:
            st.info("No data yet. Upload a CSV in the sidebar.")
        else:
            df_time["bucket"] = pd.to_datetime(df_time["bucket"])
            df_time["total_abs"] = df_time["total"].abs()
            st.line_chart(df_time.set_index("bucket")["total_abs"])
            st.dataframe(df_time, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error("Failed to load time summary")
        st.code(str(e))

st.divider()
st.subheader("Recent transactions")

try:
    by_cat = api_get("/summary/by-category")
    categories = sorted([x["category"] for x in by_cat]) if by_cat else []
except Exception:
    categories = []

with st.sidebar.expander("Filters", expanded=False):
    selected_category = st.selectbox("Category", ["(all)"] + categories, index=0)
    merchant_q = st.text_input("Merchant contains", value="")
    date_range = st.date_input("Date range", value=(), help="Optional")

params = {"limit": 200, "offset": 0}

if selected_category != "(all)":
    params["category"] = selected_category

if merchant_q.strip():
    params["merchant_contains"] = merchant_q.strip()

if isinstance(date_range, tuple) and len(date_range) == 2:
    params["start_date"] = date_range[0].isoformat()
    params["end_date"] = date_range[1].isoformat()

try:
    tx = api_get("/transactions", params=params)
    df_tx = pd.DataFrame(tx["items"])

    if df_tx.empty:
        st.info("No transactions match your filters.")
    else:
        df_tx["date"] = pd.to_datetime(df_tx["date"]).dt.date
        st.dataframe(df_tx, use_container_width=True, hide_index=True)
except Exception as e:
    st.error("Failed to load transactions")
    st.code(str(e))
