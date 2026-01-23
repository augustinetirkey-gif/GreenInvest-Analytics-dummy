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

# --- CYBER-PROFESSIONAL THEME (High Visibility Update) ---
st.markdown("""
    <style>
        /* 1. BACKGROUND: Professional Dark Mode */
        .stApp {
            background: linear-gradient(135deg, #0b0e11 0%, #151b26 100%);
            color: #e0e0e0;
        }

        /* 2. TEXT VISIBILITY */
        h1, h2, h3, h4 { color: #ffffff !important; font-family: 'Segoe UI', sans-serif; }
        p, label, .stMarkdown { color: #b0b3b8 !important; }

        /* 3. BUTTONS - HIGH CONTRAST FIX */
        /* Primary Buttons (Process Data, Calculate) - NEON GREEN with BLACK Text */
        button[kind="primary"] {
            background: #00E676 !important;
            color: #000000 !important;
            font-weight: 800 !important;
            border: none;
            box-shadow: 0 0 10px rgba(0, 230, 118, 0.4);
        }
        
        /* Secondary Buttons (Logout, Download) - WHITE/GREY High Contrast */
        button[kind="secondary"] {
            background: #ffffff !important;
            color: #000000 !important;
            border: 1px solid #ccc;
        }
        /* Specific Fix for Sidebar Logout if needed */
        [data-testid="stSidebar"] button {
             background-color: #ff5252 !important; /* Red for Logout */
             color: white !important;
        }

        /* 4. CARDS (Metrics & Login) */
        div[data-testid="metric-container"], [data-testid="stForm"] {
            background: rgba(30, 35, 45, 0.9);
            border: 1px solid rgba(0, 255, 136, 0.2);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            border-radius: 12px;
            padding: 20px;
        }

        /* 5. METRIC VALUES */
        [data-testid="stMetricValue"] {
            font-size: 2.2rem !important;
            font-weight: 700;
            color: #00ff88 !important;
        }
        
        /* 6. TABS */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: rgba(255,255,255,0.05);
            padding: 10px;
            border-radius: 10px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #00ff88 !important;
            color: black !important;
            border-radius: 5px;
        }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
DB_FILE = 'esg_cyber_v2.db'

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
authenticator = stauth.Authenticate(credentials, 'green_cookie_cyber_v2', 'secure_key_cyber_v2', cookie_expiry_days=1)

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
                if st.form_submit_button("Create Account", type="primary"):
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
    
    # Force high-contrast Logout Button in Sidebar
    st.sidebar.markdown("### User Controls")
    authenticator.logout('Sign Out / Logout', 'sidebar')

    # HERO BANNER
    st.markdown(f"""
        <div style="background: linear-gradient(90deg, #1b5e20, #2e7d32); padding: 25px; border-radius: 15px; border: 1px solid #43a047; box-shadow: 0 0 20px rgba(0,255,136,0.2);">
            <h1 style="margin:0;">GreenInvest Analytics</h1>
            <h3 style="margin:0; font-weight: 300; opacity: 0.9;">Welcome back, {name}.</h3>
        </div>
        <br>
    """, unsafe_allow_html=True)

    # SIDEBAR INPUTS
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

        # --- RENAMED AND REORGANIZED TABS ---
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Executive Summary", "🚀 Action Roadmap", "📈 Trends & History", "🔍 Deep Dive", "🔮 Impact Simulator"])

        # TAB 1: EXECUTIVE SUMMARY (Visuals)
        with tab1:
            st.subheader("High-Level Performance")
            st.caption("A quick snapshot of your current sustainability standing.")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Overall Score", f"{final:.1f}", delta="Target: 100", help="Weighted average of all 3 pillars.")
            c2.metric("Environmental", f"{e:.1f}", delta_color="normal", help="Measures resource efficiency.")
            c3.metric("Social", f"{s:.1f}", delta_color="normal", help="Measures workforce health.")
            c4.metric("Governance", f"{g:.1f}", delta_color="normal", help="Measures ethical leadership.")
            
            st.divider()
            
            col_left, col_right = st.columns(2)
            with col_left:
                st.markdown("### 🌍 Carbon Emission Analysis")
                st.caption("Visualizing the sources of your environmental footprint.")
                co2_data = pd.DataFrame({'Source': ['Energy', 'Water'], 'Emissions': [inputs.get('energy',0)*0.4, inputs.get('water',0)*0.1]})
                fig_pie = px.pie(co2_data, values='Emissions', names='Source', color_discrete_sequence=['#00e676', '#2979ff'], hole=0.6)
                fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col_right:
                st.markdown("### ⚖️ Metric Radar")
                st.caption("Identifying balanced growth across sectors.")
                df_radar = pd.DataFrame(dict(r=[e, s, g, e], theta=['Environmental', 'Social', 'Governance', 'Environmental']))
                fig_radar = px.line_polar(df_radar, r='r', theta='theta', line_close=True)
                fig_radar.update_traces(fill='toself', line_color='#00e676')
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], color='white')), paper_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_radar, use_container_width=True)

        # TAB 2: ACTION ROADMAP (Recommendations + Funding)
        with tab2:
            st.subheader("Strategic Next Steps")
            st.caption("Prioritized actions to improve your score and financial incentives you can claim now.")
            
            col_act, col_fund = st.columns(2)
            
            with col_act:
                st.markdown("#### 🛠️ Improvement Plan")
                if e < 70: 
                    st.error("Priority: Environmental Upgrade")
                    st.write("• **Issue:** High energy/water usage detected.")
                    st.write("• **Fix:** Upgrade to LED lighting (ROI: 12 months).")
                elif s < 70:
                    st.warning("Priority: Workforce Stability")
                    st.write("• **Issue:** Turnover or safety incidents are dragging score.")
                    st.write("• **Fix:** Implement quarterly safety audits.")
                else:
                    st.success("✅ Systems Optimal")
                    st.write("Continue monitoring current metrics.")

            with col_fund:
                st.markdown("#### 💰 Financial Incentives")
                with st.expander("🏦 Green Loan Program (0.5% Discount)", expanded=(final>60)):
                    if final > 60: 
                        st.success("✅ ELIGIBLE")
                        st.write("Your score > 60 qualifies you for reduced interest rates.")
                    else: 
                        st.error("❌ INELIGIBLE (Req: Score > 60)")
                
                with st.expander("🌱 EPA Sustainability Grant ($50k)", expanded=(e>75)):
                    if e > 75: 
                        st.success("✅ ELIGIBLE")
                        st.write("Your high Environmental score unlocks direct funding.")
                    else: 
                        st.error("❌ INELIGIBLE (Req: Env > 75)")

        # TAB 3: TRENDS
        with tab3:
            st.subheader("Performance History")
            st.caption("Tracking your progress over time.")
            hist = get_history(username)
            if not hist.empty:
                fig_hist = px.area(hist, x='Date', y='Overall', title="Score History", color_discrete_sequence=['#00e676'])
                fig_hist.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.info("No history available yet. Save more calculations to see trends.")

        # TAB 4: DEEP DIVE (Raw Data)
        with tab4:
            st.subheader("Input Data Verification")
            st.caption("Review the raw data used for this calculation.")
            df_display = pd.DataFrame(list(inputs.items()), columns=['Metric', 'Value'])
            st.dataframe(df_display, use_container_width=True)

        # TAB 5: SIMULATOR
        with tab5:
            st.subheader("What-If Simulator")
            st.caption("Adjust sliders to see how changes affect your score (Data is NOT saved).")
            
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
                
                st.metric("Projected New Score", f"{sim_final:.1f}", delta=f"{sim_final - final:.1f}")

    else:
        st.info("👈 Please enter data in the sidebar to view your dashboard.")
