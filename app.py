# =============================
# NEEDLU FORM GENERATOR (FINAL)
# Enforced distinction between options vs options_search
# =============================

import streamlit as st
from google import genai
from google.genai import types
import json
import re

# --------------------------------------------------
# 1. SETUP AND CLIENT INITIALIZATION
# --------------------------------------------------
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except KeyError:
    st.error("API Key not found! Please set GOOGLE_API_KEY in Streamlit secrets.")
    st.stop()

try:
    client = genai.Client(api_key=GOOGLE_API_KEY)
except Exception as e:
    st.error(f"Failed to initialize Google GenAI client: {e}")
    st.stop()

GEMINI_MODEL = "gemini-2.5-flash"

# --------------------------------------------------
# 2. SESSION STATE
# --------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "generated_json" not in st.session_state:
    st.session_state.generated_json = json.dumps(
        {"formData": {"newformName": "Draft Form"}, "fieldsData": [], "operations": []},
        indent=4,
    )
if "is_initial" not in st.session_state:
    st.session_state.is_initial = True

# --------------------------------------------------
# 3. JSON STRUCTURE EXAMPLE (CANONICAL)
# --------------------------------------------------
JSON_STRUCTURE_EXAMPLE = """
{
  "formData": {
    "entityType": "T Department",
    "formCategory": "T Form",
    "formName": "Invoice",
    "frequency": "any",
    "editable": 1,
    "deletable": 1,
    "newRec": 1,
    "parentID": 0
  },
  "fieldsData": [
    {
      "data_name": "Invoice ID",
      "data_type": "sequence",
      "sorting_value": 10,
      "help_text": "",
      "keyMember": 0,
      "prefix": "POL",
      "sufix": "",
      "digits": "1",
      "replacer": "0",
      "start_with": "1"
    },
    {
      "data_name": "Vendor Lookup",
      "data_type": "options_search",
      "sorting_value": 20,
      "help_text": "",
      "formName": "Vendor Details",
      "search_syntax": "Vendor Details$Vendor Details.Vendor Name$Vendor Details.Email$Vendor Details.Address=Invoice.Shipping Address$Vendor Details.Status=Active"
    },
    {
      "data_name": "Invoice Date",
      "data_type": "date",
      "sorting_value": 30,
      "help_text": ""
    },
    {
      "data_name": "Shipping Address",
      "data_type": "text",
      "sorting_value": 40,
      "help_text": ""
    }
  ],
  "operations": []
}
"""

# --------------------------------------------------
# 4. HARD RULES (SYSTEM PROMPT)
# --------------------------------------------------
OPERATION_RULES = """
**operations** is a top-level array.
Each operationGroup MUST contain 'exclude_menu' with values "0"-"4".
"""

OPTIONS_RULES = """
**ABSOLUTE DATA TYPE SELECTION RULES**:

1) Use "options" ONLY IF:
- Data comes from another form
- EXACTLY ONE source field is selected
- NO hidden fields
- NO field mapping
- NO filters

2) Use "options_search" IF ANY are true:
- TWO OR MORE fields involved
- ANY hidden field
- ANY mapping (Source=Target)
- ANY filter condition
- Field name contains "Lookup", "Search", or "Finder"

3) If rule (2) applies:
- "options_search" is MANDATORY
- "options" is FORBIDDEN

**options_search FORMAT (SINGLE FORMAT ONLY)**:
"SOURCE_FORM_NAME$SOURCE_FORM_NAME.DISPLAY_FIELD$SOURCE_FORM_NAME.HIDDEN_FIELD$SOURCE_FORM_NAME.LOOKUP_FIELD=CURRENT_FORM_NAME.TARGET_FIELD$SOURCE_FORM_NAME.Status=Active"

- Use FULLY QUALIFIED FormName.FieldName
- NEVER omit segments
- NEVER change order
- NEVER use numeric IDs
"""

# --------------------------------------------------
# 5. POST-GENERATION AUTO-FIX (SAFETY NET)
# --------------------------------------------------
def auto_fix_options(json_obj: dict) -> dict:
    """
    Enforce options vs options_search deterministically after generation.
    """
    for f in json_obj.get("fieldsData", []):
        name = f.get("data_name", "").lower()
        has_mapping = "search_syntax" in f
        has_hidden = "search_syntax" in f
        has_filter = "search_syntax" in f
        is_lookup_name = any(k in name for k in ["lookup", "search", "finder"])

        if f.get("data_type") == "options" and (has_mapping or has_hidden or has_filter or is_lookup_name):
            f["data_type"] = "options_search"

        if f.get("data_type") == "options_search":
            f.setdefault("help_text", "")
            if "search_syntax" not in f:
                f["search_syntax"] = (
                    "SOURCE_FORM_NAME$SOURCE_FORM_NAME.DISPLAY_FIELD$"
                    "SOURCE_FORM_NAME.HIDDEN_FIELD$"
                    "SOURCE_FORM_NAME.LOOKUP_FIELD=CURRENT_FORM_NAME.TARGET_FIELD$"
                    "SOURCE_FORM_NAME.Status=Active"
                )
    return json_obj

# --------------------------------------------------
# 6. CORE GENERATION FUNCTION
# --------------------------------------------------
def generate_or_edit_json(prompt: str) -> str:
    is_initial = st.session_state.is_initial

    if is_initial:
        system_instruction = f"""
Generate a COMPLETE JSON object.

MANDATORY:
- Output ONLY valid JSON
- sorting_value must be numeric and in steps of 10
- help_text must exist and be ""
- Allowed data_type values ONLY:
  sequence, options, options_search, date, text, number, calculation

{OPERATION_RULES}
{OPTIONS_RULES}

JSON STRUCTURE EXAMPLE:
{JSON_STRUCTURE_EXAMPLE}
"""
        user_content = f"Requirement: {prompt}"
    else:
        system_instruction = f"""
Modify the CURRENT JSON only as requested.
Preserve everything else.

CURRENT JSON:
{st.session_state.generated_json}

{OPERATION_RULES}
{OPTIONS_RULES}

JSON STRUCTURE EXAMPLE:
{JSON_STRUCTURE_EXAMPLE}
"""
        user_content = f"Change request: {prompt}"

    config = types.GenerateContentConfig(response_mime_type="application/json")

    try:
        completion = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"System Instruction:\n{system_instruction}\n\nUser Request:\n{user_content}",
            config=config,
        )

        parsed = json.loads(completion.text)
        parsed = auto_fix_options(parsed)

        st.session_state.generated_json = json.dumps(parsed, indent=4)
        st.session_state.is_initial = False
        return "JSON generated/updated successfully with enforced options vs options_search rules."

    except json.JSONDecodeError:
        return "❌ Model did not return valid JSON."
    except Exception as e:
        return f"❌ Error: {e}"

# --------------------------------------------------
# 7. STREAMLIT UI
# --------------------------------------------------
st.set_page_config(page_title="Needlu Form Generator", layout="wide")
st.title("Needlu Form Generator – Stable Options Logic")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Chat")
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if user_prompt := st.chat_input("Enter your requirement"):
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.spinner("Processing..."):
            reply = generate_or_edit_json(user_prompt)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()

with col2:
    st.subheader("Generated JSON")
    st.code(st.session_state.generated_json, language="json")
    st.download_button(
        "Download JSON",
        st.session_state.generated_json,
        file_name="generated_form.json",
        mime="application/json",
    )
