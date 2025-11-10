import streamlit as st
from google import genai
from google.genai import types 
import json

# --- 1. API Key and Client Initialization ---
GOOGLE_API_KEY = "AIzaSyBlLsEjhgb98CB_pKeDTsTxpgGItvQFzLg"

# Initialize the Google GenAI client and model name
client = None
# Using a powerful model suitable for complex JSON generation
GEMINI_MODEL = 'gemini-2.5-pro' 

if GOOGLE_API_KEY:
    try:
        # Initialize the client with the provided API key
        client = genai.Client(api_key=GOOGLE_API_KEY)
    except Exception as e:
        st.error(f"Failed to initialize Google GenAI client: {e}")

# --- 2. Session State Initialization ---
if 'messages' not in st.session_state:
    st.session_state['messages'] = []
if 'generated_json' not in st.session_state:
    # Use a dummy initial structure to check if generation has occurred
    st.session_state['generated_json'] = '{"formData": {"newformName": "Draft Form"}, "fieldsData": []}'
if 'is_initial' not in st.session_state:
    st.session_state['is_initial'] = True

# --- 3. JSON SCHEMA DEFINITION (Used for prompting) ---
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
            "data_name": "InvoiceID",
            "data_type": "sequence",
            "sorting_value": "1",
            "identifier": 0,
            "options_from": "",
            "fetch_function": "",
            "calculation": "",
            "defaultVal": "",
            "features": "",
            "inherit": 0,
            "attributes": "readonly",
            "entityMethod": "",
            "entityOrLevel": "",
            "mapping": [],
            "keyMember": 0,
            "sumClass": "",
            "data_info": "",
            "help_text": "",
            "sum_func": "",
            "countIf": "",
            "decimals": "0",
            "prefix": "INV",
            "sufix": "",
            "digits": "5",
            "replacer": "0",
            "start_with": "1"
        },
        {
            "data_name": "CustomerName",
            "data_type": "options",
            "sorting_value": "2",
            "identifier": 0,
            "options_from": "CustomerEntity",
            "fetch_function": "",
            "calculation": "",
            "defaultVal": "",
            "features": "",
            "inherit": 0,
            "attributes": "required",
            "entityMethod": "",
            "entityOrLevel": "",
            "mapping": [],
            "keyMember": 0,
            "sumClass": "",
            "data_info": "",
            "help_text": "",
            "sum_func": "",
            "countIf": "",
            "decimals": "",
            "formName": "Customers"
        },
        {
            "data_name": "InvoiceDate",
            "data_type": "date",
            "sorting_value": "3",
            "identifier": 0,
            "options_from": "",
            "fetch_function": "",
            "calculation": "",
            "defaultVal": "TODAY",
            "features": "",
            "inherit": 0,
            "attributes": "required",
            "entityMethod": "",
            "entityOrLevel": "",
            "mapping": [],
            "keyMember": 0,
            "sumClass": "",
            "data_info": "",
            "help_text": "",
            "sum_func": "",
            "countIf": "",
            "decimals": ""
        },
        {
            "data_name": "ProductID",
            "data_type": "text",
            "sorting_value": "4",
            "identifier": 0,
            "options_from": "ProductsEntity",
            "fetch_function": "",
            "calculation": "",
            "defaultVal": "",
            "features": "",
            "inherit": 0,
            "attributes": "required",
            "entityMethod": "",
            "entityOrLevel": "",
            "mapping": [],
            "keyMember": 0,
            "sumClass": "",
            "data_info": "",
            "help_text": "",
            "sum_func": "",
            "countIf": "",
            "decimals": ""
            
        },
        {
            "data_name": "Quantity",
            "data_type": "number",
            "sorting_value": "5",
            "identifier": 0,
            "options_from": "",
            "fetch_function": "",
            "calculation": "",
            "defaultVal": "",
            "features": "",
            "inherit": 0,
            "attributes": "required",
            "entityMethod": "",
            "entityOrLevel": "",
            "mapping": [],
            "keyMember": 0,
            "sumClass": "",
            "data_info": "",
            "help_text": "",
            "sum_func": "",
            "countIf": "",
            "decimals": "0"
        },
        {
            "data_name": "UnitPrice",
            "data_type": "number",
            "sorting_value": "6",
            "identifier": 0,
            "options_from": "",
            "fetch_function": "",
            "calculation": "",
            "defaultVal": "",
            "features": "",
            "inherit": 0,
            "attributes": "required",
            "entityMethod": "",
            "entityOrLevel": "",
            "mapping": [],
            "keyMember": 0,
            "sumClass": "",
            "data_info": "",
            "help_text": "",
            "sum_func": "",
            "countIf": "",
            "decimals": "2"
        },
        {
            "data_name": "LineTotal",
            "data_type": "calculation",
            "sorting_value": "7",
            "identifier": 0,
            "options_from": "",
            "fetch_function": "",
            "calculation": "{GoodsReceived^QuantityReceived^GoodsReceived.GRNLineID,Invoice.ProductID,=} * {PurchaseOrder^UnitPrice^PurchaseOrder.POLineID,Invoice.ProductID,=}",
            "defaultVal": "",
            "features": "",
            "inherit": 0,
            "attributes": "readonly",
            "entityMethod": "",
            "entityOrLevel": "",
            "mapping": [],
            "keyMember": 0,
            "sumClass": "",
            "data_info": "",
            "help_text": "",
            "sum_func": "",
            "countIf": "",
            "decimals": "2"
        }
    ]
}"""


# --- 4. CORE GENERATION / EDITING FUNCTION (Updated for Gemini) ---
def generate_or_edit_json(prompt):
    system_instruction = f"""Generate a complete JSON object for the following system creation requirement.

