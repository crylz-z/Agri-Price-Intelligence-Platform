"""Page 4, how it's built: the pipeline at a glance (spec: Page 4).

The picture is Graphviz, since Streamlit draws no Mermaid. Its boxes are filled
light with dark text, so they read the same on the light and the dark theme.
The release date and food count are read live from the marts; everything else
about the pipeline stays in the README.
"""

import streamlit as st

from src.dashboard import data, views

REPO = "https://github.com/crylz-z/Agri-Price-Intelligence-Platform"
# The browser draws the labels in its own font, wider than the one Graphviz
# measured, and SVG drops plain leading spaces: non-breaking ones keep each
# edge label clear of its arrow.
GAP = chr(0xA0) * 3

PIPELINE = f"""digraph {{
  rankdir=TB; bgcolor="transparent"; nodesep=0.4; ranksep=0.45; pad=0.3;
  node [shape=box, style="rounded,filled", fillcolor="#F4F1EC", fontcolor="#2B2620",
        color="{views.MUTED}", fontname="sans-serif", fontsize=12, margin="0.2,0.08"];
  edge [color="{views.MUTED}", fontcolor="{views.MUTED}", fontname="sans-serif",
        fontsize=10, arrowsize=0.7];
  cron [label="GitHub Actions\\nevery day, 10:00", style="rounded,dashed,filled"];
  psa [label="PSA OpenSTAT\\nfarm, wholesale and store prices"];
  raw [label="Cloudflare R2: raw\\neach release, kept unchanged"];
  dbt [label="dbt build\\nmodels and tests"];
  marts [label="Cloudflare R2: marts\\nsix Parquet tables"];
  page [label="This page\\nStreamlit"];
  cron -> psa [style=dashed, label="{GAP}checks"];
  psa -> raw [label="{GAP}new releases only"];
  raw -> dbt;
  dbt -> marts [label="{GAP}only if every\\l{GAP}test passes\\l"];
  marts -> page;
}}"""

# Each fact as a card: title, Material icon, one line.
FACTS = (
    (
        "Costs $0 a month",
        "savings",
        "Runs inside Cloudflare R2's and GitHub's free tiers.",
    ),
    (
        "Raw data kept as is",
        "inventory_2",
        "Each PSA release is stored unchanged, so every number traces back to it.",
    ),
    (
        "Tests block publishing",
        "verified",
        "If a test fails, nothing is written and the page keeps the last good data.",
    ),
    ("Checked daily", "schedule", "A job asks PSA for new releases every morning."),
)

USUAL = (
    "Each month's store price is set against the average of its own year, so "
    "inflation drops out. The usual range for a month spans every full year since "
    "2018, leaving out the highest and lowest year, and a food needs at least 5 "
    "full years to get one. The range is then scaled to the food's average store "
    "price over the 12 months before its latest, so the month being judged doesn't "
    "set its own range."
)


def page() -> None:
    shares = data.load(data.SHARES)
    growth = data.outran(data.load(data.GROWTH))
    views.masthead(shares, growth)
    st.header("How it's built", anchor=False)
    st.markdown("From PSA's tables to this page, rebuilt each time PSA releases.")
    # Its own width: stretched, the tall chart filled a desktop screen.
    st.graphviz_chart(PIPELINE, width="content")
    for row in range(0, len(FACTS), 2):
        for column, (title, icon, text) in zip(
            st.columns(2), FACTS[row : row + 2], strict=False
        ):
            with column.container(border=True, height="stretch"):
                st.markdown(f"**:material/{icon}: {title}**")
                st.markdown(text)
    st.subheader("Usual for the time of year", anchor=False)
    st.markdown(USUAL)
    released = views.latest_release(shares)
    with st.container(horizontal=True):
        st.metric("Latest PSA release", f"{released:%d %b %Y}", border=True)
        st.metric("Foods", str(len(growth)), border=True)
    st.link_button("See the code on GitHub", REPO, icon=":material/code:")
    views.footer("how", shares)
