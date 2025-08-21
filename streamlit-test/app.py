import io
import json

import fitz  # PyMuPDF
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(layout="wide")
st.title("📄 UFC PDF Visualizer with Keyword Pills")


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------
if "phase" not in st.session_state:
    # 0 = nothing loaded
    # 1 = PDF loaded, awaiting further commands
    # 2 = all processing complete
    st.session_state.phase = 0
    st.session_state.doc = None
    st.session_state.df = None
    st.session_state.keyword_map = None
    st.session_state.category_colors = None


def handle_open_pdf(uploaded):
    """Phase 1: only load the PDF and metadata."""
    if uploaded is None:
        st.warning("Please select a PDF file before opening.")
        return

    # Phase 1 logic – open the PDF and read initial metadata.
    doc = fitz.open(stream=uploaded.read(), filetype="pdf")
    st.session_state.doc = doc

    # Load supporting data needed for later phases
    st.session_state.df = pd.read_csv("data/deontic_metadata.csv")
    keyword_df = pd.read_csv("streamlit-test/keywords.csv")
    st.session_state.keyword_map = {
        row["keyword"].lower(): {
            "category": row["category"],
            "color": row["color"],
        }
        for _, row in keyword_df.iterrows()
    }
    st.session_state.category_colors = {
        r.category: r.color for r in keyword_df.itertuples()
    }

    st.session_state.phase = 1
    st.success("PDF loaded. Click 'Run All Steps' to continue.")


def run_all_steps():
    """Phase 2: render pages and keyword highlights."""
    if st.session_state.phase != 1:
        # Guard against accidental execution
        st.warning("Phase 1 has not completed. Please open a PDF first.")
        return

    doc = st.session_state.doc
    df = st.session_state.df
    keyword_map = st.session_state.keyword_map
    category_colors = st.session_state.category_colors

    visible_pages = sorted(df["page"].unique())
    max_per_row = st.sidebar.slider("Pages per row", 2, 6, 3)
    keyword_search = st.sidebar.text_input("🔍 Filter Keywords")

    font = ImageFont.load_default()

    for i in range(0, len(visible_pages), max_per_row):
        cols = st.columns(len(visible_pages[i : i + max_per_row]))
        for j, page_num in enumerate(visible_pages[i : i + max_per_row]):
            page_df = df[df["page"] == page_num]
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=150)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            draw = ImageDraw.Draw(img)

            for _, row in page_df.iterrows():
                content = row["content"].lower()
                if keyword_search and keyword_search.lower() not in content:
                    continue
                bbox = json.loads(row["bounding_box"])
                x0, y0, x1, y1 = (
                    bbox["x0"],
                    bbox["y0"],
                    bbox["x1"],
                    bbox["y1"],
                )
                for kw, meta in keyword_map.items():
                    if kw in content:
                        color = meta["color"]
                        label = meta["category"]
                        text = f" {label} "
                        w, h = draw.textsize(text, font=font)
                        rx0, ry0 = x0, y0 - h - 6
                        rx1, ry1 = rx0 + w + 4, ry0 + h + 4
                        draw.rounded_rectangle(
                            [rx0, ry0, rx1, ry1], radius=8, fill=color
                        )
                        draw.text((rx0 + 2, ry0 + 2), text, fill="white", font=font)
                        draw.rectangle([x0, y0, x1, y1], outline=color, width=2)

            cols[j].image(
                img, caption=f"Page {page_num + 1}", use_column_width=True
            )

    # Keyword legend
    st.sidebar.markdown("### 🔖 Keyword Legend")
    for cat, color in category_colors.items():
        st.sidebar.markdown(
            f"<div style='background:{color};padding:4px 10px;border-radius:20px;"
            f"color:white;display:inline-block;margin:2px'>{cat}</div>",
            unsafe_allow_html=True,
        )

    st.session_state.phase = 2


# ---------------------------------------------------------------------------
# UI controls
# ---------------------------------------------------------------------------
phase = st.session_state.phase
st.sidebar.header("Steps")
st.sidebar.markdown(f"1. Open PDF {'✅' if phase >= 1 else ''}")
st.sidebar.markdown(f"2. Run All Steps {'✅' if phase >= 2 else ''}")

uploaded_pdf = st.file_uploader("Select a PDF", type="pdf")

if st.button("1. Open PDF"):
    handle_open_pdf(uploaded_pdf)

if st.button("Run All Steps"):
    run_all_steps()

