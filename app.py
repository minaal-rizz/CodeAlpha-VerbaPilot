#app.py
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import random
from translator_service import (
    translate,
    multi_translate,
    supported_languages,
    explain_idioms_slang,
    challenge_pool
)

from translator_service import _load_phrase_db
_load_phrase_db.cache_clear()


# ---------- THEME ----------
st.set_page_config(page_title="VerbaPilot Translator", page_icon="🌐", layout="wide")
st.markdown("""
<style>
.main { background: linear-gradient(135deg,#fdfbff 0%,#eef2ff 40%,#e0f2fe 100%) !important; }
.stTextArea textarea, .stSelectbox div[data-baseweb="select"] { border-radius: 12px !important; }
button[kind="primary"] { border-radius:12px !important; font-weight:600 !important;
 box-shadow:0 2px 6px rgba(0,0,0,.15) !important; }
</style>
""", unsafe_allow_html=True)

# ---------- SIDEBAR ----------
with st.sidebar:
    st.image("https://em-content.zobj.net/source/microsoft-teams/363/globe-with-meridians_1f310.png", width=80)
    st.title("VerbaPilot")
    st.caption("Interactive AI translator")

    features_on = {
        "multi":     st.checkbox("Multi-target translate", True),
        "idiom":     st.checkbox("Slang & Idiom explanation", True),
        "challenge": st.checkbox("Daily challenge game", True),
    }
    st.divider()
    

# ---------- DATA ----------
langs = supported_languages()
codes = [l["code"] for l in langs]
names = [l["name"] for l in langs]
code_to_name = {l["code"]: l["name"] for l in langs}
st.session_state.setdefault("xp", 0)

# ---------- HEADER ----------
st.markdown("<h1 style='text-align:center;'>🌐 VerbaPilot Translator</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>Translate, explore idioms & play language games!</p>", unsafe_allow_html=True)
st.write("")

# ---------- TABS ----------
tabs = ["Translate"]
if features_on["multi"]:
    tabs.append("Multi-Target")
if features_on["idiom"]:
    tabs.append("Idioms & Slang")
if features_on["challenge"]:
    tabs.append("Daily Challenge")
tabs.append("About")
tab_objs = st.tabs(tabs)

def pick_lang_box(label, default="English", key=None):
    if label.startswith("Source"):
        options = ["auto"] + names
        idx = 0
    else:
        options = names
        idx = names.index(default) if default in names else 0
    disp = st.selectbox(label, options, index=idx, key=key)
    if disp == "auto":
        return "auto", "auto"
    code = codes[names.index(disp)]
    return code, disp

# --- Translate tab ---
with tab_objs[0]:
    col1, col2, col3 = st.columns([4,4,1])
    with col1:
        src_code, src_disp = pick_lang_box("Source language", key="src_lang")
    with col2:
        tgt_code, tgt_disp = pick_lang_box("Target language", default="Spanish", key="tgt_lang")
    with col3:
        if st.button("⇄", help="Swap languages"):
            if src_code != "auto":
                st.session_state.src_lang, st.session_state.tgt_lang = tgt_disp, src_disp
                st.rerun()

    text = st.text_area("Enter text to translate:", height=200, placeholder="Type or paste here...", key="main_text")

    if st.button("Translate", type="primary"):
        if not text.strip():
            st.error("Please enter some text.")
        else:
            try:
                with st.spinner("Translating..."):
                    res = translate(text, to_lang=tgt_code, from_lang=src_code)
            except RuntimeError as e:
                st.error(str(e) + " (Set keys in .env or Streamlit Secrets.)")
                st.stop()

            st.success("Translation:")
            st.text_area("Output:", value=res["translated"], height=200, key="output_text")

            if src_code == "auto" and res["detected"]:
                st.caption(f"Detected source language: **{code_to_name.get(res['detected'], res['detected'])}**")

            st.download_button("📄 Download result", data=res["translated"], file_name="translation.txt")

