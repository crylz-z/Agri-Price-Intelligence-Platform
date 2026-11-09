"""A light/dark button in the page's top corner.

Streamlit lets the viewer switch themes only from its ⋮ menu, and Python can't
change the theme (st.set_option rejects theme keys). So a native button mounts a
tiny component that saves the other theme where Streamlit keeps the viewer's
choice, in localStorage under `stActiveTheme-<path>-v2` (Streamlit 1.66), and
reloads. `?food=` lives in the URL, so the reload keeps the picked food. If a
Streamlit upgrade renames the key, the button just reloads in the same theme; the
⋮ menu still works.
"""

import streamlit as st

_SWITCH = st.components.v2.component(
    "theme_switch",
    js="""
export default function (component) {
  // The page background as "rgb(r, g, b)" tells the theme on screen now.
  const app = document.querySelector(".stApp") ?? document.body
  const [r, g, b] = getComputedStyle(app).backgroundColor.match(/\\d+/g).map(Number)
  const dark = 0.299 * r + 0.587 * g + 0.114 * b < 128
  const key = `stActiveTheme-${window.location.pathname}-v2`
  window.localStorage.setItem(key, JSON.stringify(dark ? "Light" : "Dark"))
  window.location.reload()
}
""",
)


def theme_button() -> None:
    dark = st.context.theme.type == "dark"
    if st.button(
        "Light" if dark else "Dark",
        icon=":material/light_mode:" if dark else ":material/dark_mode:",
        type="tertiary",
        key="theme",
        help="Switch between a light and a dark page",
    ):
        _SWITCH(key="theme_switch", height=0)
