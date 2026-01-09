import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import date, datetime
import matplotlib.pyplot as plt
import numpy as np

# ================= CONFIG =================
st.set_page_config(page_title="Student Expense Tracker – FINAL POLISH", page_icon="💎", layout="wide")

# ================= DB =================
conn = sqlite3.connect('expense_tracker.db', check_same_thread=False)
c = conn.cursor()

# USERS
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE,
    password_hash TEXT,
    role TEXT,
    created_at TIMESTAMP
)
""")

# EXPENSES
c.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    category TEXT,
    tags TEXT,
    expense_date DATE,
    note TEXT
)
""")

# AUDIT LOGS
c.execute("""
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT,
    timestamp TIMESTAMP
)
""")
conn.commit()

# ================= UTILS =================
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ================= SESSION =================
if 'user' not in st.session_state:
    st.session_state.user = None

# ================= OWNER ONE-TIME SETUP =================
if c.execute("SELECT COUNT(*) FROM users WHERE role='owner'").fetchone()[0] == 0:
    st.title("🔐 Owner First-Time Setup")
    with st.form("owner_setup"):
        oid = st.text_input("Create Owner User ID")
        opwd = st.text_input("Create Password", type="password")
        if st.form_submit_button("Create Owner"):
            c.execute("INSERT INTO users VALUES (NULL,?,?, 'owner',?)",
                      (oid, hash_password(opwd), datetime.now()))
            conn.commit()
            st.success("Owner created. Restart app.")
            st.stop()

# ================= LOGIN =================
st.title("🎓 Student Expense Tracker – FINAL VERSION")

if st.session_state.user is None:
    tab1, tab2, tab3 = st.tabs(["🔐 Login", "📝 Student Register", "🔁 Reset Password"])

    with tab1:
        uid = st.text_input("User ID")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            user = c.execute("SELECT id, role FROM users WHERE student_id=? AND password_hash=?",
                             (uid, hash_password(pwd))).fetchone()
            if user:
                st.session_state.user = {"id": user[0], "role": user[1]}
                c.execute("INSERT INTO audit_logs VALUES (NULL,?,?,?)",
                          (user[0], 'LOGIN', datetime.now()))
                conn.commit()
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")

    with tab2:
        sid = st.text_input("Student ID")
        spwd = st.text_input("Password", type="password")
        if st.button("Register"):
            try:
                c.execute("INSERT INTO users VALUES (NULL,?,?, 'student',?)",
                          (sid, hash_password(spwd), datetime.now()))
                conn.commit()
                st.success("Student registered")
            except:
                st.error("User already exists")

    with tab3:
        rid = st.text_input("Student User ID")
        new_pwd = st.text_input("New Password", type="password")
        if st.button("Reset Password"):
            role = c.execute("SELECT role FROM users WHERE student_id=?", (rid,)).fetchone()
            if role and role[0] == 'student':
                c.execute("UPDATE users SET password_hash=? WHERE student_id=?",
                          (hash_password(new_pwd), rid))
                conn.commit()
                st.success("Password reset successful")
            else:
                st.error("Only students can reset password")
    st.stop()

# ================= DASHBOARD =================
user_id = st.session_state.user['id']
role = st.session_state.user['role']

st.sidebar.success(f"Logged in as {role.upper()}")
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.experimental_rerun()

# ================= STUDENT =================
if role == 'student':
    st.header("📱 Student Dashboard (Mobile Friendly)")

    with st.form("add_exp"):
        amount = st.number_input("Amount", min_value=1.0)
        category = st.selectbox("Category", ["Food","Rent","Travel","Books","Entertainment","Other"])
        tags = st.text_input("Tags (comma separated)")
        exp_date = st.date_input("Date", value=date.today())
        note = st.text_input("Note")
        if st.form_submit_button("Add Expense"):
            c.execute("INSERT INTO expenses VALUES (NULL,?,?,?,?,?,?)",
                      (user_id, amount, category, tags, exp_date, note))
            c.execute("INSERT INTO audit_logs VALUES (NULL,?,?,?)",
                      (user_id, 'ADD_EXPENSE', datetime.now()))
            conn.commit()
            st.success("Expense added")

    df = pd.read_sql_query("SELECT * FROM expenses WHERE user_id=?", conn, params=(user_id,))

    if not df.empty:
        st.metric("Total Spend", f"₹{df['amount'].sum():,.2f}")

        # AI Classification
        def classify(cat):
            if cat in ['Rent','Books']:
                return 'Necessary'
            if cat == 'Entertainment':
                return 'Unnecessary'
            return 'Moderate'

        df['AI_Class'] = df['category'].apply(classify)
        st.subheader("🤖 AI Spending Classification")
        st.dataframe(df[['amount','category','AI_Class']])

        # Heatmap
        st.subheader("📊 Expense Heatmap")
        df['expense_date'] = pd.to_datetime(df['expense_date'])
        heat = df.groupby(df['expense_date'].dt.day)['amount'].sum()
        fig, ax = plt.subplots()
        ax.imshow([heat.values], aspect='auto')
        ax.set_yticks([])
        ax.set_xticks(range(len(heat.index)))
        ax.set_xticklabels(heat.index)
        st.pyplot(fig)

        # Delete
        st.subheader("✏️ Delete Expense")
        for _, r in df.iterrows():
            if st.button(f"Delete ₹{r['amount']} on {r['expense_date']}"):
                c.execute("DELETE FROM expenses WHERE id=?", (r['id'],))
                c.execute("INSERT INTO audit_logs VALUES (NULL,?,?,?)",
                          (user_id, 'DELETE_EXPENSE', datetime.now()))
                conn.commit()
                st.experimental_rerun()

# ================= OWNER =================
if role == 'owner':
    st.header("🔍 Admin Panel")

    df = pd.read_sql_query(
        "SELECT u.student_id, e.amount, e.category, e.tags, e.expense_date FROM expenses e JOIN users u ON e.user_id=u.id",
        conn)

    if not df.empty:
        st.metric("Total College Spend", f"₹{df['amount'].sum():,.2f}")
        st.subheader("📋 All Expenses")
        st.dataframe(df)

    logs = pd.read_sql_query("SELECT * FROM audit_logs", conn)
    st.subheader("🔍 Audit Logs")
    st.dataframe(logs)
