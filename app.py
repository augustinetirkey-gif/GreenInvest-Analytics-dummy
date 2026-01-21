import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import time
import json
import sqlite3
import datetime
import bcrypt 

# --- Import Authenticator ---
try:
    import streamlit_authenticator as stauth
except ImportError:
    st.error("Library 'streamlit-authenticator' not found. Please add it to requirements.txt")
    st.stop()

# --- Page Configuration ---
st.set_page_config(
    page_title="GreenInvest Analytics Pro",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS (Hero Banner & Cards) ---
st.markdown("""
    <style>
        /* HERO BANNER */
        .hero-container {
            background-image: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), url('https://images.unsplash.com/photo-1473448912268-2022ce9509d8?q=80&w=2641&auto=format&fit=crop');
            background-size: cover;
            background-position: center;
            padding: 4rem 2rem;
            border-radius: 20px;
            color: white;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .hero-title {
            font-size: 3.5rem;
            font-weight: 800;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        .hero-subtitle {
            font-size: 1.5rem;
            font-weight: 300;
            opacity: 0.9;
        }

        /* METRIC CARDS */
        div[data-testid="metric-container"] {
            background-color: #ffffff;
            border: 1px solid #f0f2f6;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            transition: transform 0.2s;
        }
        div[data-testid="metric-container"]:hover {
            transform: translateY(-5px);
            border-color: #4caf50;
        }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE FUNCTIONS ---
DATABASE_NAME = 'esg_data_v2.db' # Changed name to avoid conflict with old schema

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS esg_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, timestamp TEXT NOT NULL, overall_score REAL, e_score REAL, s_score REAL, g_score REAL, env_data TEXT, social_data TEXT, gov_data TEXT, industry TEXT, FOREIGN KEY (user_id) REFERENCES users (id))''')
    conn.commit()
    conn.close()

def add_user(username, password_hash, name):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash, name) VALUES (?, ?, ?)", (username, password_hash, name))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_id(username):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else None

def save_esg_history(user_id, timestamp, overall, e, s, g, env, soc, gov, industry):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO esg_history (user_id, timestamp, overall_score, e_score, s_score, g_score, env_data, social_data, gov_data, industry) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (user_id, timestamp, overall, e, s, g, json.dumps(env), json.dumps(soc), json.dumps(gov), industry))
    conn.commit()
    conn.close()

def get_esg_history(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT timestamp, overall_score, e_score, s_score, g_score, env_data, social_data, gov_data, industry FROM esg_history WHERE user_id = ? ORDER BY timestamp ASC", (user_id,))
    data = c.fetchall()
    conn.close()
    return [{'timestamp': pd.to_datetime(r[0]), 'overall_score': r[1], 'e_score': r[2], 's_score': r[3], 'g_score': r[4], 
             'env_data': json.loads(r[5]), 'social_data': json.loads(r[6]), 'gov_data': json.loads(r[7]), 'industry': r[8]} for r in data]

def get_all_users_for_authenticator():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT name, username, password_hash FROM users")
    data = c.fetchall()
    conn.close()
    return {"usernames": {r[1]: {"name": r[0], "password": r[2]} for r in data}}

init_db()

# --- ADVANCED CALCULATION LOGIC ---
def calculate_esg_score(env, soc, gov, industry):
    # Dynamic weights based on Industry
    weights = {'E': 0.33, 'S': 0.33, 'G': 0.33}
    if industry == "Manufacturing": weights = {'E': 0.5, 'S': 0.3, 'G': 0.2}
    elif industry == "Technology": weights = {'E': 0.2, 'S': 0.4, 'G': 0.4}
    elif industry == "Finance": weights = {'E': 0.1, 'S': 0.4, 'G': 0.5}

    # --- Environmental Calculation (5 Metrics) ---
    e1 = max(0, 100 - (env['energy'] / 1000))  # Energy (lower better)
    e2 = max(0, 100 - (env['water'] / 500))    # Water (lower better)
    e3 = env['recycling']                      # Recycling % (higher better)
    e4 = min(100, env['renewable'] * 2)        # Renewable % (higher better)
    e5 = min(100, env['offsets'] / 10)         # Carbon Offsets (higher better)
    e_score = (e1 + e2 + e3 + e4 + e5) / 5

    # --- Social Calculation (5 Metrics) ---
    s1 = max(0, 100 - (soc['turnover'] * 2))   # Turnover (lower better)
    s2 = max(0, 100 - (soc['incidents'] * 10)) # Incidents (lower better)
    s3 = soc['diversity']                      # Diversity % (higher better)
    s4 = min(100, soc['training'] * 2)         # Training Hours (higher better)
    s5 = min(100, soc['charity'] * 5)          # Charity % (higher better)
    s_score = (s1 + s2 + s3 + s4 + s5) / 5

    # --- Governance Calculation (5 Metrics) ---
    g1 = gov['independence']                   # Board Indep % (higher better)
    g2 = gov['ethics']                         # Ethics Training % (higher better)
    g3 = 100 if gov['whistleblower'] else 0    # Whistleblower Policy (Binary)
    g4 = 100 if gov['privacy'] else 0          # Data Privacy Policy (Binary)
    g5 = 100 if gov['audits'] else 0           # Ext Audits (Binary)
    g_score = (g1 + g2 + g3 + g4 + g5) / 5

    final = (e_score * weights['E']) + (s_score * weights['S']) + (g_score * weights['G'])
    return final, e_score, s_score, g_score

# --- VISUALIZATION FUNCTIONS ---
def create_gauge(value, title, color):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = value,
        title = {'text': title, 'font': {'size': 24}},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 50], 'color': "rgba(255, 0, 0, 0.1)"},
                {'range': [50, 80], 'color': "rgba(255, 165, 0, 0.1)"},
                {'range': [80, 100], 'color': "rgba(0, 255, 0, 0.1)"}],
            'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': value}
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor='rgba(0,0,0,0)', font={'color': "black"})
    return fig

def create_radar_chart(e, s, g):
    df = pd.DataFrame(dict(
        r=[e, s, g, e],
        theta=['Environmental', 'Social', 'Governance', 'Environmental']
    ))
    fig = px.line_polar(df, r='r', theta='theta', line_close=True)
    fig.update_traces(fill='toself', line_color='#2e7d32')
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), margin=dict(t=30, b=30))
    return fig

# --- AUTH & MAIN ---
credentials = get_all_users_for_authenticator()
authenticator = stauth.Authenticate(credentials, 'green_cookie_pro', 'secure_key_v2', cookie_expiry_days=30)
authenticator.login(location='main')

if st.session_state["authentication_status"]:
    # Logged In Setup
    username, name = st.session_state["username"], st.session_state["name"]
    st.session_state.user_id = get_user_id(username)
    authenticator.logout('Logout', 'sidebar')

    # --- HERO SECTION ---
    st.markdown(f"""
        <div class="hero-container">
            <div class="hero-title">🌍 GreenInvest Analytics Pro</div>
            <div class="hero-subtitle">Hello, {name}. Empowering your sustainable future with AI-driven insights.</div>
        </div>
    """, unsafe_allow_html=True)

    # --- INPUT SECTION (5+ Options per category) ---
    st.sidebar.header("🛠️ Data Input Panel")
    industry = st.sidebar.selectbox("Select Industry", ["General", "Manufacturing", "Technology", "Finance"])
    
    with st.sidebar.form("esg_input_form"):
        # Environmental (5 Inputs)
        with st.expander("🌳 Environmental Metrics (5 Options)", expanded=True):
            e1 = st.number_input("Energy Usage (kWh)", value=50000)
            e2 = st.number_input("Water Usage (m3)", value=2500)
            e3 = st.slider("Recycling Rate (%)", 0, 100, 40)
            e4 = st.slider("Renewable Energy Used (%)", 0, 100, 20)
            e5 = st.number_input("Carbon Offsets Purchased (Tons)", value=10)

        # Social (5 Inputs)
        with st.expander("🤝 Social Metrics (5 Options)", expanded=False):
            s1 = st.slider("Employee Turnover (%)", 0, 100, 15)
            s2 = st.number_input("Safety Incidents", value=2)
            s3 = st.slider("Leadership Diversity (%)", 0, 100, 35)
            s4 = st.number_input("Avg Training Hours/Employee", value=20)
            s5 = st.slider("Profit Donated to Charity (%)", 0, 20, 1)

        # Governance (5 Inputs)
        with st.expander("⚖️ Governance Metrics (5 Options)", expanded=False):
            g1 = st.slider("Board Independence (%)", 0, 100, 60)
            g2 = st.slider("Ethics Training Completion (%)", 0, 100, 90)
            g3 = st.checkbox("Whistleblower Policy Active?", value=True)
            g4 = st.checkbox("Data Privacy Protocol (GDPR/CCPA)?", value=True)
            g5 = st.checkbox("External Audits Conducted?", value=True)

        calc_btn = st.form_submit_button("🚀 Calculate Analysis")

    # --- MAIN DASHBOARD LOGIC ---
    if calc_btn:
        # Pack Data
        env = {'energy':e1, 'water':e2, 'recycling':e3, 'renewable':e4, 'offsets':e5}
        soc = {'turnover':s1, 'incidents':s2, 'diversity':s3, 'training':s4, 'charity':s5}
        gov = {'independence':g1, 'ethics':g2, 'whistleblower':g3, 'privacy':g4, 'audits':g5}
        
        # Calculate
        final, e, s, g = calculate_esg_score(env, soc, gov, industry)
        save_esg_history(st.session_state.user_id, datetime.datetime.now().isoformat(), final, e, s, g, env, soc, gov, industry)

        # --- VISUALIZATION ROW 1: GAUGES ---
        st.subheader(f"📊 Assessment Results ({industry} Standard)")
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.plotly_chart(create_gauge(final, "Overall Score", "#2E7D32"), use_container_width=True)
        with col2: st.plotly_chart(create_gauge(e, "Environmental", "#4CAF50"), use_container_width=True)
        with col3: st.plotly_chart(create_gauge(s, "Social", "#2196F3"), use_container_width=True)
        with col4: st.plotly_chart(create_gauge(g, "Governance", "#FF9800"), use_container_width=True)

        # --- VISUALIZATION ROW 2: RADAR & INSIGHTS ---
        col_viz, col_txt = st.columns([1, 1])
        
        with col_viz:
            st.markdown("### 🕸️ Balance Radar")
            st.plotly_chart(create_radar_chart(e, s, g), use_container_width=True)

        with col_txt:
            st.markdown("### 💡 Strategic Insights")
            
            # Smart Recommendations Logic
            if e < 70:
                st.warning(f"**Environmental Alert:** Your score ({e:.1f}) is low. Consider increasing renewable energy (currently {e4}%) or buying more offsets.")
                

[Image of wind turbines]

            else:
                st.success(f"**Environmental Strong:** Great job utilizing {e4}% renewable energy.")
                
            if s < 70:
                st.warning(f"**Social Alert:** High turnover or low training ({s4} hrs). Invest in employee retention.")
                

[Image of team meeting]

            else:
                st.success("**Social Strong:** High diversity and safety standards detected.")
                
            if g < 70:
                st.error("**Governance Critical:** Ensure policies like Whistleblower and Audits are active.")
                

[Image of legal document]

            else:
                st.info("**Governance Stable:** All major compliance protocols appear active.")

    else:
        # Default State (Instructions)
        st.info("👈 Please enter your data in the sidebar and click **'Calculate Analysis'** to generate your report.")
        
        # Show previous history if exists
        hist = get_esg_history(st.session_state.user_id)
        if hist:
            st.divider()
            st.subheader("🕰️ Historical Performance")
            hf = pd.DataFrame(hist)
            fig = px.area(hf, x='timestamp', y='overall_score', title="Your Sustainability Journey", color_discrete_sequence=['#4caf50'])
            st.plotly_chart(fig, use_container_width=True)

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')
    st.divider()
    with st.expander("✨ Register New Account"):
        with st.form("reg"):
            n = st.text_input("Full Name")
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Create Account"):
                if len(p) > 3:
                    try:
                        hashed = bcrypt.hashpw(p.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        if add_user(u, hashed, n): st.success("Created! Login above.")
                        else: st.error("Username taken.")
                    except Exception as e: st.error(str(e))
                else: st.error("Password too short.")