# --- Multi-target tab ---
idx = 1
if features_on["multi"]:
    with tab_objs[idx]:
        st.subheader("Translate into multiple languages at once")
        text_multi = st.text_area("Text", height=150, key="multi_text")

        sel_langs = st.multiselect("Select target languages (max 3)",
                                   names,
                                   default=["Spanish", "French"] if "Spanish" in names and "French" in names else [],
                                   max_selections=3)
        tgt_codes = [codes[names.index(n)] for n in sel_langs]

        if st.button("Translate all", key="multi_btn"):
            if not text_multi.strip():
                st.error("Enter text above.")
            elif not tgt_codes:
                st.warning("Pick at least one target language.")
            else:
                try:
                    with st.spinner("Translating..."):
                        out = multi_translate(text_multi, targets=tgt_codes, from_lang="auto")
                except RuntimeError as e:
                    st.error(str(e) + " (Set keys in .env or Streamlit Secrets.)")
                    st.stop()

                st.success("Results")
                for code in tgt_codes:
                    st.markdown(f"**{code_to_name[code]} ({code})**")
                    st.code(out.get(code, ""), language=None)
    idx += 1

# --- Idioms & Slang tab ---
if features_on["idiom"]:
    with tab_objs[idx]:
        st.subheader("Slang & Idiom Detector")
        idiom_text = st.text_area("Paste any English text to analyze:", height=180, key="idiom_text")
        if st.button("Explain expressions"):
            if not idiom_text.strip():
                st.error("Please enter some text.")
            else:
                hits = explain_idioms_slang(idiom_text)
                if not hits:
                    st.info("No idioms or slang from our list were found.")
                else:
                    for h in hits:
                        st.markdown(f"**{h['phrase']}**  _({h['type']})_")
                        st.write(h["meaning"])
    idx += 1

# --- Daily Challenge tab ---
if features_on["challenge"]:
    with tab_objs[idx]:
        st.subheader(" Language Challenge 🎮")
        st.caption("Translate the random phrases to earn XP!")

        pool = challenge_pool()

        target_disp = st.selectbox("Target language", names,
                                   index=names.index("Spanish") if "Spanish" in names else 0,
                                   key="ch_tgt")
        target_code = codes[names.index(target_disp)]

        if "challenge_items" not in st.session_state:
            n_items = min(3, len(pool))
            if n_items == 0:
                st.warning("No phrases found in phrases_en.json.")
                st.stop()
            st.session_state.challenge_items = random.sample(pool, n_items)
            st.session_state.checked = False

        items = st.session_state.challenge_items
        answers = [st.text_input(f"{i+1}. {phrase}", key=f"ans_{i}") for i, phrase in enumerate(items)]

        if st.button("Check answers"):
            try:
                gold = multi_translate("\n".join(items), targets=[target_code], from_lang="en")[target_code].split("\n")
            except RuntimeError as e:
                st.error(str(e) + " (Set keys in .env or Streamlit Secrets.)")
                st.stop()

            correct = sum(u.strip().lower() == g.strip().lower() for g, u in zip(gold, answers))
            gained = correct * 10
            st.session_state.xp += gained
            st.success(f"You got {correct}/{len(items)} correct! (+{gained} XP)")

            with st.expander("Show correct answers"):
                for i, g in enumerate(gold, 1):
                    st.write(f"{i}. {g}")

        st.info(f"⭐ XP: {st.session_state.xp}")

        if st.button("New challenge"):
            st.session_state.pop("challenge_items", None)
            st.session_state.pop("checked", None)
            st.rerun()
    idx += 1

# --- About tab ---
with tab_objs[-1]:
    st.markdown("""
**VerbaPilot** – Streamlit app for the CodeAlpha AI internship.

**Stack**
- Azure Translator (Free F0)
- Streamlit
- Python

**Features**
- Instant & multi-target translation  
- Idiom & slang explanations (JSON-driven)  
- Mini‑game with XP  
- Custom CSS & sidebar toggles
    """)
