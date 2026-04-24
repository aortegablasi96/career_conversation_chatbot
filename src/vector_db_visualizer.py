# streamlit_app.py
# Run with: streamlit run streamlit_app.py
#
# Requirements:
#   pip install streamlit chromadb pandas
#
# Optional for embedding visualization:
#   pip install umap-learn plotly numpy

import streamlit as st
import chromadb
from pathlib import Path
import pandas as pd
import json
import re

st.set_page_config(page_title="Chroma DB Explorer", layout="wide")

st.title("🔎 Chroma DB Explorer")
st.write("Browse all collections in a Chroma persistent database.")

# -----------------------------
# Helpers
# -----------------------------
def safe_json(obj):
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)

def highlight_text(text, query):
    if not query or not text:
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

def load_collection_data(client, collection_name: str, limit: int, include_embeddings: bool):
    include_fields = ["documents", "metadatas"]
    if include_embeddings:
        include_fields.append("embeddings")

    col = client.get_collection(collection_name)

    data = col.get(
        limit=int(limit),
        include=include_fields,
    )

    ids = data.get("ids", [])
    docs = data.get("documents", [])
    metas = data.get("metadatas", [])
    embeds = data.get("embeddings", None)

    df = pd.DataFrame(
        {
            "collection": [collection_name] * len(ids),
            "id": ids,
            "text": docs,
            "metadata": metas,
        }
    )
    return df, embeds

# -----------------------------
# Sidebar: Connection settings
# -----------------------------
st.sidebar.header("⚙️ Chroma Settings")

persist_path = st.sidebar.text_input(
    "Persistent Chroma Path",
    value=str(Path(__file__).parent.parent / "vector_db"),
    help="Folder path used by chromadb.PersistentClient(path=...)",
)

include_embeddings = st.sidebar.checkbox("Include embeddings (slower)", value=False)

load_limit = st.sidebar.number_input(
    "Load Limit per collection",
    min_value=10,
    max_value=50000,
    value=500,
    step=50,
)

# -----------------------------
# Load client + collections
# -----------------------------
try:
    client = load_client(persist_path)
    collection_names = list_collection_names(persist_path)
except Exception as e:
    st.sidebar.error("Could not connect to Chroma.")
    st.sidebar.write(str(e))
    st.stop()

if not collection_names:
    st.warning("No collections found in this Chroma database.")
    st.stop()

st.sidebar.success(f"Connected! Found {len(collection_names)} collections.")

# -----------------------------
# Sidebar: Collection selector
# -----------------------------
st.sidebar.header("📚 Collections")

mode = st.sidebar.radio(
    "Browse mode",
    ["Single collection", "All collections combined"],
)

if mode == "Single collection":
    selected_collections = [
        st.sidebar.selectbox("Choose collection", collection_names)
    ]
else:
    selected_collections = st.sidebar.multiselect(
        "Select collections to include",
        collection_names,
        default=collection_names,
    )

if not selected_collections:
    st.info("Select at least one collection.")
    st.stop()

# -----------------------------
# Load selected collection data
# -----------------------------
dfs = []
all_embeddings = {}

for cname in selected_collections:
    try:
        df_col, embeds = load_collection_data(client, cname, load_limit, include_embeddings)
        dfs.append(df_col)
        all_embeddings[cname] = embeds
    except Exception as e:
        st.warning(f"Failed to load collection: {cname}")
        st.write(str(e))

if not dfs:
    st.warning("No data loaded.")
    st.stop()

df = pd.concat(dfs, ignore_index=True)

st.caption(f"Loaded **{len(df)}** total records from {len(selected_collections)} collections.")

# -----------------------------
# Sidebar Filters
# -----------------------------
st.sidebar.header("🔍 Filters")

search_text = st.sidebar.text_input("Search in chunk text", value="")

metadata_key = st.sidebar.text_input(
    "Metadata key filter (optional)",
    value="",
    help="Example: source, file, page, chunk_id, etc.",
)

metadata_value = st.sidebar.text_input(
    "Metadata value contains (optional)",
    value="",
)

collection_filter = st.sidebar.multiselect(
    "Filter by collection",
    options=sorted(df["collection"].unique()),
    default=sorted(df["collection"].unique()),
)

# Apply filters
filtered_df = df.copy()

if collection_filter:
    filtered_df = filtered_df[filtered_df["collection"].isin(collection_filter)]