**MANDATORY**: Your response MUST be ONLY the complete, valid JSON object. Do not include any narrative or markdown outside of the JSON block.

**CRITICAL INSTRUCTION**: Every object generated within the "fieldsData" array MUST strictly adhere to the full structure provided in the JSON Structure Example, including all keys.
**MANDATORY**: The value for the `help_text` key MUST ALWAYS be an empty string ("") for ALL fields.
**MANDATORY DATA TYPES**: The 'data_type' key MUST ONLY use one of these values: sequence, options, date, text, number, calculation. Do not use any other data types.
**SPECIAL INSTRUCTION FOR OPTIONS**: For any field with data_type: "options", you MUST include the "formName" key to specify the source form.

**SPECIAL INSTRUCTION FOR FETCH_FUNCTION**: If the user asks to fetch or look up data from another form into a static field, use the fetch_function key with the following syntax:
fm^fd^rf1,tf1,lo1 and rf2,tf2,lo2 ^ Entity Level Type
Where:
- fm = form name
- fd = field name of value needed
- rfx = reference field in current form
- tfx = target field in fm
- lox = logic (EQUAL, GREATER, LESS, etc.)

**IMPORTANT INSTRUCTION FOR CALCULATION**: Calculations must use one of the following two formats.
Use the complex format when a value needs to be fetched from another form within the calculation.

1. Simple internal reference (MANDATORY FORMAT):
If the calculation comes as a simple internal reference, it must strictly follow the format {{FormName.FieldName}}.
Example (valid): {{Invoice.Quantity}} * {{Invoice.Price}}
Invalid examples (will be rejected): {{Invoice.Quantity}}, Invoice.Quantity, or missing double curly braces.
The double curly braces {{ }} and dot notation FormName.FieldName are mandatory.

2. Complex cross-form reference (to fetch values and calculate):
{{SourceForm^SourceField^MappingField,CurrentValue,Operator}} —
The entire formula must be written as a single JSON string (no + signs or concatenation between strings).
The operator between expressions can be +, -, *, or / depending on the mathematical logic required.
Use this structure exactly:
Example:
{{GoodsReceived^QuantityReceived^GoodsReceived.GRNLineID,Invoice.ProductID,=}} * {{PurchaseOrder^UnitPrice^PurchaseOrder.POLineID,Invoice.ProductID,=}}

JSON Structure Example (Use this exact schema for every field and match the structure of fields like 'sequence', 'options', and 'calculation'):
{JSON_STRUCTURE_EXAMPLE}
"""
        user_content = f"Requirement: {prompt}"
        
    else:
        # Iterative Editing Mode
        current_json = st.session_state['generated_json']
        system_instruction = f"""You are a JSON form editing assistant. You MUST modify the provided CURRENT JSON based on the user's request.
**CURRENT JSON**: {current_json}

**MANDATORY**: Your response MUST be ONLY the complete, modified JSON object. Do not include any narrative or markdown outside of the JSON block.
**CRITICAL**: You MUST preserve all fields not explicitly requested to be changed.
**SCHEMA REMINDER**: Adhere to the structure in the JSON Structure Example. Use a sorting_value that is appropriate relative to existing fields.

JSON Structure Example (Do not modify the JSON structure itself):
{JSON_STRUCTURE_EXAMPLE}
"""
        user_content = f"Please apply this change to the current JSON: {prompt}"
    
    # Configure the request to force JSON output
    config = types.GenerateContentConfig(
        response_mime_type="application/json"
    )

    # 2. Call the Google GenAI API
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
                return "Initial JSON structure generated successfully. You can now tell me what to modify (e.g., 'Add a field for Total Tax' or 'Change InvoiceID to start with 100')."
            else:
                return "JSON updated successfully based on your feedback."

        except json.JSONDecodeError:
            return f"❌ Error: Model did not return valid JSON. Raw Output: {generated_text[:200]}..."

    except Exception as e:
        return f"❌ API Error: {e}"


# --- 5. STREAMLIT UI LAYOUT ---
st.set_page_config(page_title="JSON Editor Chat", page_icon="https://www.needlu.com/webImage/needluLogoV.png", layout="wide")
st.title("Needlu Form Generator")
st.markdown("Enter your requirement below.")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Chat Interface")
    
    for message in st.session_state['messages']:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Enter your initial form requirement or a modification"):
        st.session_state['messages'].append({"role": "user", "content": prompt})
        
        if client:
            with st.spinner(f"Processing"):
                assistant_response_text = generate_or_edit_json(prompt)
        else:
            assistant_response_text = "❌ Google GenAI client is not initialized. Check API key configuration."

        st.session_state['messages'].append({"role": "assistant", "content": assistant_response_text})
        
        with st.chat_message("assistant"):
            st.markdown(assistant_response_text)
        
        st.rerun()


with col2:
    st.subheader("Current Generated JSON")
    
    st.code(st.session_state['generated_json'], language="json")
    
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

