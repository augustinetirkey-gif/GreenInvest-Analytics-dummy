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

# --- CLEAN & PROFESSIONAL STYLING (Light Mode Focus) ---
st.markdown("""
    <style>
        /* 1. BACKGROUND: Clean White/Grey */
        .stApp {
            background-color: #f8f9fa;
            color: #333333;
        }

        /* 2. HEADERS: Dark Green for Professionalism */
        h1, h2, h3 {
            color: #1b5e20 !important;
            font-family: 'Arial', sans-serif;
            font-weight: 700;
        }
        
        /* 3. TEXT: Dark Grey (Easy to read) */
        p, li, label, .stMarkdown {
            color: #424242 !important;
            font-size: 16px;
        }

        /* 4. CARDS: White boxes with soft shadow */
        div[data-testid="metric-container"], [data-testid="stForm"], .css-1r6slb0 {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }

        /* 5. METRICS: Big Green Numbers */
        [data-testid="stMetricValue"] {
            font-size: 2.5rem !important;
            color: #2e7d32 !important; /* Forest Green */
            font-weight: bold;
        }
        [data-testid="stMetricLabel"] {
            color: #616161 !important;
            font-size: 1rem;
        }

        /* 6. BUTTONS: Clear and Visible */
        /* Primary (Calculate) */
        button[kind="primary"] {
            background-color: #2e7d32 !important;
            color: white !important;
            border-radius: 8px;
            padding: 10px 20px;
            border: none;
            transition: 0.3s;
        }
        button[kind="primary"]:hover {
            background-color: #1b5e20 !important;
        }
        
        /* Secondary (Logout) */
        button[kind="secondary"] {
            background-color: #ffffff !important;
            color: #d32f2f !important; /* Red text for logout */
            border: 1px solid #d32f2f !important;
        }

        /* 7. TABS: Clean Navigation */
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px;
            border-bottom: 2px solid #e0e0e0;
        }
        .stTabs [aria-selected="true"] {
            background-color: #e8f5e9 !important;
            color: #1b5e20 !important;
            border-bottom: 3px solid #1b5e20;
        }
        
        /* 8. HERO SECTION BOX */
        .hero-box {
            background: white;
            padding: 30px;
            border-radius: 15px;
            border-left: 10px solid #2e7d32;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
DB_FILE = 'esg_clean.db'

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
        pdf.cell(200, 10, txt="Score Summary", ln=True, align='L')
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Total Score: {overall:.1f} / 100", ln=True)
        pdf.cell(200, 10, txt=f"Env Score: {e:.1f}", ln=True)
        pdf.cell(200, 10, txt=f"Soc Score: {s:.1f}", ln=True)
        pdf.cell(200, 10, txt=f"Gov Score: {g:.1f}", ln=True)
        pdf.ln(10)
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
authenticator = stauth.Authenticate(credentials, 'green_cookie_clean', 'secure_key_clean', cookie_expiry_days=1)

if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None

# --- LOGIN SCREEN (Clean & Simple) ---
if not st.session_state['authentication_status']:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("""
            <div style='text-align: center; margin-bottom: 20px; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);'>
                <h1 style='color: #2e7d32; margin: 0;'>GreenInvest</h1>
                <p style='color: gray; margin-top: 5px;'>Please sign in to continue.</p>
            </div>
        """, unsafe_allow_html=True)

    authenticator.login(location='main')

    if st.session_state['authentication_status'] is False:
        st.error('❌ Username/Password is incorrect.')
    elif st.session_state['authentication_status'] is None:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("➕ Register New Account"):
            with st.form("reg_form"):
                new_name = st.text_input("Full Name")
                new_user = st.text_input("Username")
                new_pass = st.text_input("Password", type="password")
                if st.form_submit_button("Create Account", type="primary"):
                    if len(new_pass) > 3:
                        if register_user(new_user, new_name, new_pass):
                            st.success("Success! You can now log in.")
                        else:
                            st.error("Username already taken.")
                    else:
                        st.warning("Password too short.")

# --- DASHBOARD (LOGGED IN) ---
if st.session_state['authentication_status']:
    st.session_state.initial_sidebar_state = "expanded"
    username = st.session_state["username"]
    name = st.session_state["name"]
    
    # VISIBLE LOGOUT BUTTON IN SIDEBAR
    st.sidebar.markdown("### User Settings")
    authenticator.logout('Sign Out', 'sidebar')

    # HERO BANNER (Clean Box)
    st.markdown(f"""
        <div class="hero-box">
            <h1 style="margin:0; color: #1b5e20;">Hello, {name}</h1>
            <p style="margin:0; color: #616161;">Here is your sustainability summary.</p>
        </div>
    """, unsafe_allow_html=True)

    # SIDEBAR INPUTS
    st.sidebar.header("📝 Enter Data")
    input_method = st.sidebar.radio("How to add data?", ["Manual Entry", "Upload CSV File"])
    
    inputs = {}
    calc_triggered = False

    if input_method == "Manual Entry":
        with st.sidebar.form("manual_form"):
            st.markdown("### 1. Environment")
            e1 = st.number_input("Energy Used (kWh)", 50000)
            e2 = st.number_input("Water Used (m3)", 2000)
            e3 = st.slider("Recycling (%)", 0, 100, 40)
            e4 = st.slider("Renewable Energy (%)", 0, 100, 20)
            st.divider()
            st.markdown("### 2. People (Social)")
            s1 = st.slider("Employee Turnover (%)", 0, 100, 15)
            s2 = st.number_input("Safety Incidents", 0)
            s3 = st.slider("Diversity (%)", 0, 100, 30)
            st.divider()
            st.markdown("### 3. Management (Gov)")
            g1 = st.slider("Board Independence (%)", 0, 100, 60)
            g2 = st.slider("Ethics Compliance (%)", 0, 100, 95)
            
            # Green Primary Button
            if st.form_submit_button("Calculate My Score", type="primary"):
                inputs = {'energy':e1, 'water':e2, 'recycling':e3, 'renewable':e4, 'turnover':s1, 'incidents':s2, 'diversity':s3, 'board':g1, 'ethics':g2}
                calc_triggered = True
    else:
        template = pd.DataFrame({'energy': [50000], 'water': [2000], 'recycling': [40], 'renewable': [20], 'turnover': [15], 'incidents': [0], 'diversity': [30], 'board': [60], 'ethics': [95]})
        st.sidebar.download_button("Download Blank Template", template.to_csv(index=False), "esg_template.csv")
        uploaded_file = st.sidebar.file_uploader("Upload CSV File", type=['csv'])
        if uploaded_file and st.sidebar.button("Process My File", type="primary"):
            try:
                df = pd.read_csv(uploaded_file)
                # Simple Logic for CSV
                if 'metric' in df.columns and 'value' in df.columns:
                    key_map = {'energy_consumption_kwh': 'energy', 'water_usage_m3': 'water', 'recycling_rate_pct': 'recycling', 'employee_turnover_pct': 'turnover', 'safety_incidents_count': 'incidents', 'management_diversity_pct': 'diversity', 'board_independence_pct': 'board', 'ethics_training_pct': 'ethics'}
                    parsed_inputs = {}
                    for _, row in df.iterrows():
                        metric = str(row['metric']).strip()
                        if metric in key_map: parsed_inputs[key_map[metric]] = row['value']
                    if parsed_inputs:
                        inputs = parsed_inputs
                        calc_triggered = True
                        st.sidebar.success("File Read Successfully!")
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

        # --- SIMPLE TABS ---
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 My Score", "🚀 How to Improve", "📈 History", "🔍 View Data", "🔮 Simulator"])

        # TAB 1: SCORE
        with tab1:
            st.subheader("Scorecard")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Score", f"{final:.1f}", delta="Goal: 100")
            c2.metric("Environment", f"{e:.1f}", help="Energy, Water, Waste")
            c3.metric("Social", f"{s:.1f}", help="People & Safety")
            c4.metric("Governance", f"{g:.1f}", help="Rules & Ethics")
            
            st.divider()
            
            col_left, col_right = st.columns(2)
            with col_left:
                st.markdown("### 🌍 Pollution Sources")
                st.caption("Energy vs Water usage")
                co2_data = pd.DataFrame({'Source': ['Energy', 'Water'], 'Emissions': [inputs.get('energy',0)*0.4, inputs.get('water',0)*0.1]})
                fig_pie = px.pie(co2_data, values='Emissions', names='Source', color_discrete_sequence=['#66bb6a', '#42a5f5'], hole=0.5)
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col_right:
                st.markdown("### ⚖️ Balance Chart")
                st.caption("Are you balanced across all areas?")
                df_radar = pd.DataFrame(dict(r=[e, s, g, e], theta=['Environment', 'Social', 'Governance', 'Environment']))
                fig_radar = px.line_polar(df_radar, r='r', theta='theta', line_close=True)
                fig_radar.update_traces(fill='toself', line_color='#66bb6a')
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
                st.plotly_chart(fig_radar, use_container_width=True)

        # TAB 2: IMPROVEMENTS
        with tab2:
            st.subheader("Simple Steps to Improve")
            
            col_act, col_fund = st.columns(2)
            
            with col_act:
                st.markdown("#### 🛠️ Things to Fix")
                if e < 70: 
                    st.error("Environment score is low")
                    st.write("• Switch to LED lights.")
                    st.write("• Recycle more waste.")
                elif s < 70:
                    st.warning("Social score is low")
                    st.write("• Improve safety training.")
                else:
                    st.success("You are doing great!")
                    st.write("Keep maintaining your current standards.")

            with col_fund:
                st.markdown("#### 💰 Money You Can Claim")
                with st.expander("🏦 Bank Loan Discount (0.5%)"):
                    if final > 60: 
                        st.success("✅ ELIGIBLE (Score > 60)")
                    else: 
                        st.error("❌ NOT ELIGIBLE yet")
                
                with st.expander("🌱 Government Grant ($50k)"):
                    if e > 75: 
                        st.success("✅ ELIGIBLE (Env Score > 75)")
                    else: 
                        st.error("❌ NOT ELIGIBLE yet")

        # TAB 3: HISTORY
        with tab3:
            st.subheader("Your Progress")
            hist = get_history(username)
            if not hist.empty:
                fig_hist = px.area(hist, x='Date', y='Overall', title="Score Trend", color_discrete_sequence=['#2e7d32'])
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.info("No history yet. Save your first score!")

        # TAB 4: RAW DATA
        with tab4:
            st.subheader("Your Input Data")
            df_display = pd.DataFrame(list(inputs.items()), columns=['Item', 'Value'])
            st.dataframe(df_display, use_container_width=True)

        # TAB 5: SIMULATOR
        with tab5:
            st.subheader("Test Changes")
            st.caption("Move sliders to see how your score changes.")
            
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
                
                st.metric("New Score", f"{sim_final:.1f}", delta=f"{sim_final - final:.1f}")

    else:
        st.info("👈 Please enter data in the sidebar to start.")
