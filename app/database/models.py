import json
from psycopg2.extras import RealDictCursor, execute_values
import streamlit as st

def get_cert_list(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT cert FROM questions ORDER BY cert;")
        return [row[0] for row in cur.fetchall()]

def get_questions_for_cert(conn, cert):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, question, options, correct_answer, explanation 
            FROM questions WHERE cert=%s ORDER BY id;
        """, (cert,))
        return cur.fetchall()

def save_to_db(records, conn, cert):
    with conn.cursor() as cur:
        sql = """
        INSERT INTO questions (question, options, correct_answer, explanation, cert)
        VALUES %s
        """
        values = []
        for r in records:
            if r is None:
                continue
            question = r.get("question")
            options = r.get("options")
            correct = r.get("correct_answer")
            explanation = r.get("explanation")
            if not (question and options and correct and explanation):
                continue
            values.append((question, options, correct, explanation, cert))
        if values:
            execute_values(cur, sql, values)
            conn.commit()
            st.success(f"✅ Inserted {len(values)} questions into the database.")
        else:
            st.warning("⚠️ No valid records to insert.") 

def create_user_progress_table(conn):
    with conn.cursor() as cur:
        cur.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            username TEXT NOT NULL,
            cert TEXT NOT NULL,
            answers JSONB NOT NULL,
            reviewed JSONB NOT NULL,
            PRIMARY KEY (username, cert)
        );
        ''')
        conn.commit()

def save_user_progress(conn, username, cert, answers, reviewed):
    with conn.cursor() as cur:
        cur.execute('''
        INSERT INTO user_progress (username, cert, answers, reviewed)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (username, cert) DO UPDATE SET answers=EXCLUDED.answers, reviewed=EXCLUDED.reviewed;
        ''', (username, cert, json.dumps(answers), json.dumps(list(reviewed))))
        conn.commit()

def load_user_progress(conn, username, cert):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('''
        SELECT answers, reviewed FROM user_progress WHERE username=%s AND cert=%s;
        ''', (username, cert))
        row = cur.fetchone()
        if row:
            answers = json.loads(row['answers']) if isinstance(row['answers'], str) and row['answers'] else row['answers'] or {}
            if isinstance(row['reviewed'], list):
                reviewed = set(row['reviewed'])
            elif isinstance(row['reviewed'], str) and row['reviewed']:
                reviewed = set(json.loads(row['reviewed']))
            else:
                reviewed = set()
            return answers, reviewed
        return {}, set()

def clear_user_progress(conn, username, cert):
    with conn.cursor() as cur:
        cur.execute('''
        DELETE FROM user_progress WHERE username=%s AND cert=%s;
        ''', (username, cert))
        conn.commit() 