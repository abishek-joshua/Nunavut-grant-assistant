import io
import chardet
import fitz
import streamlit as st
from docx import Document
import openai
import os

# --------------------------------
# Theme + Page Setup
# --------------------------------
st.set_page_config(page_title="Nunavut Grant Assistant", layout="wide")

# Nunavut-inspired banner colors
BLUE_BG = "background-color:#e9f4ff;border-radius:12px;padding:16px;"
GREEN_BG = "background-color:#e9ffe9;border-radius:12px;padding:16px;"

openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    st.error("❌ OpenAI API Key missing! Please add it as an environment variable in your deploy platform.")
else:
    openai.api_key = openai_api_key

# --------------------------------
# Grant Database (Business-focused)
# --------------------------------
grants = [
    {
        "name": "Northern Indigenous Economic Opportunities Program (NIEOP)",
        "funder": "Government of Canada (CanNor)",
        "purpose": "Supports Indigenous-owned business growth including equipment and expansion.",
        "apply_url": "https://www.cannor.gc.ca/eng/1385748858595/1385748915240",
        "org_type": "Business",
        "regions": ["Qikiqtaaluk", "Kivalliq", "Kitikmeot"],
        "inuit_required": True,
        "project_types": ["Start-up", "Expansion", "Equipment", "Training", "Innovation"],
        "max_funding": 250000
    },
    {
        "name": "Small Business Support Program (EDT)",
        "funder": "Government of Nunavut",
        "purpose": "Helps with starting up, equipment, and training for Nunavut entrepreneurs.",
        "apply_url": "https://www.gov.nu.ca/",
        "org_type": "Business",
        "regions": ["Qikiqtaaluk", "Kivalliq", "Kitikmeot"],
        "inuit_required": False,
        "project_types": ["Start-up", "Expansion", "Equipment", "Training"],
        "max_funding": 100000
    },
    {
        "name": "Community Tourism & Cultural Industries Program",
        "funder": "Government of Nunavut (Culture & Heritage)",
        "purpose": "Funding for cultural business promotion and tourism activities.",
        "apply_url": "https://www.gov.nu.ca/",
        "org_type": "Business",
        "regions": ["Qikiqtaaluk", "Kivalliq", "Kitikmeot"],
        "inuit_required": False,
        "project_types": ["Arts", "Culture", "Tourism", "Marketing"],
        "max_funding": 50000
    },
    {
        "name": "Kitikmeot Business Assistance Program (KBAP)",
        "funder": "Kitikmeot Inuit Association",
        "purpose": "Supports Inuit entrepreneurs in Kitikmeot for start-ups and expansion.",
        "apply_url": "https://kitia.ca/",
        "org_type": "Business",
        "regions": ["Kitikmeot"],
        "inuit_required": True,
        "project_types": ["Start-up", "Expansion", "Equipment"],
        "max_funding": 25000
    }
]

# --------------------------------
# Grant Scoring + Card Rendering
# --------------------------------
def score_grant(g, org_type, region, inuit_owned, project_type, budget):
    score = 0
    if g["org_type"] == org_type: score += 3
    if region in g["regions"]: score += 3
    if g["inuit_required"] and inuit_owned == "Yes": score += 3
    if project_type in g["project_types"]: score += 3
    if g.get("max_funding") and g["max_funding"] < budget:
        score -= 2
    return score

def render_grant_card(g, budget):
    st.markdown(f"### ✅ {g['name']}")
    st.caption(f"🏛️ {g['funder']}")
    st.write(f"{g['purpose']}")

    if g.get("max_funding"):
        st.write(f"💰 Up to: **${g['max_funding']:,}**")
        if budget > g["max_funding"]:
            short = budget - g["max_funding"]
            st.warning(f"⚠️ Shortfall: **${short:,}** — you may stack grants.")
    else:
        st.write("💰 Funding based on scope")

    st.markdown(
        f'<a href="{g["apply_url"]}" target="_blank">🔗 Apply Now →</a>',
        unsafe_allow_html=True
    )
    st.markdown("---")

