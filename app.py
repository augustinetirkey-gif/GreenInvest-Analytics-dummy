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
    page_title="GreenInvest",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CYBER-PROFESSIONAL THEME ---
st.markdown("""
    <style>
        /* 1. BACKGROUND: Sleek Dark Gradient (Professional Dark Mode) */
        .stApp {
            background: linear-gradient(135deg, #0b0e11 0%, #151b26 100%);
            color: #e0e0e0;
        }

        /* 2. TEXT VISIBILITY - Force White/Light Gray */
        h1, h2, h3, h4, h5, h6 { color: #ffffff !important; font-family: 'Segoe UI', sans-serif; }
        p, label, .stTextInput > label, .stNumberInput > label, .stSlider > label {
            color: #b0b3b8 !important;
        }

        /* 3. CARDS (Metrics & Login) - Glassmorphism with Neon Border */
        div[data-testid="metric-container"], [data-testid="stForm"] {
            background: rgba(30, 35, 45, 0.8);
            border: 1px solid rgba(0, 255, 136, 0.2); /* Subtle Neon Green Border */
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            border-radius: 12px;
            padding: 20px;
        }

        /* 4. METRIC VALUES - Glowing Green Text */
        [data-testid="stMetricValue"] {
            font-size: 2.5rem !important;
            font-weight: 700;
            color: #00ff88 !important; /* Neon Green */
            text-shadow: 0 0 10px rgba(0, 255, 136, 0.3);
        }
        [data-testid="stMetricLabel"] {
            color: #ffffff !important;
            font-size: 1rem;
        }

        /* 5. INPUT FIELDS - Dark & Clean */
        .stTextInput input, .stNumberInput input {
            background-color: #0b0e11;
            color: white !important;
            border: 1px solid #333;
            border-radius: 8px;
        }

        /* 6. BUTTONS - Gradient Green */
        div.stButton > button {
            background: linear-gradient(90deg, #00C853, #64DD17);
            color: #000;
            font-weight: bold;
            border: none;
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            box-shadow: 0 0 15px rgba(0, 200, 83, 0.6);
            color: white;
        }

        /* 7. SIDEBAR - Dark Grey */
        section[data-testid="stSidebar"] {
            background-color: #0b0e11;
            border-right: 1px solid #333;
        }

        /* 8. TABS - Modern Pill Shape */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: rgba(255,255,255,0.05);
            padding: 10px;
            border-radius: 50px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #00ff88 !important;
            color: black !important;
            border-radius: 30px;
        }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
DB_FILE = 'esg_cyber.db'

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
            self.cell(0, 10, 'GreenInvest ESG Report', 0, 1, 'C')
            self.ln(5)
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def create_pdf(name, overall, e, s, g, inputs):
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Prepared For: {name}", ln=True, align='L')
        pdf.cell(200, 10, txt=f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}", ln=True, align='L')
        pdf.ln(10)
        
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Executive Summary", ln=True, align='L')
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Overall ESG Score: {overall:.1f} / 100", ln=True)
        pdf.cell(200, 10, txt=f"Environmental: {e:.1f}", ln=True)
        pdf.cell(200, 10, txt=f"Social: {s:.1f}", ln=True)
        pdf.cell(200, 10, txt=f"Governance: {g:.1f}", ln=True)
        pdf.ln(10)
        
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Input Data Breakdown", ln=True, align='L')
        pdf.set_font("Arial", size=10)
        for key, value in inputs.items():
            pdf.cell(200, 7, txt=f"{key.capitalize()}: {value}", ln=True)
        return pdf.output(dest='S').encode('latin-1')

# --- CALCULATION ENGINE ---
def calculate_scores(inputs):
    # Parsing with defaults
    energy = float(inputs.get('energy', 50000))
    water = float(inputs.get('water', 2000))
    recycling = float(inputs.get('recycling', 40))
    renewable = float(inputs.get('renewable', 0))
    turnover = float(inputs.get('turnover', 15))
    incidents = float(inputs.get('incidents', 0))
    diversity = float(inputs.get('diversity', 30))
    board = float(inputs.get('board', 60))
    ethics = float(inputs.get('ethics', 95))

    # Logic
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
authenticator = stauth.Authenticate(credentials, 'green_cookie_cyber', 'secure_key_cyber', cookie_expiry_days=1)

if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None

# --- LOGIN SCREEN ---
if not st.session_state['authentication_status']:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("""
            <div style='text-align: center; margin-bottom: 30px;'>
                <h1 style='font-size: 80px; margin-bottom:0;'>🌿</h1>
                <h1 style='margin-top:-10px; letter-spacing: 2px;'>GreenInvest</h1>
                <p style='color: #00ff88; font-size: 16px;'>Secure Sustainability Login</p>
            </div>
        """, unsafe_allow_html=True)

    authenticator.login(location='main')

    if st.session_state['authentication_status'] is False:
        st.error('❌ Login Failed: Incorrect Credentials')
    elif st.session_state['authentication_status'] is None:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📝 Register New Account"):
            with st.form("reg_form"):
                new_name = st.text_input("Full Name")
                new_user = st.text_input("Username")
                new_pass = st.text_input("Password", type="password")
                if st.form_submit_button("Create Account"):
                    if len(new_pass) > 3:
                        if register_user(new_user, new_name, new_pass):
                            st.success("Account created! Log in above.")
                        else:
                            st.error("Username already exists.")
                    else:
                        st.warning("Password must be at least 4 characters.")

# --- DASHBOARD (LOGGED IN) ---
if st.session_state['authentication_status']:
    st.session_state.initial_sidebar_state = "expanded"
    username = st.session_state["username"]
    name = st.session_state["name"]
    authenticator.logout('Logout', 'sidebar')

    # HERO BANNER
    st.markdown(f"""
        <div style="background: linear-gradient(90deg, #1b5e20, #2e7d32); padding: 25px; border-radius: 15px; border: 1px solid #43a047; box-shadow: 0 0 20px rgba(0,255,136,0.2);">
            <h1 style="margin:0;">GreenInvest Analytics</h1>
            <h3 style="margin:0; font-weight: 300; opacity: 0.9;">Welcome back, {name}.</h3>
        </div>
        <br>
    """, unsafe_allow_html=True)

    # SIDEBAR
    st.sidebar.header("🛠️ Data Controls")
    input_method = st.sidebar.radio("Input Source:", ["Manual Entry", "Upload CSV"])
    
    inputs = {}
    calc_triggered = False

    if input_method == "Manual Entry":
        with st.sidebar.form("manual_form"):
            st.markdown("### 1. Environmental")
            e1 = st.number_input("Energy (kWh)", 50000)
            e2 = st.number_input("Water (m3)", 2000)
            e3 = st.slider("Recycling Rate (%)", 0, 100, 40)
            e4 = st.slider("Renewable Energy (%)", 0, 100, 20)
            st.divider()
            st.markdown("### 2. Social")
            s1 = st.slider("Turnover Rate (%)", 0, 100, 15)
            s2 = st.number_input("Safety Incidents", 0)
            s3 = st.slider("Diversity (%)", 0, 100, 30)
            st.divider()
            st.markdown("### 3. Governance")
            g1 = st.slider("Board Independence (%)", 0, 100, 60)
            g2 = st.slider("Ethics Compliance (%)", 0, 100, 95)
            
            if st.form_submit_button("🚀 Calculate Score", type="primary"):
                inputs = {'energy':e1, 'water':e2, 'recycling':e3, 'renewable':e4, 'turnover':s1, 'incidents':s2, 'diversity':s3, 'board':g1, 'ethics':g2}
                calc_triggered = True
    else:
        template = pd.DataFrame({'energy': [50000], 'water': [2000], 'recycling': [40], 'renewable': [20], 'turnover': [15], 'incidents': [0], 'diversity': [30], 'board': [60], 'ethics': [95]})
        st.sidebar.download_button("Download Template CSV", template.to_csv(index=False), "esg_template.csv")
        uploaded_file = st.sidebar.file_uploader("Upload CSV", type=['csv'])
        if uploaded_file and st.sidebar.button("Process Data", type="primary"):
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
                        st.sidebar.success("CSV Loaded Successfully")
                else:
                    df.columns = df.columns.str.lower().str.strip()
                    inputs = df.iloc[0].to_dict()
                    calc_triggered = True
            except Exception as e:
                st.error(f"Error: {e}")

    # DASHBOARD
    if calc_triggered:
        final, e, s, g = calculate_scores(inputs)
        save_data(username, final, e, s, g, inputs)

        if pdf_available:
            col_pdf_dl, _ = st.columns([1, 4])
            with col_pdf_dl:
                pdf_bytes = create_pdf(name, final, e, s, g, inputs)
                st.download_button("📄 Download Report (PDF)", pdf_bytes, "ESG_Report.pdf", "application/pdf")

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Scorecard", "🎯 Recommendations", "💰 Funding", "🕰️ Trends", "🧪 Simulator"])

        with tab1:
            st.subheader("Performance Overview")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Overall Score", f"{final:.1f}", delta="Target: 100")
            c2.metric("Environmental", f"{e:.1f}")
            c3.metric("Social", f"{s:.1f}")
            c4.metric("Governance", f"{g:.1f}")
            
            st.divider()
            
            col_left, col_right = st.columns(2)
            with col_left:
                st.markdown("### 🌍 Carbon Emission Analysis")
                co2_data = pd.DataFrame({'Source': ['Energy', 'Water'], 'Emissions': [inputs.get('energy',0)*0.4, inputs.get('water',0)*0.1]})
                fig_pie = px.pie(co2_data, values='Emissions', names='Source', color_discrete_sequence=['#00e676', '#2979ff'], hole=0.6)
                fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col_right:
                st.markdown("### ⚖️ Metric Radar")
                df_radar = pd.DataFrame(dict(r=[e, s, g, e], theta=['Environmental', 'Social', 'Governance', 'Environmental']))
                fig_radar = px.line_polar(df_radar, r='r', theta='theta', line_close=True)
                fig_radar.update_traces(fill='toself', line_color='#00e676')
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], color='white')), paper_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_radar, use_container_width=True)

        with tab2:
            st.subheader("Action Plan")
            c_rec1, c_rec2 = st.columns(2)
            with c_rec1:
                st.markdown("#### ⚠️ Areas for Improvement")
                if e < 70: 
                    st.error("Low Environmental Score")
                    st.write("• Action: Upgrade lighting systems to LED")
                if s < 70:
                    st.warning("Low Social Score")
                    st.write("• Action: Implement safety training program")
            with c_rec2:
                st.markdown("#### ✅ Current Strengths")
                if g > 70:
                    st.success("Strong Governance")
                    st.write("• Compliance protocols are effective")

        with tab3:
            st.subheader("Available Funding")
            col_fund1, col_fund2 = st.columns(2)
            with col_fund1:
                with st.expander("🏦 Green Loan Program", expanded=(final>60)):
                    if final > 60: st.success("✅ Unlocked: 0.5% Rate Discount")
                    else: st.error("🔒 Locked (Requires Score > 60)")
            with col_fund2:
                with st.expander("🌱 Sustainability Grant", expanded=(e>75)):
                    if e > 75: st.success("✅ Unlocked: $50,000 Grant")
                    else: st.error("🔒 Locked (Requires Env > 75)")

        with tab4:
            st.subheader("Historical Performance")
            hist = get_history(username)
            if not hist.empty:
                fig_hist = px.area(hist, x='Date', y='Overall', title="Score History", color_discrete_sequence=['#00e676'])
                fig_hist.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.write("No history available.")

        with tab5:
            st.subheader("Score Simulator")
            col_sim1, col_sim2 = st.columns(2)
            with col_sim1:
                sim_energy = st.slider("Adjust Energy Input", 0, 100000, int(inputs.get('energy', 50000)))
                sim_turnover = st.slider("Adjust Turnover Rate", 0, 100, int(inputs.get('turnover', 15)))
            
            with col_sim2:
                sim_e_raw = ((max(0, 100 - sim_energy/1000)) + (max(0, 100 - inputs.get('water',0)/500)) + inputs.get('recycling',0)) / 4
                sim_e_score = min(100, max(0, sim_e_raw))
                sim_s_raw = ((max(0, 100 - sim_turnover*2)) + (max(0, 100 - inputs.get('incidents',0)*10)) + inputs.get('diversity',0)) / 3
                sim_s_score = min(100, max(0, sim_s_raw))
                
                sim_final = (sim_e_score + sim_s_score + g) / 3
                
                st.metric("Simulated Score", f"{sim_final:.1f}", delta=f"{sim_final - final:.1f}")

    else:
        st.info("👈 Please enter data in the sidebar to view your dashboard.")
