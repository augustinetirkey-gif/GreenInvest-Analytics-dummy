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

# --- PDF LIBRARY CHECK ---
try:
    from fpdf import FPDF
    pdf_available = True
except ImportError:
    pdf_available = False

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="GreenInvest Elite",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- GAMER THEME CSS (FREE FIRE STYLE) ---
st.markdown("""
    <style>
        /* 1. BACKGROUND: Deep "Game Lobby" Gradient */
        .stApp {
            background: linear-gradient(to right, #0f0c29, #302b63, #24243e);
            color: #ffffff;
        }

        /* 2. TEXT VISIBILITY FIX - FORCE WHITE TEXT EVERYWHERE */
        h1, h2, h3, h4, h5, h6, p, label, .stTextInput > label, .stNumberInput > label, .stSlider > label {
            color: #ffffff !important;
            font-family: 'Verdana', sans-serif;
            text-shadow: 0px 2px 4px rgba(0,0,0,0.8);
        }

        /* 3. INPUT FIELDS - Dark Grey with White Text (High Contrast) */
        .stTextInput input, .stNumberInput input {
            background-color: #1e1e2f;
            color: #00ffcc !important; /* Cyber Cyan Text */
            border: 1px solid #FFD700; /* Gold Border */
            border-radius: 5px;
        }
        
        /* 4. BUTTONS - "Ranked Match" Style (Gold/Orange Gradient) */
        div.stButton > button {
            background: linear-gradient(45deg, #FFD700, #FF8C00);
            color: black;
            font-weight: bold;
            border: none;
            border-radius: 5px;
            box-shadow: 0 4px 15px rgba(255, 215, 0, 0.4);
            transition: transform 0.2s;
        }
        div.stButton > button:hover {
            transform: scale(1.05);
            color: white;
        }

        /* 5. METRIC CARDS - HUD Style */
        [data-testid="stMetricValue"] {
            font-size: 3rem !important;
            font-weight: 800;
            color: #00ff00 !important; /* Neon Green Score */
            text-shadow: 0 0 10px rgba(0, 255, 0, 0.6);
        }
        [data-testid="stMetricLabel"] {
            color: #FFD700 !important; /* Gold Label */
            font-weight: bold;
        }
        div[data-testid="metric-container"] {
            background-color: rgba(0, 0, 0, 0.6);
            border: 1px solid #333;
            border-left: 5px solid #FFD700;
            padding: 15px;
            border-radius: 10px;
        }

        /* 6. SIDEBAR - Dark Ops Style */
        section[data-testid="stSidebar"] {
            background-color: #121212;
            border-right: 2px solid #FFD700;
        }

        /* 7. TABS - Neon Selection */
        .stTabs [aria-selected="true"] {
            background-color: #FF8C00 !important;
            color: white !important;
            font-weight: bold;
        }
        
        /* 8. EXPANDERS - Glass Effect */
        .streamlit-expanderHeader {
            background-color: rgba(255, 255, 255, 0.1);
            color: white !important;
            border-radius: 5px;
        }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
DB_FILE = 'esg_elite.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, name TEXT, password_hash TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, username TEXT, timestamp TEXT, overall REAL, e_score REAL, s_score REAL, g_score REAL, details TEXT)''')
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

def save_data(username, overall, e, s, g, details):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO history (username, timestamp, overall, e_score, s_score, g_score, details) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (username, datetime.datetime.now().isoformat(), overall, e, s, g, json.dumps(details)))
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

# --- PDF GENERATOR ---
if pdf_available:
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            self.cell(0, 10, 'GreenInvest Elite Report', 0, 1, 'C')
            self.ln(5)
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def create_pdf(name, overall, e, s, g, inputs):
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Player Name: {name}", ln=True, align='L')
        pdf.cell(200, 10, txt=f"Mission Date: {datetime.datetime.now().strftime('%Y-%m-%d')}", ln=True, align='L')
        pdf.ln(10)
        
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Mission Stats (Scores)", ln=True, align='L')
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Total Rank: {overall:.1f} / 100", ln=True)
        pdf.cell(200, 10, txt=f"Env Score: {e:.1f}", ln=True)
        pdf.cell(200, 10, txt=f"Soc Score: {s:.1f}", ln=True)
        pdf.cell(200, 10, txt=f"Gov Score: {g:.1f}", ln=True)
        pdf.ln(10)
        
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Inventory (Input Data)", ln=True, align='L')
        pdf.set_font("Arial", size=10)
        for key, value in inputs.items():
            pdf.cell(200, 7, txt=f"{key}: {value}", ln=True)
        return pdf.output(dest='S').encode('latin-1')

# --- CALCULATION ENGINE ---
def calculate_scores(inputs):
    energy = float(inputs.get('energy', 50000))
    water = float(inputs.get('water', 2000))
    recycling = float(inputs.get('recycling', 40))
    renewable = float(inputs.get('renewable', 0))
    turnover = float(inputs.get('turnover', 15))
    incidents = float(inputs.get('incidents', 0))
    diversity = float(inputs.get('diversity', 30))
    board = float(inputs.get('board', 60))
    ethics = float(inputs.get('ethics', 95))

    e_raw = ((max(0, 100 - energy/1000)) + (max(0, 100 - water/500)) + (recycling) + (renewable * 1.5)) / 4
    e_score = min(100, max(0, e_raw))

    s_raw = ((max(0, 100 - turnover*2)) + (max(0, 100 - incidents*10)) + (diversity)) / 3
    s_score = min(100, max(0, s_raw))

    g_raw = (board + ethics) / 2
    g_score = min(100, max(0, g_raw))

    final = (e_score + s_score + g_score) / 3
    return final, e_score, s_score, g_score

# --- AUTHENTICATION FLOW ---
credentials = get_credentials()
authenticator = stauth.Authenticate(credentials, 'green_cookie_elite', 'secure_key_elite', cookie_expiry_days=1)

if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None

# --- LOGIN SCREEN (GAME LOBBY STYLE) ---
if not st.session_state['authentication_status']:
    # Centered Logo
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("""
            <div style='text-align: center; background: rgba(0,0,0,0.5); padding: 30px; border-radius: 20px; border: 2px solid #FFD700;'>
                <h1 style='font-size: 60px; margin:0;'>🔥</h1>
                <h1 style='color: #FFD700; margin-top:-10px; font-weight: 900; letter-spacing: 2px;'>GREEN ELITE</h1>
                <p style='color: #00ffcc; font-size: 16px; font-weight: bold;'>PRESS START TO LOGIN</p>
            </div>
        """, unsafe_allow_html=True)

    authenticator.login(location='main')

    if st.session_state['authentication_status'] is False:
        st.error('❌ ACCESS DENIED')
    elif st.session_state['authentication_status'] is None:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("➕ CREATE NEW PLAYER PROFILE"):
            with st.form("reg_form"):
                new_name = st.text_input("Codename (Name)")
                new_user = st.text_input("UserID (Username)")
                new_pass = st.text_input("Passcode (Password)", type="password")
                if st.form_submit_button("REGISTER"):
                    if len(new_pass) > 3:
                        if register_user(new_user, new_name, new_pass):
                            st.success("PROFILE CREATED! LOGIN ABOVE.")
                        else:
                            st.error("USER ID TAKEN.")
                    else:
                        st.warning("PASSCODE TOO SHORT.")

# --- DASHBOARD (LOGGED IN) ---
if st.session_state['authentication_status']:
    st.session_state.initial_sidebar_state = "expanded"
    username = st.session_state["username"]
    name = st.session_state["name"]
    authenticator.logout('LOGOUT', 'sidebar')

    # HERO BANNER
    st.markdown(f"""
        <div style="background: linear-gradient(90deg, #FF8C00, #FFD700); padding: 20px; border-radius: 10px; text-align: center; color: black; box-shadow: 0 0 20px rgba(255, 215, 0, 0.5);">
            <h1 style="color: black !important; margin:0; text-shadow: none;">WELCOME, COMMANDER {name.upper()}</h1>
            <h3 style="color: black !important; margin:0; font-weight: 300; text-shadow: none;">MISSION: SUSTAINABILITY OPTIMIZATION</h3>
        </div>
        <br>
    """, unsafe_allow_html=True)

    # SIDEBAR
    st.sidebar.header("🛠️ MISSION PARAMETERS")
    input_method = st.sidebar.radio("SOURCE:", ["MANUAL ENTRY", "UPLOAD DATA"])
    
    inputs = {}
    calc_triggered = False

    if input_method == "MANUAL ENTRY":
        with st.sidebar.form("manual_form"):
            st.markdown("### 1. ENV STATS")
            e1 = st.number_input("Energy", 50000)
            e2 = st.number_input("Water", 2000)
            e3 = st.slider("Recycling %", 0, 100, 40)
            e4 = st.slider("Renewable %", 0, 100, 20)
            st.divider()
            st.markdown("### 2. SOCIAL STATS")
            s1 = st.slider("Turnover %", 0, 100, 15)
            s2 = st.number_input("Incidents", 0)
            s3 = st.slider("Diversity %", 0, 100, 30)
            st.divider()
            st.markdown("### 3. GOV STATS")
            g1 = st.slider("Board Indep %", 0, 100, 60)
            g2 = st.slider("Ethics %", 0, 100, 95)
            
            if st.form_submit_button("🔥 CALCULATE RANK", type="primary"):
                inputs = {'energy':e1, 'water':e2, 'recycling':e3, 'renewable':e4, 'turnover':s1, 'incidents':s2, 'diversity':s3, 'board':g1, 'ethics':g2}
                calc_triggered = True
    else:
        template = pd.DataFrame({'energy': [50000], 'water': [2000], 'recycling': [40], 'renewable': [20], 'turnover': [15], 'incidents': [0], 'diversity': [30], 'board': [60], 'ethics': [95]})
        st.sidebar.download_button("DOWNLOAD BLUEPRINT", template.to_csv(index=False), "esg_template.csv")
        uploaded_file = st.sidebar.file_uploader("UPLOAD DATA", type=['csv'])
        if uploaded_file and st.sidebar.button("PROCESS DATA"):
            try:
                df = pd.read_csv(uploaded_file)
                if 'metric' in df.columns and 'value' in df.columns:
                    key_map = {'energy_consumption_kwh': 'energy', 'water_usage_m3': 'water', 'recycling_rate_pct': 'recycling', 'employee_turnover_pct': 'turnover', 'safety_incidents_count': 'incidents', 'management_diversity_pct': 'diversity', 'board_independence_pct': 'board', 'ethics_training_pct': 'ethics'}
                    parsed_inputs = {}
                    for _, row in df.iterrows():
                        metric = str(row['metric']).strip()
                        if metric in key_map: parsed_inputs[key_map[metric]] = row['value']
                    if parsed_inputs:
                        inputs = parsed_inputs
                        calc_triggered = True
                        st.sidebar.success("DATA LOADED!")
                else:
                    df.columns = df.columns.str.lower().str.strip()
                    inputs = df.iloc[0].to_dict()
                    calc_triggered = True
            except Exception as e:
                st.error(f"Error: {e}")

    # RESULTS DASHBOARD
    if calc_triggered:
        final, e, s, g = calculate_scores(inputs)
        save_data(username, final, e, s, g, inputs)

        if pdf_available:
            col_pdf_dl, _ = st.columns([1, 4])
            with col_pdf_dl:
                pdf_bytes = create_pdf(name, final, e, s, g, inputs)
                st.download_button("📄 EXPORT MISSION REPORT", pdf_bytes, "Mission_Report.pdf", "application/pdf")

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 RANKING", "🎯 OBJECTIVES", "💰 REWARDS", "🕰️ HISTORY", "🧪 SIMULATOR"])

        with tab1:
            st.subheader("CURRENT STATUS")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("TOTAL RANK", f"{final:.1f}", delta="MAX: 100")
            c2.metric("ENV", f"{e:.1f}")
            c3.metric("SOC", f"{s:.1f}")
            c4.metric("GOV", f"{g:.1f}")
            
            st.divider()
            
            col_left, col_right = st.columns(2)
            with col_left:
                st.markdown("### 🌍 EMISSION RADAR")
                co2_data = pd.DataFrame({'Source': ['Energy', 'Water'], 'Emissions': [inputs.get('energy',0)*0.4, inputs.get('water',0)*0.1]})
                fig_pie = px.pie(co2_data, values='Emissions', names='Source', color_discrete_sequence=['#FFD700', '#FF8C00'], hole=0.6)
                fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col_right:
                st.markdown("### ⚖️ PERFORMANCE WEB")
                df_radar = pd.DataFrame(dict(r=[e, s, g, e], theta=['ENV', 'SOC', 'GOV', 'ENV']))
                fig_radar = px.line_polar(df_radar, r='r', theta='theta', line_close=True)
                fig_radar.update_traces(fill='toself', line_color='#00ff00')
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], color='white')), paper_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_radar, use_container_width=True)

        with tab2:
            st.subheader("MISSION OBJECTIVES")
            c_rec1, c_rec2 = st.columns(2)
            with c_rec1:
                st.markdown("#### ⚠️ CRITICAL TARGETS")
                if e < 70: 
                    st.error("LOW ENV SCORE DETECTED")
                    st.write("• OBJECTIVE: Upgrade to LED Lights")
                if s < 70:
                    st.warning("LOW SOC SCORE DETECTED")
                    st.write("• OBJECTIVE: Reduce Accidents")
            with c_rec2:
                st.markdown("#### ✅ COMPLETED")
                if g > 70:
                    st.success("GOVERNANCE OPTIMIZED")

        with tab3:
            st.subheader("UNLOCKABLE REWARDS")
            col_fund1, col_fund2 = st.columns(2)
            with col_fund1:
                with st.expander("🏦 BANK LOAN BUFF", expanded=(final>60)):
                    if final > 60: st.success("✅ UNLOCKED: 0.5% RATE DROP")
                    else: st.error("🔒 LOCKED (REQ: LVL 60)")
            with col_fund2:
                with st.expander("🌱 GRANT DROP", expanded=(e>75)):
                    if e > 75: st.success("✅ UNLOCKED: $50K SUPPLY DROP")
                    else: st.error("🔒 LOCKED (REQ: ENV LVL 75)")

        with tab4:
            st.subheader("RANK HISTORY")
            hist = get_history(username)
            if not hist.empty:
                fig_hist = px.area(hist, x='Date', y='Overall', title="RANK PROGRESSION", color_discrete_sequence=['#FFD700'])
                fig_hist.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.write("NO BATTLE HISTORY FOUND.")

        with tab5:
            st.subheader("TACTICAL SIMULATION")
            col_sim1, col_sim2 = st.columns(2)
            with col_sim1:
                sim_energy = st.slider("Adjust Energy", 0, 100000, int(inputs.get('energy', 50000)))
                sim_turnover = st.slider("Adjust Turnover", 0, 100, int(inputs.get('turnover', 15)))
            
            with col_sim2:
                sim_e_raw = ((max(0, 100 - sim_energy/1000)) + (max(0, 100 - inputs.get('water',0)/500)) + inputs.get('recycling',0)) / 4
                sim_e_score = min(100, max(0, sim_e_raw))
                sim_s_raw = ((max(0, 100 - sim_turnover*2)) + (max(0, 100 - inputs.get('incidents',0)*10)) + inputs.get('diversity',0)) / 3
                sim_s_score = min(100, max(0, sim_s_raw))
                
                sim_final = (sim_e_score + sim_s_score + g) / 3
                
                st.metric("PROJECTED RANK", f"{sim_final:.1f}", delta=f"{sim_final - final:.1f}")

    else:
        st.info("👈 INITIATE SEQUENCE VIA SIDEBAR.")
