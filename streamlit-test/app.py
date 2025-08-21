
import streamlit as st
import pandas as pd
import json
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import io
import os
import sys

# Make core modules available
sys.path.append("pyqt-pdf-analyzer")
from core.annotation_renderers import render_keyword_annotation
from core.annotation_system import Annotation, AnnotationType

st.set_page_config(layout="wide")
st.title("📄 UFC PDF Visualizer with Keyword Pills")

# Add diagnostic print
st.write("Files in directory:", os.listdir("streamlit-test/"))

# Then attempt to read
keyword_df = pd.read_csv("streamlit-test/keywords.csv")

keyword_map = {
    row["keyword"].lower(): {"category": row["category"], "color": row["color"]}
    for _, row in keyword_df.iterrows()
}
category_colors = {r.category: r.color for r in keyword_df.itertuples()}

# Load metadata & PDF
df = pd.read_csv("data/deontic_metadata.csv")
pdf_path = "data/ufc_example.pdf"
if not os.path.exists(pdf_path):
    st.error("Place 'ufc_example.pdf' inside data/")
    st.stop()

visible_pages = sorted(df["page"].unique())
max_per_row = st.sidebar.slider("Pages per row", 2, 6, 3)
keyword_search = st.sidebar.text_input("🔍 Filter Keywords")

for i in range(0, len(visible_pages), max_per_row):
    cols = st.columns(len(visible_pages[i:i + max_per_row]))
    for j, page_num in enumerate(visible_pages[i:i + max_per_row]):
        page_df = df[df["page"] == page_num]
        page = fitz.open(pdf_path).load_page(page_num)
        pix = page.get_pixmap(dpi=150)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        draw = ImageDraw.Draw(img)

        for _, row in page_df.iterrows():
            content = row["content"].lower()
            if keyword_search and keyword_search.lower() not in content:
                continue
            bbox = json.loads(row["bounding_box"])
            bounds = {"x0": bbox["x0"], "y0": bbox["y0"], "x1": bbox["x1"], "y1": bbox["y1"]}
            for kw, meta in keyword_map.items():
                if kw in content:
                    annotation = Annotation(
                        text=kw,
                        annotation_type=AnnotationType.KEYWORD,
                        category=meta["category"],
                        color=meta["color"],
                        metadata={}
                    )
                    render_keyword_annotation(annotation, draw, bounds)

        cols[j].image(img, caption=f"Page {page_num + 1}", use_column_width=True)

# Legend
st.sidebar.markdown("### 🔖 Keyword Legend")
for cat, color in category_colors.items():
    st.sidebar.markdown(
        f"<div style='background:{color};padding:4px 10px;border-radius:20px;color:white;display:inline-block;margin:2px'>{cat}</div>",
        unsafe_allow_html=True
    )
