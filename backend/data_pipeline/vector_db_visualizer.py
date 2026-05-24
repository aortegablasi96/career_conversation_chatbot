from pathlib import Path
import streamlit as st
import chromadb
import pandas as pd
import json
import re

import traceback

DB_NAME = str(Path(__file__).parent.parent / "vector_db")

st.set_page_config(page_title="Chroma DB Explorer", layout="wide")

st.title("🔎 Chroma DB Explorer")

# -----------------------------
# Helpers
# -----------------------------
def safe_json(obj):
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)

def safe_str(x):
    if x is None:
        return ""
    return str(x)

def highlight_text(text, query):
    if not query:
        return text
    try:
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        return pattern.sub(lambda m: f"**:orange[{m.group(0)}]**", text)
    except Exception:
        return text

@st.cache_resource
def load_client(persist_path: str):
    return chromadb.PersistentClient(path=persist_path)

@st.cache_data
def list_collection_names(persist_path: str):
    client = chromadb.PersistentClient(path=persist_path)
    cols = client.list_collections()
    return sorted([c.name for c in cols])

def load_collection_data(client, collection_name: str, limit: int):
    col = client.get_collection(collection_name)

    data = col.get(limit=int(limit), include=["documents", "metadatas"])

    ids = data.get("ids") or []
    docs = data.get("documents") or []
    metas = data.get("metadatas") or []

    # Chroma sometimes returns None docs -> normalize length
    if docs is None:
        docs = [""] * len(ids)
    if metas is None:
        metas = [{}] * len(ids)

    # Ensure same length
    n = min(len(ids), len(docs), len(metas))
    ids, docs, metas = ids[:n], docs[:n], metas[:n]

    return pd.DataFrame({
        "collection": [collection_name] * n,
        "id": ids,
        "text": [safe_str(x) for x in docs],
        "metadata": metas
    })

# -----------------------------
# Sidebar Settings
# -----------------------------
st.sidebar.header("⚙️ Settings")

persist_path = st.sidebar.text_input(
    "Chroma persist path",
    value=DB_NAME,
)

load_limit = st.sidebar.number_input(
    "Load limit per collection",
    min_value=10,
    max_value=50000,
    value=500,
    step=50,
)

# -----------------------------
# Connect to Chroma
# -----------------------------
try:
    client = load_client(persist_path)
    collection_names = list_collection_names(persist_path)
except Exception as e:
    st.error("❌ Failed to connect to Chroma")
    st.code(str(e))
    st.stop()

if not collection_names:
    st.warning("No collections found.")
    st.stop()

st.sidebar.success(f"Found {len(collection_names)} collections")

# -----------------------------
# Collection selection
# -----------------------------
mode = st.sidebar.radio("Browse mode", ["Single collection", "Multiple collections"])

if mode == "Single collection":
    selected_collections = [st.sidebar.selectbox("Collection", collection_names)]
else:
    selected_collections = st.sidebar.multiselect(
        "Collections",
        collection_names,
        default=collection_names
    )

if not selected_collections:
    st.warning("Select at least one collection.")
    st.stop()

# -----------------------------
# Load data
# -----------------------------
dfs = []
for cname in selected_collections:
    try:
        dfs.append(load_collection_data(client, cname, load_limit))
    except Exception as e:
        st.warning(f"Failed to load collection `{cname}`")
        st.code(str(e))

if not dfs:
    st.error("No data loaded from any collection.")
    st.stop()

df = pd.concat(dfs, ignore_index=True)

st.caption(f"Loaded **{len(df)}** chunks total.")

# -----------------------------
# Filters
# -----------------------------
st.sidebar.header("🔍 Filters")

search_text = st.sidebar.text_input("Search text", "")

metadata_key = st.sidebar.text_input("Metadata key (optional)", "")
metadata_value = st.sidebar.text_input("Metadata contains (optional)", "")

collection_filter = st.sidebar.multiselect(
    "Filter collections",
    sorted(df["collection"].unique()),
    default=sorted(df["collection"].unique())
)

filtered_df = df.copy()

if collection_filter:
    filtered_df = filtered_df[filtered_df["collection"].isin(collection_filter)]

if search_text.strip():
    filtered_df = filtered_df[
        filtered_df["text"].str.contains(search_text, case=False, na=False)
    ]

if metadata_key.strip() and metadata_value.strip():
    def meta_match(meta):
        if not isinstance(meta, dict):
            return False
        return metadata_value.lower() in safe_str(meta.get(metadata_key, "")).lower()

    filtered_df = filtered_df[filtered_df["metadata"].apply(meta_match)]

filtered_df = filtered_df.reset_index(drop=True)

st.sidebar.write(f"Matches: **{len(filtered_df)}**")

if len(filtered_df) == 0:
    st.warning("No matching chunks.")
    st.stop()

# -----------------------------
# Layout
# -----------------------------
left, right = st.columns([0.45, 0.55], gap="large")

with left:
    st.subheader("📄 Chunk List")

    # preview column
    filtered_df["preview"] = filtered_df["text"].apply(
        lambda x: safe_str(x)[:200].replace("\n", " ")
    )

    labels = filtered_df.apply(
        lambda r: f"[{r['collection']}] {r['id']} :: {r['preview']}",
        axis=1
    ).tolist()

    selected_label = st.selectbox("Select chunk", labels, index=0)

    selected_index = labels.index(selected_label)
    selected_row = filtered_df.iloc[selected_index]

    st.dataframe(
        filtered_df[["collection", "id", "preview"]],
        use_container_width=True,
        height=500,
    )

with right:
    st.subheader("🔎 Chunk Inspector")

    st.markdown(f"**Collection:** `{selected_row['collection']}`")
    st.markdown(f"**ID:** `{selected_row['id']}`")

    st.markdown("### 📌 Metadata")
    st.code(safe_json(selected_row["metadata"]), language="json")

    st.markdown("### 🧾 Chunk Text")
    st.markdown(highlight_text(selected_row["text"], search_text))

    st.markdown("### 🧠 Similarity Search (within same collection)")
    query = st.text_input("Query text", "")

    n_results = st.slider("Top N", 1, 20, 5)

    if st.button("Run similarity query"):
        try:
            col = client.get_collection(selected_row["collection"])
            results = col.query(
                query_texts=[query],
                n_results=int(n_results),
                include=["documents", "metadatas", "distances"]
            )

            out_df = pd.DataFrame({
                "id": results["ids"][0],
                "distance": results["distances"][0],
                "preview": [safe_str(x)[:200].replace("\n", " ") for x in results["documents"][0]],
                "metadata": [safe_json(m)[:200] for m in results["metadatas"][0]],
            })

            st.dataframe(out_df, use_container_width=True)

        except Exception as e:
            st.error("Query failed")
            st.code(str(e))
            traceback.print_exc()