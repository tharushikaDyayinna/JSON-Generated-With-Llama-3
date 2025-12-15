import streamlit as st
from google import genai
from google.genai import types
import json

# --- 1. SETUP AND CLIENT INITIALIZATION ---
# The name used here must match the key name you save in Streamlit Cloud
try:
    # Access the API key from Streamlit's secrets storage
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except KeyError:
    st.error("API Key not found! Please set the 'GOOGLE_API_KEY' secret in the Streamlit Cloud settings.")
    st.stop() # Stop the app if the key is missing

# Initialize the client with the secret key
try:
    client = genai.Client(api_key=GOOGLE_API_KEY)
except Exception as e:
    st.error(f"Failed to initialize Google GenAI client: {e}")

# Using a powerful model suitable for complex JSON generation
GEMINI_MODEL = 'gemini-2.5-flash'


# --- 2. SESSION STATE INITIALIZATION ---
if 'messages' not in st.session_state:
    st.session_state['messages'] = []
if 'generated_json' not in st.session_state:
    st.session_state['generated_json'] = '{"formData": {"newformName": "Draft Form"}, "fieldsData": [], "operations": []}'
if 'is_initial' not in st.session_state:
    st.session_state['is_initial'] = True


# --- 3. JSON SCHEMA DEFINITION (Used for prompting) ---
# Updated to show a name-based syntax example for "options_search"
JSON_STRUCTURE_EXAMPLE = """{
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
            "keyMember": 0,
            "prefix": "POL",
            "sufix": "",
            "digits": "1",
            "replacer": "0",
            "start_with": "1"
        },
         {
            "data_name": "Customer Name",
            "data_type": "options_search",
            "sorting_value": "80",
            "formName": "Vendor Details"
            "search_syntax": "Vendor Details$Vendor Details.Vendor Name,Vendor Details.Vendor Product$Vendor Details.Vendor Product Category$Vendor Details.Vendor Product=Invoice.Product Name,Vendor Details.Vendor Product Category=Invoice.Product Category$Vendor Details.Status=Active"
        },
        {
            "data_name": "Invoice Date",
            "data_type": "date",
            "sorting_value": "30"
        },
        {
            "data_name": "Product Name",
            "data_type": "text",
            "sorting_value": "40"
        },

        {
            "data_name": "Product Category",
            "data_type": "text",
            "sorting_value": "50"
        },

        
        {
             "data_name": "Unit Price",
            "data_type": "number",
            "sorting_value": "60",
            "decimals": "2"
        },
        {
            "data_name": "Line Total",
            "data_type": "calculation",
            "sorting_value": "70",
            "calculation": "{GoodsReceived^Quantity^GoodsReceived.GRNLineID,Invoice.Product ID,=} * {Invoice.Unit Price}",
            "decimals": "2"
        }
       
    ],
    "operations": [
        {
            "id": "",
            "form": "",
            "object_field": null,
            "update_field": null,
            "fixed_update": null,
            "update_type": "d_newRecord",
            "update_val": null,
            "new_form": "851",
            "new_form_entity": "",
            "new_form_entity_level": "Needlu",
            "operation_group": "0",
            "display_name": "",
            "dest_multiplier": "0",
            "thisForm": "0",
            "sorting_fields": "",
            "map_until_field": null,
            "exe_condition": null,
            "skip_cal": null,
            "mapping": [
                ["Invoice.Invoice ID", "Invoice history.Reference No", "=", ""],
                ["Invoice.Customer Name", "Invoice history.Customer Name", "=", ""]
            ],
            "operationGroups": [
                {
                    "name": "Invoice Update",
                    "list": "1253",
                    "group_type": "0",
                    "mc_field": "0",
                    "menue_condition": "",
                    "mc_value": "",
                    "exclude_menu": "1",
                    "on_submit": "1",
                    "auth_category": "",
                    "menu_sort": "0"
                }
            ]
        }
    ]
}"""