if search_text.strip():
    mask = filtered_df["text"].fillna("").str.contains(search_text, case=False, na=False)
    filtered_df = filtered_df[mask]

if metadata_key.strip() and metadata_value.strip():
    def meta_contains(meta):
        if not isinstance(meta, dict):
            return False
        val = meta.get(metadata_key, "")
        return metadata_value.lower() in str(val).lower()

    filtered_df = filtered_df[filtered_df["metadata"].apply(meta_contains)]

filtered_df = filtered_df.reset_index(drop=True)

st.sidebar.write(f"📌 Matching records: **{len(filtered_df)}**")

if len(filtered_df) == 0:
    st.warning("No matching chunks.")
    st.stop()

# -----------------------------
# Main layout
# -----------------------------
left, right = st.columns([0.45, 0.55], gap="large")

with left:
    st.subheader("📄 Chunk List")

    filtered_df["preview"] = filtered_df["text"].fillna("").apply(
        lambda x: x[:200].replace("\n", " ")
    )

    # Create a nice label for selectbox
    filtered_df["label"] = filtered_df.apply(
        lambda r: f"[{r['collection']}] {r['id']} :: {r['preview']}",
        axis=1
    )

    selected_label = st.selectbox(
        "Select a chunk",
        filtered_df["label"].tolist(),
        index=0,
    )

    selected_row = filtered_df[filtered_df["label"] == selected_label].iloc[0]

    st.markdown("### 📋 Table View")
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
    chunk_text = selected_row["text"] or ""
    st.markdown(highlight_text(chunk_text, search_text))

    st.markdown("### 🧠 Similarity Search (Query Collection)")
    st.caption("Similarity search works inside one collection at a time.")

    query = st.text_input("Query text", value="")
    n_results = st.slider("Top N results", 1, 20, 5)

    if st.button("Run similarity query"):
        try:
            col = client.get_collection(selected_row["collection"])
            results = col.query(
                query_texts=[query],
                n_results=int(n_results),
                include=["documents", "metadatas", "distances"],
            )

            res_docs = results["documents"][0]
            res_metas = results["metadatas"][0]
            res_dists = results["distances"][0]
            res_ids = results["ids"][0]

            out_df = pd.DataFrame(
                {
                    "id": res_ids,
                    "distance": res_dists,
                    "text_preview": [d[:200].replace("\n", " ") for d in res_docs],
                    "metadata": [safe_json(m)[:200] for m in res_metas],
                }
            )

            st.markdown("### 📌 Query Results")
            st.dataframe(out_df, use_container_width=True)

        except Exception as e:
            st.error("Query failed.")
            st.write(str(e))

# -----------------------------
# Optional: Embedding visualization (UMAP)
# -----------------------------
st.divider()
st.subheader("🗺️ Embedding Map (Optional)")

st.write(
    "Embedding visualization is only meaningful within a single collection "
    "because different collections may use different embedding models."
)

if not include_embeddings:
    st.info("Enable **Include embeddings** in the sidebar to use embedding visualization.")
else:
    if len(collection_filter) != 1:
        st.info("Select exactly **one** collection in the sidebar filter to view its embedding map.")
    else:
        colname = collection_filter[0]
        embeds = all_embeddings.get(colname)

        if embeds is None:
            st.warning("No embeddings loaded for this collection.")
        else:
            try:
                import numpy as np
                import umap
                import plotly.express as px

                st.write(f"Computing 2D projection for collection `{colname}`...")

                X = np.array(embeds)

                reducer = umap.UMAP(
                    n_neighbors=15,
                    min_dist=0.1,
                    metric="cosine",
                    random_state=42
                )
                coords = reducer.fit_transform(X)

                viz_df = df[df["collection"] == colname].copy().reset_index(drop=True)
                viz_df["x"] = coords[: len(viz_df), 0]
                viz_df["y"] = coords[: len(viz_df), 1]
                viz_df["preview"] = viz_df["text"].fillna("").apply(lambda x: x[:120].replace("\n", " "))

                fig = px.scatter(
                    viz_df,
                    x="x",
                    y="y",
                    hover_data=["id", "preview"],
                    title=f"UMAP projection of embeddings: {colname}",
                )

                st.plotly_chart(fig, use_container_width=True)

            except ImportError:
                st.warning("Install extra packages for embedding visualization:")
                st.code("pip install umap-learn plotly numpy")
            except Exception as e:
                st.error("Failed to build embedding visualization.")
                st.write(str(e))