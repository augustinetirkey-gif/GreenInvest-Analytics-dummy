import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sqlite3
import datetime
import json
import time

# --- SAFETY CHECK: Imports ---
try:
    import bcrypt
    import streamlit_authenticator as stauth
except ImportError as e:
    st.error(f"❌ Missing Library Error: {e}")
    st.info("Please run: pip install streamlit-authenticator bcrypt")
    st.stop()

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="GreenInvest Pro",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM STYLING ---
st.markdown("""
    <style>
        .stApp { background: linear-gradient(to bottom right, #fdfbf7, #e8f5e9); }
        .hero-section {
            padding: 3rem 2rem;
            border-radius: 20px;
            background: linear-gradient(135deg, #1b5e20 0%, #4caf50 100%);
            color: white;
            text-align: center;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            margin-bottom: 2rem;
        }
        .hero-title { font-size: 3rem; font-weight: 800; margin: 0; text-shadow: 0 2px 5px rgba(0,0,0,0.3); }
        .hero-subtitle { font-size: 1.2rem; opacity: 0.9; margin-top: 0.5rem; font-weight: 300; }
        
        /* Tab Styling */
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            height: 50px; white-space: pre-wrap; background-color: #f1f8e9; border-radius: 5px; color: #2e7d32; font-weight: 600;
        }
        .stTabs [aria-selected="true"] { background-color: #2e7d32; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
DB_FILE = 'esg_pro_final.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, name TEXT, password_hash TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, username TEXT, timestamp TEXT, overall REAL, e_score REAL, s_score REAL, g_score REAL, details TEXT, industry TEXT)''')
    conn.commit()
    conn.close()

def register_user(username, name, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        c.execute("INSERT INTO users (username, name, password_hash) VALUES (?, ?, ?)", (username, name, hashed))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_credentials():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username, name, password_hash FROM users")
    users = c.fetchall()
    conn.close()
    creds = {"usernames": {}}
    for u, n, p in users:
        creds["usernames"][u] = {"name": n, "password": p}
    return creds

def save_data(username, overall, e, s, g, details, industry):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO history (username, timestamp, overall, e_score, s_score, g_score, details, industry) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (username, datetime.datetime.now().isoformat(), overall, e, s, g, json.dumps(details), industry))
    conn.commit()
    conn.close()

def get_history(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT timestamp, overall, e_score, s_score, g_score FROM history WHERE username = ? ORDER BY timestamp ASC", (username,))
    data = c.fetchall()
    conn.close()
    return pd.DataFrame(data, columns=['Date', 'Overall', 'Environmental', 'Social', 'Governance'])

init_db()

# --- CALCULATION ENGINE ---
def calculate_scores(inputs, industry):
    # 1. Environmental Logic
    e_raw = ((max(0, 100 - inputs['energy']/1000)) + (max(0, 100 - inputs['water']/500)) + (inputs['recycling']) + (inputs['renewable'] * 1.5) + (inputs['offsets'] * 2)) / 5
    e_score = min(100, max(0, e_raw))

    # 2. Social Logic
    s_raw = ((max(0, 100 - inputs['turnover']*2)) + (max(0, 100 - inputs['incidents']*10)) + (inputs['diversity']) + (inputs['training'] * 2) + (inputs['charity'] * 10)) / 5
    s_score = min(100, max(0, s_raw))

    # 3. Governance Logic
    g_raw = (inputs['board'] + inputs['ethics'] + (100 if inputs['whistle'] else 0) + (100 if inputs['privacy'] else 0) + (100 if inputs['audit'] else 0)) / 5
    g_score = min(100, max(0, g_raw))

    # 4. Industry Weighting
    w = {'Gen': (0.33,0.33,0.33), 'Mfg': (0.5,0.3,0.2), 'Tech': (0.2,0.4,0.4), 'Fin': (0.1,0.4,0.5)}
    weights = w.get(industry, w['Gen'])
    
    final = (e_score * weights[0]) + (s_score * weights[1]) + (g_score * weights[2])
    return final, e_score, s_score, g_score

# --- VISUALIZATION HELPERS ---
def make_gauge(val, title, color):
    return go.Figure(go.Indicator(
        mode="gauge+number", value=val, title={'text': title},
        gauge={'axis': {'range': [None, 100]}, 'bar': {'color': color}, 'steps': [{'range': [0,50], 'color': 'white'}, {'range': [50,100], 'color': '#f1f8e9'}]}
    )).update_layout(height=250, margin=dict(l=10,r=10,t=40,b=10), paper_bgcolor='rgba(0,0,0,0)')

def make_radar(e, s, g):
    df = pd.DataFrame(dict(r=[e,s,g,e], theta=['Env','Soc','Gov','Env']))
    fig = px.line_polar(df, r='r', theta='theta', line_close=True)
    fig.update_traces(fill='toself', line_color='#2e7d32')
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), margin=dict(t=20, b=20))
    return fig

# --- AUTHENTICATION FLOW ---
credentials = get_credentials()
authenticator = stauth.Authenticate(credentials, 'green_cookie_final', 'secure_key_final', cookie_expiry_days=1)
authenticator.login(location='main')

if st.session_state["authentication_status"]:
    # === LOGGED IN ===
    username = st.session_state["username"]
    name = st.session_state["name"]
    authenticator.logout('Logout', 'sidebar')

    # Hero Banner
    st.markdown(f"""
        <div class="hero-section">
            <h1 class="hero-title">GreenInvest Pro</h1>
            <p class="hero-subtitle">Welcome, {name}. Measure, Analyze, and Optimize your Impact.</p>
        </div>
    """, unsafe_allow_html=True)

    # --- SIDEBAR INPUTS ---
    st.sidebar.header("🛠️ Data Input Panel")
    input_method = st.sidebar.radio("Choose Input Method:", ["Manual Entry", "Upload CSV"])
    
    ind_map = {"General": "Gen", "Manufacturing": "Mfg", "Technology": "Tech", "Finance": "Fin"}
    industry_select = st.sidebar.selectbox("Industry Sector", list(ind_map.keys()))
    industry_code = ind_map[industry_select]

    inputs = {}
    calc_triggered = False

    # 1. MANUAL INPUT
    if input_method == "Manual Entry":
        with st.sidebar.form("manual_form"):
            with st.expander("🌳 Environmental", expanded=True):
                e1 = st.number_input("Energy (kWh)", 50000)
                e2 = st.number_input("Water (m3)", 2000)
                e3 = st.slider("Recycling Rate (%)", 0, 100, 40)
                e4 = st.slider("Renewable Energy (%)", 0, 100, 20)
                e5 = st.number_input("Carbon Offsets (Tons)", 0)
            with st.expander("🤝 Social"):
                s1 = st.slider("Turnover Rate (%)", 0, 100, 15)
                s2 = st.number_input("Safety Incidents", 0)
                s3 = st.slider("Diversity (%)", 0, 100, 30)
                s4 = st.number_input("Training Hours", 20)
                s5 = st.slider("Charity (%)", 0, 20, 1)
            with st.expander("⚖️ Governance"):
                g1 = st.slider("Board Independence (%)", 0, 100, 60)
                g2 = st.slider("Ethics Compliance (%)", 0, 100, 95)
                g3 = st.checkbox("Whistleblower Policy?", True)
                g4 = st.checkbox("Data Privacy Policy?", True)
                g5 = st.checkbox("External Audits?", True)
            if st.form_submit_button("🚀 Calculate Score"):
                inputs = {'energy':e1, 'water':e2, 'recycling':e3, 'renewable':e4, 'offsets':e5,
                          'turnover':s1, 'incidents':s2, 'diversity':s3, 'training':s4, 'charity':s5,
                          'board':g1, 'ethics':g2, 'whistle':g3, 'privacy':g4, 'audit':g5}
                calc_triggered = True

    # 2. CSV UPLOAD
    else:
        # Create Template
        template = pd.DataFrame({'energy': [50000], 'water': [2000], 'recycling': [40], 'renewable': [20], 'offsets': [0],
                                 'turnover': [15], 'incidents': [0], 'diversity': [30], 'training': [20], 'charity': [1],
                                 'board': [60], 'ethics': [95], 'whistle': [1], 'privacy': [1], 'audit': [1]})
        st.sidebar.download_button("Download Template CSV", template.to_csv(index=False), "esg_template.csv")
        
        uploaded_file = st.sidebar.file_uploader("Upload CSV", type=['csv'])
        if uploaded_file and st.sidebar.button("Process CSV"):
            try:
                df = pd.read_csv(uploaded_file)
                # Map first row to inputs
                inputs = df.iloc[0].to_dict()
                calc_triggered = True
            except Exception as e:
                st.error(f"Error reading CSV: {e}")

    # --- MAIN DASHBOARD LOGIC ---
    if calc_triggered:
        final, e, s, g = calculate_scores(inputs, industry_code)
        save_data(username, final, e, s, g, inputs, industry_code)

        # TABS FOR RESULTS
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📈 Analysis Charts", "🤔 Why This Score?", "🚀 Recommendations"])

        with tab1:
            st.subheader("Executive Summary")
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.plotly_chart(make_gauge(final, "Overall ESG", "#1b5e20"), use_container_width=True)
            with c2: st.plotly_chart(make_gauge(e, "Environmental", "#43a047"), use_container_width=True)
            with c3: st.plotly_chart(make_gauge(s, "Social", "#1976d2"), use_container_width=True)
            with c4: st.plotly_chart(make_gauge(g, "Governance", "#fbc02d"), use_container_width=True)

        with tab2:
            col_radar, col_bar = st.columns(2)
            with col_radar:
                st.subheader("Balance Radar")
                st.plotly_chart(make_radar(e, s, g), use_container_width=True)
            with col_bar:
                st.subheader("Score Breakdown")
                chart_data = pd.DataFrame({'Category': ['Env', 'Soc', 'Gov'], 'Score': [e, s, g]})
                st.plotly_chart(px.bar(chart_data, x='Category', y='Score', color='Category', color_discrete_sequence=['#43a047', '#1976d2', '#fbc02d']), use_container_width=True)

        with tab3:
            st.subheader("Score Driver Analysis")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.info(f"**Environmental: {e:.1f}**")
                st.write(f"- Renewable Energy: {inputs['renewable']}%")
                st.write(f"- Recycling Rate: {inputs['recycling']}%")
            with c2:
                st.info(f"**Social: {s:.1f}**")
                st.write(f"- Employee Turnover: {inputs['turnover']}%")
                st.write(f"- Diversity: {inputs['diversity']}%")
            with c3:
                st.info(f"**Governance: {g:.1f}**")
                st.write(f"- Board Independence: {inputs['board']}%")
                st.write(f"- Audits Active: {'Yes' if inputs['audit'] else 'No'}")

        with tab4:
            st.subheader("AI-Driven Improvement Plan")
            
            if e < 70:
                st.warning("⚠️ **Priority: Environmental**")
                st.write("Your energy efficiency is dragging down your score. Switch to LED lighting and purchase carbon credits.")
                st.image("https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?w=800", caption="Invest in LED & Solar", use_container_width=True)
            
            elif s < 70:
                st.warning("⚠️ **Priority: Social**")
                st.write("Turnover is high. Implement a wellness program and increase training hours.")
                st.image("https://images.unsplash.com/photo-1521737604893-d14cc237f11d?w=800", caption="Team Culture Building", use_container_width=True)
            
            else:
                st.success("✅ **Status: Excellent**")
                st.write("You are a sustainability leader! Focus on maintaining compliance and publishing your annual ESG report.")
                st.image("https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=800", caption="Market Leadership", use_container_width=True)

    else:
        # Default Landing
        st.info("👈 Use the sidebar to input data manually or upload a CSV.")
        hist = get_history(username)
        if not hist.empty:
            st.divider()
            st.subheader("Your Progress Trend")
            st.plotly_chart(px.area(hist, x='Date', y='Overall', title="Score History"), use_container_width=True)

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')
    st.divider()
    with st.expander("📝 Register New Account"):
        with st.form("reg_form"):
            new_name = st.text_input("Full Name")
            new_user = st.text_input("Username")
            new_pass = st.text_input("Password", type="password")
            if st.form_submit_button("Sign Up"):
                if len(new_pass) > 3:
                    if register_user(new_user, new_name, new_pass):
                        st.success("Account created! Log in above.")
                    else:
                        st.error("Username already exists.")
                else:
                    st.error("Password must be at least 4 characters.")
