import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sqlite3
import datetime
import json
import time

# --- SAFETY CHECK: Imports ---
# This ensures the app tells you what is missing instead of just crashing
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

# --- CUSTOM STYLING (CSS) ---
st.markdown("""
    <style>
        /* Modern Gradient Background */
        .stApp {
            background: linear-gradient(to bottom right, #fdfbf7, #e8f5e9);
        }
        
        /* HERO BANNER */
        .hero-section {
            padding: 3rem 2rem;
            border-radius: 20px;
            background: linear-gradient(135deg, #1b5e20 0%, #4caf50 100%);
            color: white;
            text-align: center;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            margin-bottom: 2rem;
        }
        .hero-title {
            font-size: 3rem;
            font-weight: 800;
            margin: 0;
            text-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }
        .hero-subtitle {
            font-size: 1.2rem;
            opacity: 0.9;
            margin-top: 0.5rem;
            font-weight: 300;
        }

        /* CARD STYLING */
        div[data-testid="stMetricValue"] {
            font-size: 1.8rem;
            color: #2e7d32;
        }
        
        /* SIDEBAR */
        section[data-testid="stSidebar"] {
            background-color: #f1f8e9;
        }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
DB_FILE = 'esg_pro_v5.db' # Unique name to prevent conflicts

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # User Table
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, name TEXT, password_hash TEXT)''')
    # History Table
    c.execute('''CREATE TABLE IF NOT EXISTS history 
                 (id INTEGER PRIMARY KEY, username TEXT, timestamp TEXT, 
                  overall REAL, e_score REAL, s_score REAL, g_score REAL, 
                  details TEXT, industry TEXT)''')
    conn.commit()
    conn.close()

def register_user(username, name, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        # Secure Hashing
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        c.execute("INSERT INTO users (username, name, password_hash) VALUES (?, ?, ?)", 
                  (username, name, hashed))
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
    
    # Format for streamlit-authenticator
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

# Initialize Database
init_db()

# --- CALCULATION ENGINE ---
def calculate_scores(inputs, industry):
    # 1. Environmental
    e_raw = (
        (max(0, 100 - inputs['energy']/1000)) + 
        (max(0, 100 - inputs['water']/500)) + 
        (inputs['recycling']) + 
        (inputs['renewable'] * 1.5) + 
        (inputs['offsets'] * 2)
    ) / 5
    e_score = min(100, max(0, e_raw))

    # 2. Social
    s_raw = (
        (max(0, 100 - inputs['turnover']*2)) + 
        (max(0, 100 - inputs['incidents']*10)) + 
        (inputs['diversity']) + 
        (inputs['training'] * 2) + 
        (inputs['charity'] * 10)
    ) / 5
    s_score = min(100, max(0, s_raw))

    # 3. Governance
    g_raw = (inputs['board'] + inputs['ethics'] + 
             (100 if inputs['whistle'] else 0) + 
             (100 if inputs['privacy'] else 0) + 
             (100 if inputs['audit'] else 0)) / 5
    g_score = min(100, max(0, g_raw))

    # Industry Weights
    w = {'Gen': (0.33,0.33,0.33), 'Mfg': (0.5,0.3,0.2), 'Tech': (0.2,0.4,0.4), 'Fin': (0.1,0.4,0.5)}
    weights = w.get(industry, w['Gen'])
    
    final = (e_score * weights[0]) + (s_score * weights[1]) + (g_score * weights[2])
    return final, e_score, s_score, g_score

# --- VISUALS ---
def make_gauge(val, title, color):
    return go.Figure(go.Indicator(
        mode="gauge+number", value=val, title={'text': title},
        gauge={'axis': {'range': [None, 100]}, 'bar': {'color': color},
               'steps': [{'range': [0,50], 'color': 'white'}, {'range': [50,100], 'color': '#f1f8e9'}]}
    )).update_layout(height=250, margin=dict(l=10,r=10,t=40,b=10), paper_bgcolor='rgba(0,0,0,0)')

def make_radar(e, s, g):
    df = pd.DataFrame(dict(r=[e,s,g,e], theta=['Env','Soc','Gov','Env']))
    fig = px.line_polar(df, r='r', theta='theta', line_close=True)
    fig.update_traces(fill='toself', line_color='#2e7d32')
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), margin=dict(t=20, b=20))
    return fig

# --- AUTHENTICATION FLOW ---
credentials = get_credentials()
authenticator = stauth.Authenticate(credentials, 'green_cookie_v5', 'key_secure_v5', cookie_expiry_days=1)

# Login Widget
authenticator.login(location='main')

if st.session_state["authentication_status"]:
    # === MAIN APPLICATION ===
    username = st.session_state["username"]
    name = st.session_state["name"]
    authenticator.logout('Logout', 'sidebar')

    # Hero Banner
    st.markdown(f"""
        <div class="hero-section">
            <h1 class="hero-title">GreenInvest Analytics Pro</h1>
            <p class="hero-subtitle">Welcome, {name}. Measure, Analyze, and Optimize your Impact.</p>
        </div>
    """, unsafe_allow_html=True)

    # --- SIDEBAR INPUTS ---
    st.sidebar.header("📊 Data Input Panel")
    ind_map = {"General": "Gen", "Manufacturing": "Mfg", "Technology": "Tech", "Finance": "Fin"}
    industry_select = st.sidebar.selectbox("Industry Sector", list(ind_map.keys()))
    industry_code = ind_map[industry_select]

    with st.sidebar.form("data_form"):
        with st.expander("🌳 Environmental (5 Metrics)", expanded=True):
            e1 = st.number_input("Energy (kWh)", 50000)
            e2 = st.number_input("Water (m3)", 2000)
            e3 = st.slider("Recycling Rate (%)", 0, 100, 40)
            e4 = st.slider("Renewable Energy (%)", 0, 100, 20)
            e5 = st.number_input("Carbon Offsets (Tons)", 0)
        
        with st.expander("🤝 Social (5 Metrics)"):
            s1 = st.slider("Turnover Rate (%)", 0, 100, 15)
            s2 = st.number_input("Safety Incidents", 0)
            s3 = st.slider("Diversity in Mgmt (%)", 0, 100, 30)
            s4 = st.number_input("Training Hours/Year", 20)
            s5 = st.slider("Charity Contributions (%)", 0, 20, 1)

        with st.expander("⚖️ Governance (5 Metrics)"):
            g1 = st.slider("Board Independence (%)", 0, 100, 60)
            g2 = st.slider("Ethics Compliance (%)", 0, 100, 95)
            g3 = st.checkbox("Whistleblower Policy?", True)
            g4 = st.checkbox("Data Privacy Policy?", True)
            g5 = st.checkbox("External Audits?", True)

        submitted = st.form_submit_button("🚀 Calculate Score", type="primary")

    # --- DASHBOARD ---
    if submitted:
        inputs = {
            'energy': e1, 'water': e2, 'recycling': e3, 'renewable': e4, 'offsets': e5,
            'turnover': s1, 'incidents': s2, 'diversity': s3, 'training': s4, 'charity': s5,
            'board': g1, 'ethics': g2, 'whistle': g3, 'privacy': g4, 'audit': g5
        }
        
        final, e, s, g = calculate_scores(inputs, industry_code)
        save_data(username, final, e, s, g, inputs, industry_code)

        # Row 1: Gauges
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.plotly_chart(make_gauge(final, "Overall ESG", "#1b5e20"), use_container_width=True)
        with c2: st.plotly_chart(make_gauge(e, "Environmental", "#43a047"), use_container_width=True)
        with c3: st.plotly_chart(make_gauge(s, "Social", "#1976d2"), use_container_width=True)
        with c4: st.plotly_chart(make_gauge(g, "Governance", "#fbc02d"), use_container_width=True)

        # Row 2: Deep Dive
        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.subheader("🕸️ Balance Radar")
            st.plotly_chart(make_radar(e, s, g), use_container_width=True)

        with col_right:
            st.subheader("💡 AI Recommendations")
            if e < 70:
                st.warning(f"**Environmental:** Increase renewable energy (Current: {e4}%) to boost score.")
                st.image("https://images.unsplash.com/photo-1497435334941-8c899ee9e8e9?w=600", caption="Sustainable Action", use_container_width=True)
            elif s < 70:
                st.warning("**Social:** High turnover detected. Implement employee retention programs.")
                st.image("https://images.unsplash.com/photo-1552664730-d307ca884978?w=600", caption="Team Building", use_container_width=True)
            else:
                st.success("**Performance:** Your ESG metrics are performing well against industry standards.")
                st.image("https://images.unsplash.com/photo-1518544806352-05f31d054d55?w=600", caption="Global Impact", use_container_width=True)

    else:
        # Landing State
        st.info("👈 Use the sidebar to input your data and click Calculate.")
        
        # History
        hist_df = get_history(username)
        if not hist_df.empty:
            st.divider()
            st.subheader("📈 Historical Trends")
            st.plotly_chart(px.area(hist_df, x='Date', y='Overall', title="Your Score History"), use_container_width=True)

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
