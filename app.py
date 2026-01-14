import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import json
import sqlite3
import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import json
import sqlite3
import datetime

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="GreenInvest Analytics",
    page_icon="🌿",
    layout="wide"
)

# ---------------- TITLE ----------------
st.title("🌿 GreenInvest Analytics Dashboard")

# ---------------- SIDEBAR MENU ----------------
menu = st.sidebar.radio(
    "Navigation",
    ["Home", "Upload Data", "Analytics", "Database"]
)

# ---------------- HOME ----------------
if menu == "Home":
    st.header("Welcome to GreenInvest Analytics")
    st.write("""
    This platform helps you analyze green investment trends,
    visualize data and store investment records efficiently.
    """)

# ---------------- UPLOAD DATA ----------------
elif menu == "Upload Data":
    st.header("Upload Your Investment Data")

    file = st.file_uploader("Upload CSV File", type=["csv"])

    if file is not None:
        df = pd.read_csv(file)
        st.success("File Uploaded Successfully!")
        st.dataframe(df)

# ---------------- ANALYTICS ----------------
elif menu == "Analytics":
    st.header("Investment Analytics")

    file = st.file_uploader("Upload CSV File for Analysis", type=["csv"], key="analysis")

    if file is not None:
        df = pd.read_csv(file)
        st.dataframe(df)

        column = st.selectbox("Select Column to Visualize", df.columns)

        fig = go.Figure()
        fig.add_trace(go.Bar(x=df.index, y=df[column]))
        fig.update_layout(title=f"{column} Analysis")

        st.plotly_chart(fig, use_container_width=True)

# ---------------- DATABASE ----------------
elif menu == "Database":
    st.header("Investment Database")

    conn = sqlite3.connect("greeninvest.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS investments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            amount REAL
        )
    """)
    conn.commit()

    date = st.date_input("Select Date", datetime.date.today())
    amount = st.number_input("Investment Amount", min_value=0.0)

    if st.button("Save Record"):
        cursor.execute("INSERT INTO investments(date, amount) VALUES(?,?)",
                       (str(date), amount))
        conn.commit()
        st.success("Record Saved Successfully!")

    st.subheader("Stored Records")
    df = pd.read_sql("SELECT * FROM investments", conn)
    st.dataframe(df)

    conn.close()
