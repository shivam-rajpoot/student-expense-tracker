# ================= STUDENT EXPENSE TRACKER – PRODUCTION FINAL =================
import streamlit as st
import sqlite3, hashlib
import pandas as pd
from datetime import date, datetime
import matplotlib.pyplot as plt

st.set_page_config(page_title="Student Expense Tracker – Premium", page_icon="💎", layout="wide")

# ---------------- DB ----------------
conn = sqlite3.connect("expense_tracker.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
student_id TEXT UNIQUE,
password_hash TEXT,
role TEXT,
created_at TEXT)""")

c.execute("""CREATE TABLE IF NOT EXISTS expenses(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
amount REAL,
category TEXT,
tags TEXT,
note TEXT,
expense_date TEXT)""")

conn.commit()

def hash_pwd(p): return hashlib.sha256(p.encode()).hexdigest()

if "user" not in st.session_state:
    st.session_state.user = None

# ---------------- OWNER SETUP ----------------
if c.execute("SELECT COUNT(*) FROM users WHERE role='owner'").fetchone()[0] == 0:
    st.title("🔐 Owner First Setup")
    oid = st.text_input("Owner ID", key="oid")
    op = st.text_input("Password", type="password", key="op")
    if st.button("Create Owner", key="oc"):
        c.execute("INSERT INTO users VALUES(NULL,?,?,?,?)",
                  (oid, hash_pwd(op), "owner", datetime.now().isoformat()))
        conn.commit()
        st.success("Owner created. Restart app.")
        st.stop()

# ---------------- LOGIN ----------------
st.title("🎓 Student Expense Tracker")

if st.session_state.user is None:
    t1, t2 = st.tabs(["Login", "Register"])
    with t1:
        u = st.text_input("User ID", key="lu")
        p = st.text_input("Password", type="password", key="lp")
        if st.button("Login", key="lb"):
            r = c.execute("SELECT id,role FROM users WHERE student_id=? AND password_hash=?",
                          (u, hash_pwd(p))).fetchone()
            if r:
                st.session_state.user = {"id": r[0], "role": r[1]}
                st.rerun()
            else:
                st.error("Invalid login")
    with t2:
        ru = st.text_input("Student ID", key="ru")
        rp = st.text_input("Password", type="password", key="rp")
        if st.button("Register", key="rb"):
            try:
                c.execute("INSERT INTO users VALUES(NULL,?,?,?,?)",
                          (ru, hash_pwd(rp), "student", datetime.now().isoformat()))
                conn.commit()
                st.success("Registered")
            except:
                st.error("User exists")
    st.stop()

uid = st.session_state.user["id"]
role = st.session_state.user["role"]

st.sidebar.success(f"Logged in as {role}")
if st.sidebar.button("Logout", key="lo"):
    st.session_state.user = None
    st.rerun()

# ---------------- STUDENT ----------------
if role == "student":
    nav = st.radio("", ["Dashboard", "Add", "Profile"], horizontal=True, key="nav")

    if nav == "Add":
        st.subheader("➕ Add Expense")
        with st.form("addf"):
            amt = st.number_input("Amount", min_value=1.0, key="amt")
            cat = st.selectbox("Category",
                               ["Food","Travel","Rent","Books","Entertainment","Other"], key="cat")

            tag_options = ["Urgent","Optional","Daily","Monthly","College","Personal"]
            sel_tags = st.multiselect("Select Tags", tag_options, key="stags")
            custom_tag = st.text_input("Custom Tag (optional)", key="ctag")

            note_options = ["Lunch","Bus","Movie","Stationary","Fees"]
            sel_note = st.selectbox("Select Note", [""]+note_options, key="snote")
            custom_note = st.text_input("Custom Note (optional)", key="cnote")

            ed = st.date_input("Date", value=date.today(), key="dt")

            if st.form_submit_button("Save"):
                tags = ",".join(sel_tags + ([custom_tag] if custom_tag else []))
                note = custom_note if custom_note else sel_note
                c.execute("INSERT INTO expenses VALUES(NULL,?,?,?,?,?,?)",
                          (uid, amt, cat, tags, note, ed.isoformat()))
                conn.commit()
                st.success("Expense added")
                st.rerun()

    if nav == "Dashboard":
        df = pd.read_sql_query("SELECT * FROM expenses WHERE user_id=?", conn, params=(uid,))
        if df.empty:
            st.info("No expenses yet — start tracking!")
        else:
            st.metric("Total Spend", f"₹{df.amount.sum():,.0f}")
            st.dataframe(df, use_container_width=True)

    if nav == "Profile":
        st.subheader("👤 Profile")
        cnt, total = c.execute(
            "SELECT COUNT(*),COALESCE(SUM(amount),0) FROM expenses WHERE user_id=?",(uid,)
        ).fetchone()
        st.metric("Expenses Logged", cnt)
        st.metric("Total Spend", f"₹{total:,.0f}")
        st.subheader("🏅 Achievements")
        if cnt>=1: st.success("First Expense")
        if cnt>=10: st.success("Consistent Tracker")
        st.progress(min(cnt/10,1.0))

# ---------------- OWNER ----------------
if role == "owner":
    st.header("Admin Dashboard")
    df = pd.read_sql_query("""
    SELECT u.student_id, COUNT(e.id) cnt, COALESCE(SUM(e.amount),0) total
    FROM users u LEFT JOIN expenses e ON u.id=e.user_id
    WHERE u.role='student' GROUP BY u.id
    """, conn)
    if not df.empty:
        df["Rank"] = df["cnt"].rank(ascending=False, method="dense").astype(int)
        st.dataframe(df, use_container_width=True)
                     
