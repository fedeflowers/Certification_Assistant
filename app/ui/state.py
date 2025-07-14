import streamlit as st

def update_answer(question_id):
    radio_key = f"answer_{question_id}_{st.session_state.block_selected}"
    st.session_state.block_answers[question_id] = st.session_state[radio_key]
    st.session_state.show_answer = False
    st.session_state.submitted = False 