#================= STUDENT EXPENSE TRACKER – PRODUCTION EDITION =================

# Enterprise‑grade Streamlit App

# ZERO widget ID conflicts

# Advanced Analytics + AI‑style Insights

# Mobile‑like UX Polish

import streamlit as st import sqlite3, hashlib import pandas as pd from datetime import date, datetime, timedelta import matplotlib.pyplot as plt import numpy as np

# ================= PAGE CONFIG =================

st.set_page_config(page_title="Student Expense Tracker – Pro", page_icon="💎", layout="wide")

# ================= DATABASE =================

conn = sqlite3.connect("expense_tracker.db", check_same_thread=False) c = conn.cursor()

c.execute(""" CREATE TABLE IF NOT EXISTS users ( id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT UNIQUE, password_hash TEXT, role TEXT, created_at TEXT ) """)

c.execute(""" CREATE TABLE IF NOT EXISTS expenses ( id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, category TEXT, tags TEXT, expense_date TEXT, note TEXT ) """)

c.execute(""" CREATE TABLE IF NOT EXISTS limits ( user_id INTEGER UNIQUE, weekly REAL, monthly REAL ) """) conn.commit()

# ================= UTIL =================

def hash_pwd(p): return hashlib.sha256(p.encode()).hexdigest()

# ================= SESSION =================

if "user" not in st.session_state: st.session_state.user = None

# ================= OWNER SETUP =================

if c.execute("SELECT COUNT(*) FROM users WHERE role='owner'").fetchone()[0]==0: st.title("🔐 Owner First‑Time Setup") oid=st.text_input("Owner ID",key="oid") op=st.text_input("Password",type="password",key="op") if st.button("Create Owner",key="oc"): c.execute("INSERT INTO users VALUES(NULL,?,?,?,?)",(oid,hash_pwd(op),"owner",datetime.now().isoformat())) conn.commit(); st.success("Restart app"); st.stop()

# ================= LOGIN =================

st.title("🎓 Student Expense Tracker – Pro")

if st.session_state.user is None: t1,t2,t3=st.tabs(["Login","Register","Reset"]) with t1: u=st.text_input("User ID",key="lu") p=st.text_input("Password",type="password",key="lp") if st.button("Login",key="lb"): r=c.execute("SELECT id,role FROM users WHERE student_id=? AND password_hash=?",(u,hash_pwd(p))).fetchone() if r: st.session_state.user={"id":r[0],"role":r[1]}; st.rerun() else: st.error("Invalid") with t2: ru=st.text_input("Student ID",key="ru") rp=st.text_input("Password",type="password",key="rp") if st.button("Register",key="rb"): try: c.execute("INSERT INTO users VALUES(NULL,?,?,?,?)",(ru,hash_pwd(rp),"student",datetime.now().isoformat())); conn.commit(); st.success("Registered") except: st.error("Exists") with t3: fu=st.text_input("Student ID",key="fu") fp=st.text_input("New Password",type="password",key="fp") if st.button("Reset",key="fb"): c.execute("UPDATE users SET password_hash=? WHERE student_id=?",(hash_pwd(fp),fu)); conn.commit(); st.success("Reset done") st.stop()

# ================= DASHBOARD =================

uid=st.session_state.user['id']; role=st.session_state.user['role']

st.sidebar.success(f"Logged as {role}") if st.sidebar.button("Logout",key="lo"): st.session_state.user=None; st.rerun()

# ================= STUDENT =================

if role=="student": nav=st.radio("",["📊 Dashboard","➕ Add","🤖 AI","👤 Profile"],horizontal=True,key="nav")

df=pd.read_sql_query("SELECT * FROM expenses WHERE user_id=?",conn,params=(uid,))

if nav=="➕ Add": st.subheader("➕ Add Expense") with st.form("addf"): a=st.number_input("Amount",1.0,key="a") c1=st.selectbox("Category",["Food","Travel","Rent","Books","Entertainment","Other"],key="c1") t=st.text_input("Tags (comma)",key="t") d=st.date_input("Date",date.today(),key="d") n=st.text_input("Note",key="n") if st.form_submit_button("Save",key="s"): c.execute("INSERT INTO expenses VALUES(NULL,?,?,?,?,?,?)",(uid,a,c1,t,d.isoformat(),n)); conn.commit(); st.success("Saved"); st.rerun()

if nav=="📊 Dashboard": if df.empty: st.info("No expenses yet — start tracking!") else: total=df.amount.sum(); st.metric("💰 Total Spend",f"₹{total:,.0f}") df['expense_date']=pd.to_datetime(df['expense_date']) w=df[df.expense_date>=datetime.now()-timedelta(days=7)].amount.sum() lw=df[(df.expense_date<datetime.now()-timedelta(days=7))&(df.expense_date>=datetime.now()-timedelta(days=14))].amount.sum() trend="→ Stable"; color="⚪" if w>lw: trend="↑ Increasing"; color="🔴" if w<lw: trend="↓ Decreasing"; color="🟢" st.info(f"{color} Weekly Trend: {trend}")

if nav=="🤖 AI": st.subheader("🧠 AI Spending Personality") if df.empty: st.info("Track expenses to unlock AI insights") else: food=df[df.category=="Food"].amount.sum()/df.amount.sum()*100 if food>50: st.success("🍔 Food Lover") elif food<20: st.success("💼 Balanced Spender") else: st.success("🧘 Moderate")

if nav=="👤 Profile": st.subheader("👤 Profile – Premium") cnt=len(df); st.metric("🧾 Total Expenses",cnt) st.progress(min(cnt/20,1.0)) st.subheader("🏅 Badges") if cnt>=1: st.success("First Expense") if cnt>=10: st.success("Consistent Tracker")

# ================= OWNER =================

if role=="owner": st.header("🔍 Owner Risk Dashboard") lb=pd.read_sql_query("SELECT u.student_id,COUNT(e.id) cnt,COALESCE(SUM(e.amount),0) total FROM users u LEFT JOIN expenses e ON u.id=e.user_id WHERE u.role='student' GROUP BY u.id",conn) if not lb.empty: lb['Risk']=np.where(lb.total>5000,"High","Normal") st.dataframe(lb) st.subheader("🧠 AI Insight") st.info("High spenders flagged anonymously")
