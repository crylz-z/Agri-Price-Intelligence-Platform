"""The dashboard's five pages (ADR 25), in reading order.

Each page is a file in `app_pages/` that calls its function in `views.py`, so
`AppTest.switch_page` can reach it. Paths are absolute, because
`tmp/local_app.py` runs `app.py` from another folder.
"""

from pathlib import Path

import streamlit as st

PAGES_DIR = Path(__file__).parent / "app_pages"

# name: (title, icon, url path; "" is the default page)
PAGES = {
    "story": ("The story", "menu_book", ""),
    "caught": ("Who got caught", "gavel", "caught"),
    "food": ("Check your food", "search", "food"),
    "short": ("The short version", "bolt", "short"),
    "how": ("How it's built", "construction", "how"),
}


def page(name: str) -> st.Page:
    """The page called `name`, for `st.navigation` and `st.page_link`."""
    title, icon, url_path = PAGES[name]
    return st.Page(
        PAGES_DIR / f"{name}.py",
        title=title,
        icon=f":material/{icon}:",
        url_path=url_path or None,
        default=not url_path,
    )


def pages() -> list[st.Page]:
    return [page(name) for name in PAGES]


def after(name: str) -> str:
    """The page that follows `name`; the last leads back to the story."""
    names = list(PAGES)
    return names[(names.index(name) + 1) % len(names)]
