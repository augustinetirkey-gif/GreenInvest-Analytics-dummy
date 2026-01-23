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
    page_title="GreenInvest Pro",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- VISUAL OVERHAUL: CSS STYLING ---
st.markdown("""
    <style>
        /* 1. ANIMATED FOREST BACKGROUND */
        .stApp {
            background: linear-gradient(-45deg, #0f2027, #203a43, #2c5364, #1b5e20);
            background-size: 400% 400%;
            animation: gradient 15s ease infinite;
            font-family: 'Helvetica Neue', sans-serif;
        }
        @keyframes gradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        /* 2. LOGIN CARD */
        [data-testid="stForm"] {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(15px);
            border-radius: 25px;
            padding: 40px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.5);
            border: 1px solid rgba(255, 255, 255, 0.2);
            max-width: 450px;
            margin: auto;
        }

        /* 3. HEADERS & TABS */
        h1, h2, h3 { color: #ffffff !important; text-shadow: 0px 2px 4px rgba(0,0,0,0.4); }
        .stTabs [data-baseweb="tab-list"] { gap: 20px; background-color: rgba(255,255,255,0.1); padding: 10px 20px; border-radius: 50px; }
        .stTabs [data-baseweb="tab"] { height: 50px; color: white; font-weight: 600; }
        .stTabs [aria-selected="true"] { background-color: #4caf50 !important; color: white !important; border-radius: 30px; }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
DB_FILE = 'esg_visual_final.db'

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
        pdf.cell(200, 10, txt=f"Prepared for: {name}", ln=True, align='L')
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

# --- VISUALIZATION HELPERS ---
def make_gauge(val, title, color):
    return go.Figure(go.Indicator(
        mode="gauge+number", value=val, title={'text': title},
        gauge={'axis': {'range': [None, 100]}, 'bar': {'color': color}, 'steps': [{'range': [0,50], 'color': 'white'}, {'range': [50,100], 'color': '#f1f8e9'}]}
    )).update_layout(height=250, margin=dict(l=10,r=10,t=40,b=10), paper_bgcolor='rgba(0,0,0,0)')

# --- AUTHENTICATION FLOW (FIXED) ---
credentials = get_credentials()
authenticator = stauth.Authenticate(credentials, 'green_cookie_final', 'secure_key_final', cookie_expiry_days=1)

# Initialize Session State
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None

# --- LOGIN SCREEN ---
if not st.session_state['authentication_status']:
    # Visual Header
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("""
            <div style='text-align: center; padding-bottom: 20px;'>
                <h1 style='font-size: 80px; margin-bottom:0;'>🌿</h1>
                <h1 style='font-size: 50px; margin-top:0;'>GreenInvest</h1>
                <p style='color: #e0e0e0; font-size: 18px;'>Sustainable Intelligence Dashboard</p>
            </div>
        """, unsafe_allow_html=True)
    
    # 1. CALL LOGIN (WITHOUT UNPACKING)
    authenticator.login(location='main')

    # 2. CHECK STATUS MANUALLY
    if st.session_state['authentication_status'] is False:
        st.error('❌ Access Denied: Incorrect Username/Password')
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
    
    # 3. GET USER DATA FROM SESSION STATE
    username = st.session_state["username"]
    name = st.session_state["name"]
    
    authenticator.logout('Logout', 'sidebar')

    # Hero Banner
    st.markdown(f"""
        <div style="background: rgba(255,255,255,0.1); border-radius: 20px; padding: 2rem; text-align: center; border: 1px solid rgba(255,255,255,0.2);">
            <h1 style="margin:0;">GreenInvest Analytics</h1>
            <h3 style="margin:0; font-weight: 300;">Welcome, {name}. Let's measure your impact.</h3>
        </div>
        <br>
    """, unsafe_allow_html=True)

    # Sidebar
    st.sidebar.header("🛠️ Input Control")
    input_method = st.sidebar.radio("Data Source:", ["Manual Entry", "Upload CSV"])
    
    inputs = {}
    calc_triggered = False

    if input_method == "Manual Entry":
        with st.sidebar.form("manual_form"):
            with st.expander("🌳 Environmental", expanded=True):
                e1 = st.number_input("Energy (kWh)", 50000)
                e2 = st.number_input("Water (m3)", 2000)
                e3 = st.slider("Recycling Rate (%)", 0, 100, 40)
                e4 = st.slider("Renewable Energy (%)", 0, 100, 20)
            with st.expander("🤝 Social"):
                s1 = st.slider("Turnover Rate (%)", 0, 100, 15)
                s2 = st.number_input("Safety Incidents", 0)
                s3 = st.slider("Diversity (%)", 0, 100, 30)
            with st.expander("⚖️ Governance"):
                g1 = st.slider("Board Independence (%)", 0, 100, 60)
                g2 = st.slider("Ethics Compliance (%)", 0, 100, 95)
            if st.form_submit_button("🚀 Calculate Analysis"):
                inputs = {'energy':e1, 'water':e2, 'recycling':e3, 'renewable':e4, 'turnover':s1, 'incidents':s2, 'diversity':s3, 'board':g1, 'ethics':g2}
                calc_triggered = True
    else:
        template = pd.DataFrame({'energy': [50000], 'water': [2000], 'recycling': [40], 'renewable': [20], 'turnover': [15], 'incidents': [0], 'diversity': [30], 'board': [60], 'ethics': [95]})
        st.sidebar.download_button("Download Template", template.to_csv(index=False), "esg_template.csv")
        uploaded_file = st.sidebar.file_uploader("Upload CSV", type=['csv'])
        if uploaded_file and st.sidebar.button("Process Data"):
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
                        st.sidebar.success("✅ Stacked CSV Processed!")
                else:
                    df.columns = df.columns.str.lower().str.strip()
                    inputs = df.iloc[0].to_dict()
                    calc_triggered = True
            except Exception as e:
                st.error(f"Error: {e}")

    # Dashboard Logic
    if calc_triggered:
        final, e, s, g = calculate_scores(inputs)
        save_data(username, final, e, s, g, inputs)

        # PDF Button
        if pdf_available:
            col_pdf_dl, _ = st.columns([1, 4])
            with col_pdf_dl:
                pdf_bytes = create_pdf(name, final, e, s, g, inputs)
                st.download_button("📄 Download PDF Report", pdf_bytes, "ESG_Report.pdf", "application/pdf")

        # Tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Scorecard", "🎯 Action Plan", "💰 Funding", "🕰️ Trends", "🧪 Simulator"])

        with tab1:
            st.subheader("Performance Overview")
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.plotly_chart(make_gauge(final, "Overall ESG", "#1b5e20"), use_container_width=True)
            with c2: st.plotly_chart(make_gauge(e, "Environmental", "#43a047"), use_container_width=True)
            with c3: st.plotly_chart(make_gauge(s, "Social", "#1976d2"), use_container_width=True)
            with c4: st.plotly_chart(make_gauge(g, "Governance", "#fbc02d"), use_container_width=True)

            st.divider()
            col_left, col_right = st.columns(2)
            with col_left:
                st.markdown("### 🌍 Carbon Footprint")
                co2_data = pd.DataFrame({'Source': ['Energy', 'Water'], 'Emissions': [inputs.get('energy',0)*0.4, inputs.get('water',0)*0.1]})
                fig_pie = px.pie(co2_data, values='Emissions', names='Source', color_discrete_sequence=['#ff7043', '#42a5f5'], hole=0.5)
                fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_pie, use_container_width=True)
            with col_right:
                st.markdown("### ⚖️ Balance Radar")
                df_radar = pd.DataFrame(dict(r=[e, s, g, e], theta=['Env', 'Soc', 'Gov', 'Env']))
                fig_radar = px.line_polar(df_radar, r='r', theta='theta', line_close=True)
                fig_radar.update_traces(fill='toself', line_color='#00e676')
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), paper_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_radar, use_container_width=True)

        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                st.info("🚨 Critical Priorities")
                if e < 70: st.markdown("* **Energy:** Switch to LED lighting.")
                if s < 70: st.markdown("* **Social:** Implement safety training.")
            with col2:
                st.success("✅ Strengths")
                if g > 70: st.markdown("* **Governance:** Strong ethics policy.")

        with tab3:
            st.subheader("Marketplace Opportunities")
            with st.expander("🏦 Green Loan Program", expanded=(final>60)):
                if final > 60: st.success("✅ Qualified for 0.5% rate discount.")
                else: st.error("❌ Score > 60 required.")

        with tab4:
            st.subheader("Historical Trends")
            hist = get_history(username)
            if not hist.empty:
                fig_hist = px.area(hist, x='Date', y='Overall', title="Score History", color_discrete_sequence=['#00e676'])
                fig_hist.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_hist, use_container_width=True)
            else: st.write("No history yet.")

        with tab5:
            st.subheader("Scenario Simulator")
            sim_energy = st.slider("Simulate Energy Usage", 0, 100000, int(inputs.get('energy', 50000)))
            sim_e_raw = ((max(0, 100 - sim_energy/1000)) + (max(0, 100 - inputs.get('water',0)/500)) + inputs.get('recycling',0)) / 4
            sim_final = (min(100, max(0, sim_e_raw)) + s + g) / 3
            st.metric("Projected Score", f"{sim_final:.1f}", delta=f"{sim_final - final:.1f}")

    else:
        st.info("👈 Please enter data to generate your dashboard.")
