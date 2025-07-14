import streamlit as st
import math
import os
import tempfile
from app.database.db import get_conn, create_table
from app.database.models import (
    get_cert_list, get_questions_for_cert, save_to_db,
    save_user_progress, load_user_progress, clear_user_progress, create_user_progress_table
)
from app.pdf_processing.extract import extract_full_text
from app.pdf_processing.parse import split_blocks
from app.llm.chain import extract_response
from app.ui.state import update_answer

QUESTIONS_PER_BLOCK = 20

REVIEWED_KEY = "reviewed_questions"

def run_quiz_app():
    st.set_page_config(layout="wide")
    st.title("📚 Certification Quiz Viewer")
    st.markdown("Select a certification and question block.")

    # --- LLM provider selection (always visible) ---
    if "llm_provider" not in st.session_state:
        st.session_state.llm_provider = "OpenAI"
    if "gemini_api_key" not in st.session_state:
        st.session_state.gemini_api_key = ""
    st.sidebar.markdown("### LLM Provider")
    st.session_state.llm_provider = st.sidebar.selectbox(
        "LLM Provider", ["OpenAI", "Gemini (Google)"], index=0 if st.session_state.llm_provider=="OpenAI" else 1, key="llm_provider_select")

    conn = get_conn()
    create_table(conn)
    create_user_progress_table(conn)

    # --- Single user mode ---
    username = "default_user"

    pdf_file = st.sidebar.file_uploader("⬆️ Upload certification PDF", type=["pdf"])

    # --- Session state initialization ---
    if "pdf_processed_name" not in st.session_state:
        st.session_state.pdf_processed_name = None
    if "cert_selected" not in st.session_state:
        st.session_state.cert_selected = None
    if "block_selected" not in st.session_state:
        st.session_state.block_selected = 1
    if "q_idx" not in st.session_state:
        st.session_state.q_idx = 0
    if "block_answers" not in st.session_state:
        st.session_state.block_answers = {}
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    if "show_answer" not in st.session_state:
        st.session_state.show_answer = False
    if REVIEWED_KEY not in st.session_state:
        st.session_state[REVIEWED_KEY] = set()

    # --- Load progress from DB when cert changes ---
    cert = st.session_state.cert_selected
    if cert and ("progress_loaded" not in st.session_state or not st.session_state["progress_loaded"]):
        answers, reviewed = load_user_progress(conn, username, cert)
        st.session_state.block_answers = answers or {}
        st.session_state[REVIEWED_KEY] = reviewed or set()
        st.session_state["progress_loaded"] = True

    # --- Clear progress button ---
    if st.sidebar.button("🗑️ Clear all progress (answers & reviews)"):
        clear_user_progress(conn, username, st.session_state.cert_selected)
        st.session_state.block_answers = {}
        st.session_state[REVIEWED_KEY] = set()
        st.session_state.submitted = False
        st.session_state.show_answer = False
        st.session_state.q_idx = 0
        st.session_state["progress_loaded"] = False
        st.success("Progress cleared! Start fresh.")
        st.rerun()

    if pdf_file is not None and st.session_state.pdf_processed_name != pdf_file.name:
        st.session_state.pdf_processed_name = pdf_file.name
        with st.sidebar:
            with st.spinner("📄 Extracting text from PDF..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    tmp_pdf.write(pdf_file.read())
                    tmp_pdf_path = tmp_pdf.name
                extracted_text = extract_full_text(tmp_pdf_path)
                os.remove(tmp_pdf_path)
        with st.sidebar:
            with st.spinner("🔍 Parsing questions..."):
                cert = os.path.splitext(pdf_file.name)[0].replace(" ", "_").lower()
                blocks = split_blocks(extracted_text)
                total = len(blocks)
                progress_bar = st.progress(0, text="Parsing progress: 0%")
                records = []
                for i, block in enumerate(blocks, 1):
                    data = extract_response(block)
                    if data:
                        records.append(data)
                    progress_percent = i / total
                    progress_bar.progress(progress_percent, text=f"Parsing progress: {int(progress_percent*100)}%")
                progress_bar.empty()
        if records:
            save_to_db(records, conn, cert)
            st.session_state.cert_selected = cert
            st.session_state.block_selected = 1
            st.session_state.q_idx = 0
            st.session_state.block_answers = {}
            st.session_state.submitted = False
            st.session_state.show_answer = False
            st.rerun()
        else:
            st.warning("❌ No valid questions extracted from the PDF.")
            st.session_state.pdf_processed_name = None

    certs = get_cert_list(conn)
    if not certs:
        st.warning("No certifications found in the database. Please upload a PDF.")
        return
    default_cert_index = certs.index(st.session_state.cert_selected) if st.session_state.cert_selected in certs else 0
    new_cert_selected = st.sidebar.selectbox("Select certification:", certs, index=default_cert_index, key="cert_select")
    if new_cert_selected != st.session_state.cert_selected:
        st.session_state.cert_selected = new_cert_selected
        st.session_state.block_selected = 1
        st.session_state.q_idx = 0
        st.session_state.block_answers = {}
        st.session_state.submitted = False
        st.session_state.show_answer = False
        st.rerun()

    questions = []
    total_questions = 0
    total_blocks = 0
    if st.session_state.cert_selected:
        questions = get_questions_for_cert(conn, st.session_state.cert_selected)
        total_questions = len(questions)
        total_blocks = math.ceil(total_questions / QUESTIONS_PER_BLOCK)

    block_options = list(range(1, total_blocks + 1)) if total_blocks > 0 else [1]
    if st.session_state.block_selected > total_blocks and total_blocks > 0:
        st.session_state.block_selected = total_blocks
    elif total_blocks == 0:
        st.session_state.block_selected = 1
    default_block_index = st.session_state.block_selected - 1 if st.session_state.block_selected <= total_blocks else 0
    new_block_selected = st.sidebar.selectbox(
        f"Select block (1-{total_blocks}):",
        options=block_options,
        index=default_block_index,
        key="block_select"
    )
    if new_block_selected != st.session_state.block_selected:
        st.session_state.block_selected = new_block_selected
        st.session_state.q_idx = 0
        st.session_state.block_answers = {}
        st.session_state.submitted = False
        st.session_state.show_answer = False
        st.rerun()

    if not questions:
        st.info("No questions available for the selected certification.")
        return

    start_idx = (st.session_state.block_selected - 1) * QUESTIONS_PER_BLOCK
    end_idx = min(start_idx + QUESTIONS_PER_BLOCK, total_questions)
    block_questions = questions[start_idx:end_idx]
    if st.session_state.q_idx >= len(block_questions):
        st.session_state.q_idx = 0

    # --- Review UI ---
    with st.sidebar.expander("🔖 Review marked questions", expanded=False):
        reviewed = st.session_state[REVIEWED_KEY]
        if reviewed:
            st.write(f"You have marked {len(reviewed)} question(s) for review.")
            for qid in reviewed:
                # Find block and index for this qid
                idx = next((i for i, q in enumerate(questions) if q["id"] == qid), None)
                if idx is not None:
                    block_num = idx // QUESTIONS_PER_BLOCK + 1
                    q_num = idx % QUESTIONS_PER_BLOCK + 1
                    if st.button(f"Go to Block {block_num}, Q{q_num}", key=f"goto_{qid}"):
                        st.session_state.block_selected = block_num
                        st.session_state.q_idx = q_num - 1
                        st.rerun()
        else:
            st.write("No questions marked for review.")

    col1_nav, col2_nav, col3_nav = st.columns([1, 2, 1])
    with col1_nav:
        if st.button("⬅️ Previous Question", key="prev_q_btn", disabled=(st.session_state.q_idx == 0)):
            st.session_state.q_idx -= 1
            st.session_state.show_answer = False
            st.session_state.submitted = False
            st.rerun()
    with col3_nav:
        if st.button("Next Question ➡️", key="next_q_btn", disabled=(st.session_state.q_idx == len(block_questions) - 1)):
            st.session_state.q_idx += 1
            st.session_state.show_answer = False
            st.session_state.submitted = False
            st.rerun()
    st.markdown("---")

    q_idx = st.session_state.q_idx
    question = block_questions[q_idx]
    st.markdown(f"### 📝 Block {st.session_state.block_selected} - Question {q_idx + 1} of {len(block_questions)}")
    st.markdown(f"<div style='font-size:18px; font-weight:600; margin-bottom:15px;'>{question['question']}</div>", unsafe_allow_html=True)
    options = question["options"]
    selected_key = f"answer_{question['id']}_{st.session_state.block_selected}"
    current_answer_for_question = st.session_state.block_answers.get(question["id"])
    if current_answer_for_question in options:
        current_radio_index = options.index(current_answer_for_question)
    else:
        current_radio_index = None
    st.radio(
        "Select your answer:",
        options=options,
        index=current_radio_index,
        key=selected_key,
        on_change=update_answer,
        args=(question["id"],),
        label_visibility="visible"
    )

    # --- Mark for review toggle ---
    qid = question["id"]
    reviewed = st.session_state[REVIEWED_KEY]
    is_reviewed = qid in reviewed
    mark_label = "Unmark review" if is_reviewed else "Mark for review"
    if st.button(f"🔖 {mark_label}", key=f"review_{qid}"):
        if is_reviewed:
            reviewed.remove(qid)
        else:
            reviewed.add(qid)
        st.session_state[REVIEWED_KEY] = reviewed
        save_user_progress(conn, username, st.session_state.cert_selected, st.session_state.block_answers, list(st.session_state[REVIEWED_KEY]))
        st.rerun()

    # --- Save answer on change ---
    if st.session_state.block_answers.get(qid) is not None:
        save_user_progress(conn, username, st.session_state.cert_selected, st.session_state.block_answers, list(st.session_state[REVIEWED_KEY]))

    if st.button("👁️ Show correct answer & explanation", key=f"show_answer_btn_{question['id']}"):
        st.session_state.show_answer = True
        st.session_state.submitted = False
    if st.session_state.show_answer:
        user_answer = st.session_state.block_answers.get(question["id"])
        is_correct = user_answer == question["correct_answer"]
        if is_correct:
            box_style = (
                "background-color:#d4edda; "
                "color:#155724; "
                "padding:15px; "
                "border-radius:6px; "
                "border-left: 5px solid #2e7d32; "
                "margin-top:15px;"
            )
            title_color = "#2e7d32"
            title_text = "Correct answer"
        else:
            box_style = (
                "background-color:#f8d7da; "
                "color:#721c24; "
                "padding:15px; "
                "border-radius:6px; "
                "border-left: 5px solid #a71d2a; "
                "margin-top:15px;"
            )
            title_color = "#a71d2a"
            title_text = "Incorrect answer"
        st.markdown(
            f"<div style='{box_style}'>"
            f"<b style='font-size:17px; color:{title_color};'>{title_text}:</b> {question['correct_answer']}<br>"
            f"<b style='font-size:17px; color:{title_color};'>Explanation:</b> {question['explanation']}"
            f"</div>", unsafe_allow_html=True)
        st.markdown("---")
    if q_idx == len(block_questions) - 1:
        if st.button("✅ Submit block answers", key="submit_block_btn"):
            answered_questions_in_block = [q_id for q_id in st.session_state.block_answers if q_id in [q['id'] for q in block_questions]]
            if len(answered_questions_in_block) < len(block_questions):
                st.warning("⚠️ Please answer all questions in this block before submitting.")
                st.session_state.submitted = False
            else:
                st.session_state.submitted = True
                st.session_state.show_answer = False
    if st.session_state.submitted:
        correct = 0
        incorrect = 0
        st.markdown("## 📊 Block Results")
        st.write(f"Total questions answered: **{len(st.session_state.block_answers)}** / **{len(block_questions)}**")
        for i, q in enumerate(block_questions):
            qid = q["id"]
            user_answer = st.session_state.block_answers.get(qid)
            correct_answer = q["correct_answer"]
            explanation = q["explanation"]
            is_correct = user_answer == correct_answer
            if is_correct:
                correct += 1
                style = (
                    "background-color:#d4edda; "
                    "color:#155724; "
                    "padding:12px 15px; "
                    "border-radius:8px; "
                    "font-weight:600; "
                    "margin-bottom:8px;"
                )
                status_icon = "✅"
            else:
                incorrect += 1
                style = (
                    "background-color:#f8d7da; "
                    "color:#721c24; "
                    "padding:12px 15px; "
                    "border-radius:8px; "
                    "font-weight:600; "
                    "margin-bottom:8px;"
                )
                status_icon = "❌"
            st.markdown(f"### {status_icon} Question {i + 1}: {q['question']}")
            user_answer_display = user_answer if user_answer else "No answer selected"
            st.markdown(
                f"<div style='{style}'>"
                f"Your Answer: {user_answer_display}"
                f"</div>",
                unsafe_allow_html=True
            )
            st.markdown(f"**Correct Answer:** {correct_answer}")
            st.markdown(f"**💡 Explanation:** {explanation}")
            st.markdown("---")
        st.markdown(f"### ✅ Correct answers: {correct}")
        st.markdown(f"### ❌ Wrong answers: {incorrect}")
        st.markdown(f"### 📝 Score: {correct} / {len(block_questions)}")
        st.markdown("---")
        if st.button("🔄 Review this block", key="review_block_btn"):
            st.session_state.q_idx = 0
            st.session_state.show_answer = False
            st.session_state.submitted = False
            st.rerun()
        if total_blocks > 0 and st.session_state.block_selected < total_blocks:
            if st.button("➡️ Move to next block", key="next_block_btn"):
                st.session_state.block_selected += 1
                st.session_state.q_idx = 0
                st.session_state.block_answers = {}
                st.session_state.submitted = False
                st.session_state.show_answer = False
                st.rerun() 