# --- 4. CORE GENERATION / EDITING FUNCTION (FINALIZED with FormName.FieldName References) ---
def generate_or_edit_json(prompt):
    """Handles both initial JSON generation and subsequent iterative editing using the Gemini API."""

    is_initial = st.session_state['is_initial']

    # --- INSTRUCTION DETAILS FOR OPERATIONS ---
    OPERATION_RULES = """
**NEW KEY: "operations"**: This is a top-level array.
**CRITICAL INSTRUCTION FOR operationGroups**: Each object in 'operationGroups' MUST contain 'exclude_menu' with values "0", "1", "2", "3", or "4".
"""

    # --- FINALIZED INSTRUCTION FOR OPTIONS SEARCH (Using FormName.FieldName References) ---
    OPTIONS_SEARCH_RULES = """
**SPECIAL INSTRUCTION FOR DATA TYPES**:
- If the user asks for "option search", "search field", or "advanced search", you **MUST** use the exact data_type: "options_search" (with an underscore). 
- **NEVER** output "option search" (with a space).

**CRITICAL RULE FOR options_search SYNTAX**:
- For **"options_search"** type, you **MUST** include the **"formName"** key to specify the source form.
- The **"search_syntax"** key MUST use the **FULLY QUALIFIED** reference: **"FormName.FieldName"** for every field entry.

**search_syntax format**:
"Display Field Refs (comma-separated)$Hidden Field Refs (comma-separated)$Mapping (SourceRef=CurrentRef)$Filter Condition (SourceRef=Value)"

**Example of Target Syntax (Using fully qualified references)**:
"Vendor Details$Vendor Details.Vendor Name,Vendor Details.Vendor Product$Vendor Details.Vendor Product Category$Vendor Details.Vendor Product=Invoice.Product Name,Vendor Details.Vendor Product Category=Invoice.Product Category$Vendor Details.Status=Active"

**Value Logic**:
    - If the user provided specific details, use them to construct the fully qualified, name-based format.
    - If the user DID NOT provide specific details, use this **FULLY QUALIFIED** placeholder string exactly:
      "SOURCE_FORM_NAME$SOURCE_FORM_NAME.DISPLAY_FIELD1,SOURCE_FORM_NAME.DISPLAY_FIELD2$SOURCE_FORM_NAME.HIDDEN_FIELD$SOURCE_FORM_NAME.LOOKUP_FIELD=CURRENT_FORM_NAME.TARGET_FIELD$SOURCE_FORM_NAME.Status=Active"
"""

    # --- Schema Example Update (Ensure the example reflects the new syntax) ---
    # NOTE: Since the full code isn't being displayed here, the JSON_STRUCTURE_EXAMPLE 
    # must be updated in the main script to reflect the new syntax for consistency. 
    # The AI will be instructed below.

    if is_initial:
        # System instructions are set to enforce the new rules
        system_instruction = f"""Generate a complete JSON object.

**MANDATORY**: Response must be ONLY valid JSON.
**CRITICAL**: "fieldsData" and "operations" must match the provided schema structure.
**MANDATORY DATA TYPES**: The 'data_type' key MUST ONLY use: **sequence, options, options_search, date, text, number, calculation**.
**MANDATORY**: 'sorting_value' must be in intervals of 10.
**MANDATORY**: 'help_text' must be "".
**OPTIONS RULE**: For **'options'** and **'options_search'** types, include "formName".

**IMPORTANT INSTRUCTION FOR CALCULATION**: Calculations must use one of the following two formats: Simple internal reference or Complex cross-form reference.
The entire formula must be written as a **single JSON string**.

{OPERATION_RULES}
{OPTIONS_SEARCH_RULES}

JSON Structure Example (Ensure this example in your main code shows fully qualified refs):
{JSON_STRUCTURE_EXAMPLE}
"""
        user_content = f"Requirement: {prompt}"

    else:
        current_json = st.session_state['generated_json']
        system_instruction = f"""You are a JSON form editing assistant. Modify the CURRENT JSON based on the request.

**CURRENT JSON**: {current_json}

**MANDATORY**: Response must be ONLY valid JSON.
**CRITICAL**: Preserve existing fields unless asked to change.
**SCHEMA REMINDER**: Adhere to the structure in the JSON Structure Example. Use a sorting_value that is appropriate relative to existing fields.

{OPERATION_RULES}
{OPTIONS_SEARCH_RULES}

JSON Structure Example:
{JSON_STRUCTURE_EXAMPLE}
"""
        user_content = f"Please apply this change to the current JSON: {prompt}"

    # Configure request
    config = types.GenerateContentConfig(response_mime_type="application/json")

    try:
        full_prompt = f"System Instruction:\n{system_instruction}\n\nUser Request:\n{user_content}"
        
        completion = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_prompt,
            config=config
        )

        generated_text = completion.text

        try:
            parsed_json = json.loads(generated_text)
            formatted_json = json.dumps(parsed_json, indent=4)
            st.session_state['generated_json'] = formatted_json
            st.session_state['is_initial'] = False
            
            if is_initial:
                return "JSON generated. The `search_syntax` is now **mandatory** for `options_search` fields and should include the placeholder."
            else:
                return "JSON updated successfully."

        except json.JSONDecodeError:
            return f"❌ Error: Model did not return valid JSON. Raw Output: {generated_text[:200]}..."

    except Exception as e:
        return f"❌ API Error: {e}"

# --- 5. STREAMLIT UI LAYOUT ---
st.set_page_config(page_title="JSON Editor Chat", page_icon="https://www.needlu.com/webImage/needluLogoV.png", layout="wide")
st.title("Needlu Form Generator")
st.markdown("Enter your requirement below.")

# Create two columns for the split view
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Chat Interface")

    # Display the chat history
    for message in st.session_state['messages']:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle new user input
    if prompt := st.chat_input("Enter your initial form requirement or a modification"):
        # Add user message to state
        st.session_state['messages'].append({"role": "user", "content": prompt})

        # Get response from the model
        if client:
            with st.spinner(f"Processing..."):
                assistant_response_text = generate_or_edit_json(prompt)
        else:
            assistant_response_text = "❌ Google GenAI client is not initialized. Check API key configuration."

        # Add assistant response (narrative) to state
        st.session_state['messages'].append({"role": "assistant", "content": assistant_response_text})

        # Display assistant message
        with st.chat_message("assistant"):
            st.markdown(assistant_response_text)

        # Rerun to update the JSON display in col2
        st.rerun()


with col2:
    st.subheader("Current Generated JSON")

    # Display the latest generated JSON artifact
    st.code(st.session_state['generated_json'], language="json")

    # Download button for the current artifact
    st.download_button(
        label="Download Current JSON",
        data=st.session_state['generated_json'],
        file_name="generated_form_latest.json",
        mime="application/json"
    )

    if st.session_state['is_initial']:
        st.info("Start by entering your form requirement (e.g., 'Create a Purchase Order form with fields for Vendor, Item, Quantity, and Price').")
    else:
        st.success("Refine the JSON using the chat interface on the left.")


