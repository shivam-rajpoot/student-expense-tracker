# ================= STUDENT EXPENSE TRACKER – FINAL COPY-READY =================
# ✅ Single-file Streamlit App
# ✅ Error-fixed
# ✅ Streamlit Cloud compatible

import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import date, datetime
import matplotlib.pyplot as plt
import numpy as np
import io

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Student Expense Tracker – Premium", page_icon="💎", layout="wide")

# ================= DATABASE =================
conn = sqlite3.connect("expense_tracker.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE,
    password_hash TEXT,
    role TEXT,
    created_at TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    category TEXT,
    tags TEXT,
    expense_date TEXT,
    note TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT,
    timestamp TEXT
)
""")
conn.commit()

# ================= UTIL =================
def hash_pwd(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ================= SESSION =================
if "user" not in st.session_state:
    st.session_state.user = None

# ================= OWNER FIRST SETUP =================
if c.execute("SELECT COUNT(*) FROM users WHERE role='owner'").fetchone()[0] == 0:
    st.title("🔐 Owner First-Time Setup")
    oid = st.text_input("Create Owner ID")
    opwd = st.text_input("Create Password", type="password")
    if st.button("Create Owner"):
        c.execute("INSERT INTO users VALUES (NULL,?,?,?,?)",
                  (oid, hash_pwd(opwd), "owner", datetime.now().isoformat()))
        conn.commit()
        st.success("Owner created. Restart app.")
        st.stop()

# ================= LOGIN =================
st.title("🎓 Student Expense Tracker – Final")

if st.session_state.user is None:
    tab1, tab2, tab3 = st.tabs(["🔐 Login","📝 Register","🔁 Reset Password"])

    with tab1:
        uid = st.text_input("User ID")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            u = c.execute("SELECT id,role FROM users WHERE student_id=? AND password_hash=?",
                          (uid, hash_pwd(pwd))).fetchone()
            if u:
                st.session_state.user = {"id":u[0],"role":u[1]}
                st.rerun()
            else:
                st.error("Invalid credentials")

    with tab2:
        sid = st.text_input("Student ID")
        spwd = st.text_input("Password", type="password")
        if st.button("Register"):
            try:
                c.execute("INSERT INTO users VALUES (NULL,?,?,?,?)",
                          (sid, hash_pwd(spwd), "student", datetime.now().isoformat()))
                conn.commit()
                st.success("Registered successfully")
            except:
                st.error("User already exists")

    with tab3:
        rid = st.text_input("Student ID")
        npwd = st.text_input("New Password", type="password")
        if st.button("Reset Password"):
            role = c.execute("SELECT role FROM users WHERE student_id=?", (rid,)).fetchone()
            if role and role[0]=="student":
                c.execute("UPDATE users SET password_hash=? WHERE student_id=?",
                          (hash_pwd(npwd), rid))
                conn.commit()
                st.success("Password reset")
            else:
                st.error("Only students can reset password")
    st.stop()

# ================= DASHBOARD =================
uid = st.session_state.user['id']
role = st.session_state.user['role']

st.sidebar.success(f"Logged in as {role}")
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# ================= STUDENT =================
if role == "student":
    nav = st.radio("", ["📊 Dashboard","➕ Add","🧠 AI","👤 Profile"], horizontal=True)

    if nav == "➕ Add":
        st.subheader("➕ Add Expense")
        with st.form("add"):
            amt = st.number_input("Amount", min_value=1.0)
            cat = st.selectbox("Category", ["Food","Travel","Rent","Books","Entertainment","Other"])
            tags = st.text_input("Tags")
            ed = st.date_input("Date", value=date.today())
            note = st.text_input("Note")
            if st.form_submit_button("Save"):
                c.execute("INSERT INTO expenses VALUES (NULL,?,?,?,?,?,?)",
                          (uid,amt,cat,tags,ed.isoformat(),note))
                conn.commit()
                st.success("Expense added")
                st.rerun()

    if nav == "📊 Dashboard":
        df = pd.read_sql_query("SELECT * FROM expenses WHERE user_id=?", conn, params=(uid,))
        if df.empty:
            st.info("📝 No expenses yet — start tracking!")
        else:
            st.metric("💰 Total Spend", f"₹{df['amount'].sum():,.0f}")

    if nav == "👤 Profile":
        st.subheader("👤 Profile – Premium")
        total = c.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM expenses WHERE user_id=?", (uid,)).fetchone()
        st.metric("🧾 Total Expenses", total[0])
        st.metric("💰 Total Spend", f"₹{total[1]:,.0f}")

        st.subheader("🏅 Achievement Badges")
        if total[0]>=1: st.success("🥇 First Expense Logged")
        if total[0]>=10: st.success("📒 Consistent Tracker")

        st.subheader("🎯 Badge Progress")
        st.progress(min(total[0]/10,1.0))

        st.subheader("🏆 Leaderboard")
        lb = pd.read_sql_query("SELECT COUNT(e.id) cnt, u.student_id FROM users u JOIN expenses e ON u.id=e.user_id GROUP BY u.id", conn)
        st.dataframe(lb)

# ================= OWNER =================
if role == "owner":
    st.header("🔍 Admin Dashboard")
    lb = pd.read_sql_query("SELECT u.student_id, COUNT(e.id) cnt, COALESCE(SUM(e.amount),0) total FROM users u LEFT JOIN expenses e ON u.id=e.user_id WHERE u.role='student' GROUP BY u.id", conn)
    if not lb.empty:
        lb['Rank'] = lb['cnt'].rank(ascending=False,method='dense').astype(int)
        st.dataframe(lb[['Rank','student_id','cnt','total']])

    st.subheader("👑 Monthly Champion")
    if not lb.empty:
        champ = lb.sort_values(['cnt','total'],ascending=[False,True]).iloc[0]
        st.success(f"Champion: {champ['student_id']}")
        st.info("🧠 AI Insight: Consistent tracking + controlled spending")

        fig,ax=plt.subplots(figsize=(6,4))
        ax.axis('off')
        ax.text(0.5,0.6,"CERTIFICATE OF ACHIEVEMENT",ha='center',fontsize=18,weight='bold')
        ax.text(0.5,0.4,champ['student_id'],ha='center',fontsize=14)
        st.pyplot(fig)
    
