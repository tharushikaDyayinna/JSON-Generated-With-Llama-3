import streamlit as st
from groq import Groq
import json


GROQ_API_KEY = "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"

# If you prefer using Streamlit Secrets for better security, you can
# uncomment the block below and remove the direct assignment above:
# try:
#     GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
# except KeyError:
#     st.error("GROQ_API_KEY not found in Streamlit Secrets. Please configure it in your app's secrets settings.")
#     GROQ_API_KEY = None # Ensure the key is None if not found

# Initialize the Groq client
client = None
if GROQ_API_KEY:
    try:
        client = Groq(api_key=GROQ_API_KEY)
        # Using Llama 3 70B for high-quality structured generation
        LLAMA3_MODEL = 'llama-3.3-70b-versatile'
    except Exception as e:
        st.error(f"Failed to initialize Groq client: {e}")

# --- Streamlit App Setup ---
st.set_page_config(page_title="Form JSON Generator (Llama 3)", page_icon="", layout="centered")
st.title("System Form JSON Generator (Llama 3)")
#st.markdown("Enter your system creation requirement, and Llama 3 will generate a complete, detailed JSON structure.")

user_input = st.text_area("Enter your system creation requirement :", "", height=150)

if st.button("Generate JSON"):
    if not GROQ_API_KEY:
        # This branch should only be reached if the key is None (e.g., if you switch back to secrets and it fails)
        st.error("Cannot proceed. The Groq API key is not configured.")
    elif not client:
        st.error("Cannot proceed. Groq client failed to initialize.")
    elif user_input.strip():

        # Define the JSON structure example for context and schema definition
        json_structure_example = """{
            "formData": {
                "entType": "T Department",
                "formCat": "T Form",
                "newformName": "Invoice",
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
                    "data_name": "LineTotal",
                    "data_type": "calculation",
                    "sorting_value": "7",
                    "identifier": 0,
                    "options_from": "",
                    "fetch_function": "",
                    "calculation": "{GoodsReceived^QuantityReceived^GoodsReceived.GRNLineID,RequestForm.CurrentLine,=} * {PurchaseOrder^UnitPrice^PurchaseOrder.POLineID,RequestForm.CurrentLine,=}",
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

        # Define the JSON schema to enforce the output structure
        json_schema = json.loads(json_structure_example)

        # --- CONSTRUCT THE PROMPT ---
        # The prompt still provides context and rules for the model.
        system_prompt = f"""You are a system automation expert. Your task is to generate a JSON object based on the user's requirement.

**CRITICAL INSTRUCTION**: Every object generated within the "fieldsData" array MUST strictly adhere to the full structure provided in the JSON Structure Example, including all keys.
**MANDATORY**: The value for the `help_text` key MUST ALWAYS be an empty string ("") for ALL fields.
**SPECIAL INSTRUCTION FOR OPTIONS**: For any field with data_type: "options", you MUST include the "formName" key to specify the source form.

**SPECIAL INSTRUCTION FOR FETCH_FUNCTION**: Use the `fetch_function` key with the following syntax for lookups:
`fm^fd^rf1,tf1,lo1 and rf2,tf2,lo2 ^ Entity Level Type`

**IMPORTANT INSTRUCTION FOR CALCULATION**: Calculations must use one of the following two formats. Use the complex format when a value needs to be fetched from another form within the calculation.
1. Simple internal reference: **{{FormName.FieldName}}** (e.g., {{Invoice.Quantity}} * {{Invoice.Price}})
2. Complex cross-form reference: **{{SourceForm^SourceField^MappingField,CurrentValue,Operator}}** (e.g., {{{{GoodsReceived^QuantityReceived^GoodsReceived.GRNLineID,RequestForm.CurrentLine,=}}}} * {{{{PurchaseOrder^UnitPrice^PurchaseOrder.POLineID,RequestForm.CurrentLine,=}}}})

JSON Structure Example (Use this exact schema):
{json_structure_example}
"""

        try:
            with st.spinner("Generating JSON with Llama 3..."):
                # --- 2. Groq API Call Implementation ---
                # Use the Groq chat.completions.create method with JSON response format
                completion = client.chat.completions.create(
                    model=LLAMA3_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Requirement: {user_input}"}
                    ],
                    # Mandate JSON output for reliability
                    response_format={"type": "json_object"}
                )

                generated_json_text = completion.choices[0].message.content

            # Attempt to parse and re-format the JSON for clean display
            try:
                # Validate and re-format the JSON
                parsed_json = json.loads(generated_json_text)
                formatted_json = json.dumps(parsed_json, indent=4)

            except json.JSONDecodeError:
                # This should rarely happen with response_format="json_object"
                formatted_json = generated_json_text
                st.error("Warning: The generated content is not perfectly valid JSON, displaying raw text.")

            # Display the JSON
            st.subheader("Generated JSON Output")
            st.code(formatted_json, language="json")

            # Download
            st.download_button(
                label="Download JSON",
                data=formatted_json,
                file_name="generated_form_llama3.json",
                mime="application/json"
            )

        except Exception as e:
            st.error(f"An error occurred during Groq API call: {e}")

    else:
        st.warning("Please enter a requirement before clicking Generate.")

