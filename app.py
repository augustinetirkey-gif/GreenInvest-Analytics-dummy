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

# --- ATTRACTIVE & READABLE STYLING ---
st.markdown("""
    <style>
        /* 1. BACKGROUND: Clean Professional White */
        .stApp {
            background-color: #f8f9fa;
            color: #212121;
        }

        /* 2. HEADERS: Clear & Bold */
        h1, h2, h3 {
            color: #1b5e20 !important; /* Forest Green */
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-weight: 700;
        }
        
        /* 3. CARDS: Floating White Boxes */
        div[data-testid="metric-container"], [data-testid="stForm"], .css-1r6slb0 {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05); /* Soft Shadow */
        }

        /* 4. METRICS: Big & Easy to Read */
        [data-testid="stMetricValue"] {
            font-size: 3rem !important;
            color: #2e7d32 !important;
            font-weight: 800;
        }
        [data-testid="stMetricLabel"] {
            color: #757575 !important;
            font-size: 1.1rem;
            font-weight: 500;
        }

        /* 5. BUTTONS: High Contrast */
        button[kind="primary"] {
            background-color: #2e7d32 !important;
            color: white !important;
            border-radius: 8px;
            padding: 12px 24px;
            font-size: 16px;
            border: none;
            transition: 0.3s;
            box-shadow: 0 4px 6px rgba(46, 125, 50, 0.2);
        }
        button[kind="primary"]:hover {
            background-color: #1b5e20 !important;
            transform: translateY(-2px);
        }
        
        /* 6. LOGOUT BUTTON: Distinct Red */
        [data-testid="stSidebar"] button {
            background-color: #ffebee !important;
            color: #c62828 !important;
            border: 1px solid #ef5350 !important;
        }

        /* 7. TABS: Modern Navigation */
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px;
            border-bottom: 2px solid #eeeeee;
        }
        .stTabs [aria-selected="true"] {
            background-color: #e8f5e9 !important;
            color: #1b5e20 !important;
            border-radius: 8px;
            font-weight: bold;
        }
        
        /* 8. ALERTS: Soft Colors */
        .stAlert {
            border-radius: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
DB_FILE = 'esg_history_fix.db'

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
    # Renaming columns to be friendly
    return pd.DataFrame(data, columns=['Date', 'Total Score', 'Planet (Env)', 'People (Soc)', 'Policy (Gov)'])

init_db()

# --- PDF GENERATOR ---
if pdf_available:
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            self.cell(0, 10, 'GreenInvest Sustainability Report', 0, 1, 'C')
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
        pdf.cell(200, 10, txt=f"Planet (Env): {e:.1f}", ln=True)
        pdf.cell(200, 10, txt=f"People (Soc): {s:.1f}", ln=True)
        pdf.cell(200, 10, txt=f"Policy (Gov): {g:.1f}", ln=True)
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
authenticator = stauth.Authenticate(credentials, 'green_cookie_insight', 'secure_key_insight', cookie_expiry_days=1)

if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None

# --- LOGIN SCREEN ---
if not st.session_state['authentication_status']:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("""
            <div style='text-align: center; margin-bottom: 20px; background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); border-top: 5px solid #2e7d32;'>
                <h1 style='color: #2e7d32; font-size: 50px; margin: 0;'>🌿</h1>
                <h1 style='color: #2e7d32; margin-top: 0;'>GreenInvest</h1>
                <p style='color: gray; margin-top: 10px; font-size: 18px;'>Your Sustainability Dashboard</p>
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
    
    # LOGOUT BUTTON (In Sidebar)
    st.sidebar.markdown("### User Settings")
    st.sidebar.write(f"Logged in as: **{name}**")
    authenticator.logout('Sign Out', 'sidebar')

    # HERO BANNER
    st.markdown(f"""
        <div style="background: white; padding: 30px; border-radius: 15px; border-left: 8px solid #2e7d32; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 25px;">
            <h1 style="margin:0; color: #1b5e20;">Hello, {name}</h1>
            <p style="margin:0; color: #616161; font-size: 18px;">Here is your sustainability summary.</p>
        </div>
    """, unsafe_allow_html=True)

    # SIDEBAR INPUTS
    st.sidebar.header("📝 Enter Your Data")
    input_method = st.sidebar.radio("How to add data?", ["Manual Entry", "Upload CSV File"])
    
    inputs = {}
    calc_triggered = False

    if input_method == "Manual Entry":
        with st.sidebar.form("manual_form"):
            st.markdown("### 1. Planet (Environment)")
            e1 = st.number_input("Energy Used (kWh)", 50000)
            e2 = st.number_input("Water Used (m3)", 2000)
            e3 = st.slider("Recycling Rate (%)", 0, 100, 40)
            e4 = st.slider("Renewable Energy (%)", 0, 100, 20)
            st.divider()
            st.markdown("### 2. People (Social)")
            s1 = st.slider("Employee Turnover (%)", 0, 100, 15)
            s2 = st.number_input("Safety Incidents", 0)
            s3 = st.slider("Diversity (%)", 0, 100, 30)
            st.divider()
            st.markdown("### 3. Policy (Governance)")
            g1 = st.slider("Board Independence (%)", 0, 100, 60)
            g2 = st.slider("Ethics Compliance (%)", 0, 100, 95)
            
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

    # DASHBOARD LOGIC
    if calc_triggered:
        final, e, s, g = calculate_scores(inputs)
        save_data(username, final, e, s, g, inputs)
        
        # Determine Changes (Delta)
        history = get_history(username)
        delta_val = 0
        if len(history) > 1:
            # Compare current score with the previous entry
            prev_score = history.iloc[-2]['Total Score']
            delta_val = final - prev_score

        if pdf_available:
            col_pdf_dl, _ = st.columns([1, 4])
            with col_pdf_dl:
                pdf_bytes = create_pdf(name, final, e, s, g, inputs)
                st.download_button("📄 Download Report (PDF)", pdf_bytes, "ESG_Report.pdf", "application/pdf")

        # --- TABS ---
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 My Score", "🚀 How to Improve", "📈 Past Scores", "🔍 View Data", "🔮 Simulator"])

        # TAB 1: SCORE
        with tab1:
            st.subheader("Your Scorecard")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Score", f"{final:.1f}", delta=f"{delta_val:.1f} since last time")
            c2.metric("Planet", f"{e:.1f}", help="Environment: Energy, Water, Waste")
            c3.metric("People", f"{s:.1f}", help="Social: Safety, Turnover, Diversity")
            c4.metric("Policy", f"{g:.1f}", help="Governance: Ethics, Board")
            
            st.divider()
            
            col_left, col_right = st.columns(2)
            with col_left:
                st.markdown("### 🌍 Impact Breakdown")
                st.caption("Which resources are you using the most?")
                co2_data = pd.DataFrame({'Source': ['Energy', 'Water'], 'Impact': [inputs.get('energy',0)*0.4, inputs.get('water',0)*0.1]})
                fig_pie = px.pie(co2_data, values='Impact', names='Source', color_discrete_sequence=['#66bb6a', '#42a5f5'], hole=0.5)
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col_right:
                st.markdown("### ⚖️ Balance Check")
                st.caption("Are you focusing too much on one area?")
                df_radar = pd.DataFrame(dict(r=[e, s, g, e], theta=['Planet', 'People', 'Policy', 'Planet']))
                fig_radar = px.line_polar(df_radar, r='r', theta='theta', line_close=True)
                fig_radar.update_traces(fill='toself', line_color='#66bb6a')
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
                st.plotly_chart(fig_radar, use_container_width=True)

        # TAB 2: IMPROVEMENTS
        with tab2:
            st.subheader("Simple Steps to Improve")
            
            col_act, col_fund = st.columns(2)
            
            with col_act:
                st.markdown("#### 🛠️ Recommendations")
                if e < 70: 
                    st.error("Planet Score is Low")
                    st.write("• **Tip:** Switch to LED lights to save energy.")
                    st.write("• **Tip:** Fix water leaks.")
                elif s < 70:
                    st.warning("People Score is Low")
                    st.write("• **Tip:** Increase safety training.")
                else:
                    st.success("You are doing great!")
                    st.write("Maintain current standards.")

            with col_fund:
                st.markdown("#### 💰 Financial Benefits")
                with st.expander("🏦 Bank Loan Discount (0.5%)"):
                    if final > 60: 
                        st.success("✅ ELIGIBLE (Score > 60)")
                    else: 
                        st.error("❌ NOT ELIGIBLE yet")
                
                with st.expander("🌱 Government Grant ($50k)"):
                    if e > 75: 
                        st.success("✅ ELIGIBLE (Planet Score > 75)")
                    else: 
                        st.error("❌ NOT ELIGIBLE yet")

        # TAB 3: HISTORY (FIXED)
        with tab3:
            st.subheader("Your Progress")
            st.caption("See how your scores have changed over time.")
            hist = get_history(username)
            if not hist.empty:
                # Use a Line Chart for clarity on multiple metrics
                fig_line = px.line(hist, x='Date', y=['Total Score', 'Planet (Env)', 'People (Soc)', 'Policy (Gov)'],
                                   title="Performance Trends", markers=True)
                fig_line.update_layout(hovermode="x unified")
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("No history found. Click 'Calculate My Score' to start tracking!")

        # TAB 4: RAW DATA
        with tab4:
            st.subheader("Your Input Data")
            df_display = pd.DataFrame(list(inputs.items()), columns=['Item', 'Value'])
            st.dataframe(df_display, use_container_width=True)

        # TAB 5: SIMULATOR
        with tab5:
            st.subheader("Test Changes")
            st.caption("See what happens if you change your business inputs.")
            
            col_sim1, col_sim2 = st.columns(2)
            with col_sim1:
                sim_energy = st.slider("Energy Usage", 0, 100000, int(inputs.get('energy', 50000)))
                sim_turnover = st.slider("Employee Turnover", 0, 100, int(inputs.get('turnover', 15)))
            
            with col_sim2:
                sim_e_raw = ((max(0, 100 - sim_energy/1000)) + (max(0, 100 - inputs.get('water',0)/500)) + inputs.get('recycling',0)) / 4
                sim_e_score = min(100, max(0, sim_e_raw))
                sim_s_raw = ((max(0, 100 - sim_turnover*2)) + (max(0, 100 - inputs.get('incidents',0)*10)) + inputs.get('diversity',0)) / 3
                sim_s_score = min(100, max(0, sim_s_raw))
                
                sim_final = (sim_e_score + sim_s_score + g) / 3
                
                st.metric("New Predicted Score", f"{sim_final:.1f}", delta=f"{sim_final - final:.1f}")

    else:
        st.info("👈 Please enter your data in the sidebar to generate your dashboard.")
