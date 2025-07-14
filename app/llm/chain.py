from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import json
import streamlit as st

llm = ChatOpenAI(temperature=0, model_name="gpt-4.1-mini")
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
chain = LLMChain(llm=llm, prompt=prompt_template)

def extract_response(block):
    raw = chain.run(input_text=block.strip()).replace("```json", "").replace("```", "")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        st.warning(f"⚠️ JSON parsing error for block: {block[:60]}...")
        return None 