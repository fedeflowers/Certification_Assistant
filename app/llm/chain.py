import os
import streamlit as st

# Add import for Gemini
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import json

# --- UI for LLM selection and API key ---
def get_llm():
    provider = st.session_state.get("llm_provider", "OpenAI")
    if provider == "Gemini (Google)":
        if HAS_GEMINI:
            gemini_key = os.environ.get("GOOGLE_API_KEY", "")
            if gemini_key:
                os.environ["GOOGLE_API_KEY"] = gemini_key
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        else:
            st.warning("Gemini support not installed. Please add 'langchain-google-genai' to requirements.txt and restart.")
            llm = None
    else:
        llm = ChatOpenAI(temperature=0, model_name="gpt-4.1-mini")
    return llm

prompt_template = PromptTemplate(
    input_variables=["input_text"],
    template="""
You are an expert teacher. Given a multiple-choice question with its options, respond in JSON format as follows:

"question": the question text 
"options": a list of options, each starting with a letter label (A., B., C., ...) — if the input options do not have letters, add them in this format 
"correct_answer": the letter and text of the correct option (e.g. "B. Example answer") 
"explanation": a detailed explanation of why the answer is correct 
Question text + options: 
{input_text}

Respond only with JSON:
"""
)

def extract_response(block):
    llm = get_llm()
    if llm is None:
        return None
    chain = LLMChain(llm=llm, prompt=prompt_template)
    raw = chain.run(input_text=block.strip()).replace("```json", "").replace("```", "")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        st.warning(f"⚠️ JSON parsing error for block: {block[:60]}...")
        return None 