# --------------------------------
# Text Extraction Helpers
# --------------------------------
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10MB

def extract_text(uploaded_file):
    raw = uploaded_file.read()
    ext = uploaded_file.name.lower().split(".")[-1]
    if ext == "pdf":
        doc = fitz.open(stream=io.BytesIO(raw), filetype="pdf")
        return "\n".join(p.get_text("text") for p in doc)
    if ext == "docx":
        doc = Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs if p.text)
    if ext == "txt":
        enc = chardet.detect(raw).get("encoding") or "utf-8"
        return raw.decode(enc, errors="replace")
    return ""

def auto_extract(files):
    texts, logs = [], []
    if not files: return "", logs
    for f in files:
        size = getattr(f,"size",len(f.getvalue()) if hasattr(f,"getvalue") else 0)
        if size > MAX_FILE_BYTES:
            logs.append(f"⚠️ {f.name} too large (>10MB)")
            continue
        txt = extract_text(f)
        if txt: texts.append(txt); logs.append(f"✅ {f.name}")
        else: logs.append(f"⚠️ No text: {f.name}")
    return "\n".join(texts), logs


# ==================================================
# ONBOARDING / GUIDANCE
# ==================================================
st.title("Nunavut Grant Assistant")

st.info(
    "This tool helps Inuit entrepreneurs and organizations:\n\n"
    "✅ Create grant proposal drafts\n"
    "✅ Improve existing proposals\n"
    "✅ Match with relevant funding programs"
)

st.markdown("💡 Tip: Choose *one* path below based on your situation.")


# ==================================================
# SUPPORTING DOCS (automatic extraction)
# ==================================================
st.subheader("📄 Supporting Documents (Optional)")
st.caption("Upload business plan, budget quotes, letters of support, etc.\n"
           "Example: Equipment quote for a $45,000 oven.")

supp_files = st.file_uploader(
    "Upload documents (PDF/DOCX/TXT)",
    type=["pdf","docx","txt"], accept_multiple_files=True)

if supp_files:
    combined, logs = auto_extract(supp_files)
    if combined:
        st.session_state.supporting_docs = combined
    with st.expander("Document processing", expanded=False):
        for l in logs: st.markdown(l)


# ==================================================
# PATH 1 — CREATE PROPOSAL
# ==================================================
st.markdown(f"<div style='{BLUE_BG}'>", unsafe_allow_html=True)
st.markdown("### ✍️ Create Proposal Draft")
st.write("Best if you **have an idea but no proposal yet**.")
st.caption("Example: A new bakery in Cambridge Bay hiring 3 Inuit staff.")

col1, col2 = st.columns(2)
with col1:
    org_type = st.selectbox("Organization Type", ["Business"])
    region = st.selectbox("Region", ["Qikiqtaaluk","Kivalliq","Kitikmeot"])
    inuit_owned = st.selectbox("Inuit-owned?", ["Yes","No"])
with col2:
    project_type = st.selectbox("Project Focus", [
        "Start-up","Expansion","Equipment","Training",
        "Arts","Tourism","Marketing","Innovation"])
    budget = st.number_input("Total Budget ($)", min_value=1, value=50000)

description = st.text_area(
    "Describe your project (1–3 paragraphs)",
    placeholder="Example: We are opening a bakery in Cambridge Bay, hiring Inuit bakers, "
                "and offering fresh food options..."
)

