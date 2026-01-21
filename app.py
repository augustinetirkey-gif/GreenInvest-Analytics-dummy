import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import json
import datetime
import time

from streamlit_authenticator import Authenticate, Hasher

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="GreenInvest Analytics",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= CUSTOM CSS =================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(to right, #ffffff, #f1f8e9);
    color: #1b3a2f;
}

@keyframes fadeInUp {
    from {opacity:0; transform:translateY(20px);}
    to {opacity:1; transform:translateY(0);}
}

.welcome {
    animation: fadeInUp 1s ease-out;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(to bottom, #2E7D32, #388E3C);
}

section[data-testid="stSidebar"] * {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# ================= DATABASE =================
DB = "esg.db"
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    name TEXT,
    password TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS esg (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    environmental INTEGER,
    social INTEGER,
    governance INTEGER,
    total INTEGER,
    created_at TEXT
)
""")
conn.commit()

# ================= AUTH =================
def get_users():
    c.execute("SELECT username, name, password FROM users")
    rows = c.fetchall()
    users = {"usernames": {}}
    for u, n, p in rows:
        users["usernames"][u] = {"name": n, "password": p}
    return users

credentials = get_users()

authenticator = Authenticate(
    credentials,
    "green_cookie",
    "green_key",
    cookie_expiry_days=1
)

name, auth_status, username = authenticator.login("Login", "main")

# ================= NOT LOGGED IN =================
if auth_status is False:
    st.error("❌ Incorrect username or password")

elif auth_status is None:
    st.info("🔐 Please login or register")

    with st.expander("🆕 New User Registration"):
        new_name = st.text_input("Name")
        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")

        if st.button("Register"):
            hashed = Hasher([new_pass]).generate()[0]
            try:
                c.execute("INSERT INTO users VALUES (?,?,?)",
                          (new_user, new_name, hashed))
                conn.commit()
                st.success("✅ Registered! Now login.")
            except:
                st.error("Username already exists")

# ================= LOGGED IN =================
else:
    authenticator.logout("Logout", "sidebar")
    st.sidebar.success(f"Welcome {name}")

    st.markdown(f"<h1 class='welcome'>🌿 GreenInvest Analytics</h1>", unsafe_allow_html=True)
    st.write("ESG Analytics Dashboard (Manual + CSV)")

    tab1, tab2, tab3 = st.tabs(["✍ Manual Entry", "📂 CSV Upload", "📊 Dashboard"])

    # ============ MANUAL ENTRY ============
    with tab1:
        st.subheader("Manual ESG Input")

        col1, col2, col3 = st.columns(3)
        with col1:
            e = st.slider("Environmental", 0, 100, 50)
        with col2:
            s = st.slider("Social", 0, 100, 50)
        with col3:
            g = st.slider("Governance", 0, 100, 50)

        total = e + s + g
        st.metric("Total ESG Score", total)

        if st.button("Save Manual Data"):
            c.execute(
                "INSERT INTO esg VALUES (NULL,?,?,?,?,?,?)",
                (username, e, s, g, total, datetime.datetime.now().isoformat())
            )
            conn.commit()
            st.success("Saved successfully")

    # ============ CSV UPLOAD ============
    with tab2:
        st.subheader("Upload CSV File")

        st.info("CSV columns: environmental, social, governance")

        csv = st.file_uploader("Upload CSV", type="csv")

        if csv:
            df = pd.read_csv(csv)
            st.dataframe(df)

            if {"environmental", "social", "governance"}.issubset(df.columns):
                if st.button("Save CSV Data"):
                    for _, r in df.iterrows():
                        total = r["environmental"] + r["social"] + r["governance"]
                        c.execute(
                            "INSERT INTO esg VALUES (NULL,?,?,?,?,?,?)",
                            (username, int(r["environmental"]), int(r["social"]),
                             int(r["governance"]), int(total),
                             datetime.datetime.now().isoformat())
                        )
                    conn.commit()
                    st.success("CSV data saved")
            else:
                st.error("Invalid CSV format")

    # ============ DASHBOARD ============
    with tab3:
        df_db = pd.read_sql(
            "SELECT * FROM esg WHERE username=?",
            conn,
            params=(username,)
        )

        if df_db.empty:
            st.warning("No data available")
        else:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_db["created_at"],
                y=df_db["environmental"],
                name="Environmental"
            ))
            fig.add_trace(go.Bar(
                x=df_db["created_at"],
                y=df_db["social"],
                name="Social"
            ))
            fig.add_trace(go.Bar(
                x=df_db["created_at"],
                y=df_db["governance"],
                name="Governance"
            ))

            fig.update_layout(
                barmode="group",
                title="ESG History"
            )

            st.plotly_chart(fig, use_container_width=True)

            latest = df_db.iloc[-1].to_dict()
            st.download_button(
                "📥 Download Latest Report (JSON)",
                json.dumps(latest, indent=4),
                file_name="esg_report.json"
            )

    st.divider()
    st.caption("Made with ❤️ for a greener future")