if st.button("Generate Proposal + Grant Matches"):
    scored = [(g, score_grant(g, org_type, region, inuit_owned, project_type, budget)) for g in grants]
    scored.sort(key=lambda x: x[1], reverse=True)
    full = [g for g,_ in scored if g.get("max_funding") and g["max_funding"] >= budget]
    partial = [g for g,_ in scored if g not in full]

    st.subheader("🎯 Full Funding Matches")
    if full:
        for g in full: render_grant_card(g, budget)
    else: st.info("No grants fully cover this budget.")

    st.subheader("⚠️ Partial Funding Options")
    if partial:
        for g in partial: render_grant_card(g, budget)
    else: st.info("No partial options.")

    context = f"""
    ORG: {org_type}
    Region: {region}
    Inuit-owned: {inuit_owned}
    Type: {project_type}
    Budget: ${budget:,}
    Description: {description}
    """
    if st.session_state.get("supporting_docs"):
        context += f"\n\nATTACHMENT INFO:\n{st.session_state.supporting_docs[:6000]}"

    prompt = f"""
    Write a Nunavut grant proposal for a {project_type} project.
    Include:
    - Executive Summary (what + why)
    - Local Need (community benefit)
    - Inuit Employment (e.g., hire Inuit Bakers)
    - Timeline (Month 1–6)
    - Budget justification (tie costs to outcomes)
    - Readiness & Sustainability
    Use:
    {context}
    """

    with st.spinner("Writing proposal..."):
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}],
            temperature=0.3)
    st.session_state.generated = resp["choices"][0]["message"]["content"]

if "generated" in st.session_state:
    st.subheader("📄 Draft Proposal")
    st.write(st.session_state.generated)
    st.download_button("⬇️ Download Proposal", st.session_state.generated, "Proposal.txt")

st.markdown("</div>", unsafe_allow_html=True)

# ==================================================
# PATH 2 — ANALYZE EXISTING DRAFT
# ==================================================
st.markdown(f"<div style='{GREEN_BG}'>", unsafe_allow_html=True)
st.markdown("### 🧠 Improve Existing Proposal")
st.write("Best if you **already have a draft**.")
st.caption("Example: You wrote a proposal for a sewing business and want help improving it.")

prop_file = st.file_uploader("Upload Proposal (PDF/DOCX/TXT)", type=["pdf","docx","txt"])

if prop_file:
    extracted, logs = auto_extract([prop_file])
    if extracted:
        st.session_state.existing = extracted
    with st.expander("Proposal processing", expanded=False):
        for l in logs: st.markdown(l)

if st.button("Analyze My Draft"):
    if not st.session_state.get("existing"):
        st.error("Upload a proposal first.")
    else:
        context = ""
        if st.session_state.get("supporting_docs"):
            context = f"\nSUPPORTING DOCS:\n{st.session_state.supporting_docs[:6000]}"

        prompt = f"""
        You are a Nunavut grant reviewer.
        Evaluate this proposal and give improvements:
        - Readiness score (0–10)
        - Missing information checklist
        - Strong + weak areas
        - Fix Inuit employment and benefit details
        - Fix timeline and budget clarity

        PROPOSAL:
        {st.session_state.existing[:10000]}

        {context}
        """

        with st.spinner("Reviewing..."):
            fb = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"user","content":prompt}],
                temperature=0.3)
        st.session_state.feedback = fb["choices"][0]["message"]["content"]
        st.success("✅ Feedback ready")

if "feedback" in st.session_state:
    st.subheader("📋 Reviewer Feedback")
    st.write(st.session_state.feedback)

    if st.button("Improve Draft"):
        improve_prompt = f"""
        Rewrite the proposal with improvements applied:
        - Add Inuit hiring plan
        - Show Month 1–6 timeline milestones
        - Strengthen budget justification
        - Add measured outcomes (jobs, food security)

        ORIGINAL:
        {st.session_state.get("existing")[:8000]}

        FEEDBACK:
        {st.session_state.feedback[:6000]}
        """

        with st.spinner("Improving..."):
            imp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"user","content":improve_prompt}],
                temperature=0.3)
        st.session_state.improved = imp["choices"][0]["message"]["content"]
        st.success("✅ Improved draft ready")

if "improved" in st.session_state:
    st.subheader("🚀 Improved Proposal")
    st.write(st.session_state.improved)
    st.download_button("⬇️ Download Improved Proposal", st.session_state.improved, "Improved.txt")

st.markdown("</div>", unsafe_allow_html=True)
