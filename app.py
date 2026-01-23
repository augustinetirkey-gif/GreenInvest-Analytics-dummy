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
    page_title="GreenAnalytics",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ANALYTICS THEME CSS (HIGH CONTRAST DARK) ---
st.markdown("""
    <style>
        /* 1. BACKGROUND: Professional Dark Analytics Theme */
        .stApp {
            background: linear-gradient(135deg, #0b0f19 0%, #16222a 100%);
            color: #ffffff;
        }

        /* 2. TYPOGRAPHY */
        h1, h2, h3 {
            color: #00FF99 !important; /* Neon Green Title */
            font-family: 'Helvetica Neue', sans-serif;
            font-weight: 700;
        }
        p, label, .stMarkdown {
            color: #E0E0E0 !important;
            font-size: 1.05rem;
        }

        /* 3. INPUT FIELDS */
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: #1F2937;
            color: #00FF99 !important;
            border: 1px solid #374151;
            border-radius: 8px;
        }

        /* 4. BUTTONS - "Execute Analysis" Style */
        div.stButton > button {
            background: linear-gradient(90deg, #00C853, #64DD17);
            color: #000000;
            font-weight: bold;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            box-shadow: 0 4px 14px rgba(0, 200, 83, 0.4);
            transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 200, 83, 0.6);
            color: white;
        }

        /* 5. METRIC CARDS - Analytical HUD */
        div[data-testid="metric-container"] {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid #00FF99;
            border-left: 6px solid #00FF99;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        [data-testid="stMetricValue"] {
            font-size: 2.5rem !important;
            color: #ffffff !important;
        }
        [data-testid="stMetricLabel"] {
            color: #00FF99 !important;
            font-size: 1rem;
            font-weight: bold;
        }

        /* 6. SIDEBAR */
        section[data-testid="stSidebar"] {
            background-color: #0f172a;
            border-right: 1px solid #334155;
        }

        /* 7. TABS */
        .stTabs [aria-selected="true"] {
            background-color: rgba(0, 255, 153, 0.2) !important;
            border-bottom: 2px solid #00FF99 !important;
            color: #00FF99 !important;
        }
        
        /* 8. INFO BOXES */
        .stAlert {
            background-color: rgba(255,255,255,0.05);
            border: 1px solid #444;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
DB_FILE = 'green_analytics.db'

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

# --- INSIGHT ENGINE (NEW FEATURE) ---
# Dictionary to map metrics to human-readable explanations
METRIC_KNOWLEDGE = {
    'energy': "Scope 1 & 2 emissions derived from electricity and fuel usage.",
    'water': "Total water withdrawal in cubic meters. Crucial for resource scarcity risks.",
    'recycling': "Percentage of waste diverted from landfills.",
    'renewable': "Percentage of energy sourced from solar, wind, or hydro.",
    'turnover': "Rate at which employees leave the workforce (lower is usually better).",
    'incidents': "Number of reportable safety accidents per year.",
    'diversity': "Percentage of management roles held by underrepresented groups.",
    'board': "Percentage of independent directors (reduces conflict of interest).",
    'ethics': "Percentage of employees trained in anti-corruption/ethics policies."
}

def generate_text_insight(score, category):
    if score >= 80:
        return f"🌟 **Excellent {category} Performance:** You are leading the industry. Your current strategy is highly effective and presents low risk to investors."
    elif score >= 50:
        return f"⚠️ **Moderate {category} Performance:** You are compliant but not competitive. There are specific inefficiencies holding back your rating."
    else:
        return f"🚨 **Critical {category} Risk:** Immediate action required. Current metrics indicate high liability and potential regulatory fines."

# --- PDF GENERATOR ---
if pdf_available:
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            self.set_text_color(0, 150, 0)
            self.cell(0, 10, 'GreenAnalytics | Executive Summary', 0, 1, 'C')
            self.ln(5)
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Generated by GreenAnalytics - Page {self.page_no()}', 0, 0, 'C')

    def create_pdf(name, overall, e, s, g, inputs):
        pdf = PDF()
        pdf.add_page()
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Analyst: {name}", ln=True)
        pdf.cell(200, 10, txt=f"Report Date: {datetime.datetime.now().strftime('%Y-%m-%d')}", ln=True)
        pdf.ln(10)
        
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="1. Performance Overview", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Overall ESG Rating: {overall:.1f} / 100", ln=True)
        pdf.cell(200, 10, txt=f"Environmental Score: {e:.1f}", ln=True)
        pdf.cell(200, 10, txt=f"Social Score: {s:.1f}", ln=True)
        pdf.cell(200, 10, txt=f"Governance Score: {g:.1f}", ln=True)
        pdf.ln(10)
        
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="2. Raw Data Inputs", ln=True)
        pdf.set_font("Arial", size=10)
        for key, value in inputs.items():
            pdf.cell(200, 7, txt=f"{key.capitalize()}: {value}", ln=True)
        return pdf.output(dest='S').encode('latin-1')

# --- CALCULATION ENGINE ---
def calculate_scores(inputs):
    # Safe defaults using .get()
    energy = float(inputs.get('energy', 50000))
    water = float(inputs.get('water', 2000))
    recycling = float(inputs.get('recycling', 40))
    renewable = float(inputs.get('renewable', 0))
    turnover = float(inputs.get('turnover', 15))
    incidents = float(inputs.get('incidents', 0))
    diversity = float(inputs.get('diversity', 30))
    board = float(inputs.get('board', 60))
    ethics = float(inputs.get('ethics', 95))

    # Logic: normalize raw inputs to 0-100 scale
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
authenticator = stauth.Authenticate(credentials, 'green_analytics_cookie', 'secure_key_analytics', cookie_expiry_days=1)

if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None

# --- LOGIN SCREEN ---
if not st.session_state['authentication_status']:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("""
            <div style='text-align: center; margin-top: 50px; margin-bottom: 30px;'>
                <h1 style='font-size: 60px; margin:0;'>🌿</h1>
                <h1 style='color: #00FF99; margin-top:-10px; font-weight: 800; letter-spacing: 2px;'>GREEN ANALYTICS</h1>
                <p style='color: #cccccc;'>Advanced ESG Intelligence Platform</p>
            </div>
        """, unsafe_allow_html=True)

    authenticator.login(location='main')

    if st.session_state['authentication_status'] is False:
        st.error('❌ Access Denied: Invalid Credentials')
    elif st.session_state['authentication_status'] is None:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🆕 CREATE ANALYST ACCOUNT"):
            with st.form("reg_form"):
                new_name = st.text_input("Full Name")
                new_user = st.text_input("Username")
                new_pass = st.text_input("Password", type="password")
                if st.form_submit_button("Create Profile"):
                    if len(new_pass) > 3:
                        if register_user(new_user, new_name, new_pass):
                            st.success("Account created successfully! Please login.")
                        else:
                            st.error("Username already exists.")
                    else:
                        st.warning("Password must be at least 4 characters.")

# --- MAIN DASHBOARD ---
if st.session_state['authentication_status']:
    st.session_state.initial_sidebar_state = "expanded"
    username = st.session_state["username"]
    name = st.session_state["name"]
    authenticator.logout('Logout', 'sidebar')

    # SIDEBAR CONFIGURATION
    st.sidebar.title(f"👤 {name}")
   "
    st.sidebar.divider()
    
    st.sidebar.header("🛠️ Data Configuration")
    input_method = st.sidebar.radio("Data Source:", ["Manual Input", "Upload CSV"], help="Choose how you want to input your sustainability data.")
    
    inputs = {}
    calc_triggered = False

    if input_method == "Manual Input":
        with st.sidebar.form("manual_form"):
            st.markdown("### 🌍 Environment")
            e1 = st.number_input("Energy Consumption (kWh)", 0, 200000, 50000, help="Total electricity and fuel usage per year.")
            e2 = st.number_input("Water Usage (m³)", 0, 50000, 2000, help="Total water withdrawn from all sources.")
            e3 = st.slider("Recycling Rate (%)", 0, 100, 40, help="Percentage of waste diverted from landfill.")
            e4 = st.slider("Renewable Energy (%)", 0, 100, 20, help="Percent of energy from solar/wind/hydro.")
            
            st.markdown("### 👥 Social")
            s1 = st.slider("Employee Turnover (%)", 0, 100, 15, help="Percentage of employees leaving voluntarily.")
            s2 = st.number_input("Safety Incidents", 0, 100, 0, help="Number of reportable OSHA incidents.")
            s3 = st.slider("Management Diversity (%)", 0, 100, 30, help="Minority/Female representation in management.")
            
            st.markdown("### ⚖️ Governance")
            g1 = st.slider("Board Independence (%)", 0, 100, 60, help="% of board members not affiliated with the company.")
            g2 = st.slider("Ethics Training (%)", 0, 100, 95, help="% of staff who completed compliance training.")
            
            if st.form_submit_button("🚀 RUN ANALYSIS", type="primary"):
                inputs = {'energy':e1, 'water':e2, 'recycling':e3, 'renewable':e4, 'turnover':s1, 'incidents':s2, 'diversity':s3, 'board':g1, 'ethics':g2}
                calc_triggered = True
    else:
        st.sidebar.info("Upload a CSV with columns: metric, value")
        uploaded_file = st.sidebar.file_uploader("Upload Data", type=['csv'])
        if uploaded_file and st.sidebar.button("Process File"):
            try:
                df = pd.read_csv(uploaded_file)
                # Basic csv parsing logic (simplified)
                inputs = df.set_index('metric')['value'].to_dict() if 'metric' in df.columns else df.iloc[0].to_dict()
                calc_triggered = True
                st.sidebar.success("File processed!")
            except Exception as e:
                st.error(f"Error parsing file: {e}")

    # HEADER AREA
    col_head_1, col_head_2 = st.columns([3, 1])
    with col_head_1:
        st.title("ESG Performance Dashboard")
        st.markdown(f"**Current Session:** {datetime.datetime.now().strftime('%B %d, %Y')}")
    with col_head_2:
        if calc_triggered and pdf_available:
            final, e, s, g = calculate_scores(inputs)
            pdf_bytes = create_pdf(name, final, e, s, g, inputs)
            st.download_button("📄 Download Report", pdf_bytes, "ESG_Report.pdf", "application/pdf")

    if not calc_triggered:
         # Empty State / Landing
        st.info("👈 Please enter your sustainability data in the sidebar to generate the dashboard.")
        [st.image("https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&q=80&w=2670", caption="Sustainable Data Analytics", use_column_width=True)]
    
    else:
        # Run Calculation
        final, e, s, g = calculate_scores(inputs)
        save_data(username, final, e, s, g, inputs)

        # TABS
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 RANKING & ANALYSIS", "🎯 STRATEGIC OBJECTIVES", "💰 FINANCIAL IMPACT", "🕰️ HISTORICAL TRENDS", "🧪 SCENARIO SIMULATOR"])

        with tab1:
            st.markdown("### 🏆 Executive Summary")
            
            # TOP LEVEL METRICS with Context
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Overall ESG Score", f"{final:.1f}/100", delta="Target: 80")
            c2.metric("Environmental", f"{e:.1f}", delta=f"{e-70:.1f} vs Avg", delta_color="normal")
            c3.metric("Social", f"{s:.1f}", delta=f"{s-70:.1f} vs Avg", delta_color="normal")
            c4.metric("Governance", f"{g:.1f}", delta=f"{g-70:.1f} vs Avg", delta_color="normal")
            
            st.divider()
            
            # DEEP DIVE VISUALIZATIONS
            col_viz1, col_viz2 = st.columns([1, 1])
            
            with col_viz1:
                st.subheader("Performance Gauge")
                # Using a Gauge Chart for better readability than Radar
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = final,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "Overall Sustainability Health"},
                    gauge = {
                        'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "white"},
                        'bar': {'color': "#00FF99"},
                        'bgcolor': "rgba(0,0,0,0)",
                        'borderwidth': 2,
                        'bordercolor': "gray",
                        'steps': [
                            {'range': [0, 50], 'color': '#FF5252'},
                            {'range': [50, 75], 'color': '#FFD740'},
                            {'range': [75, 100], 'color': '#69F0AE'}],
                        'threshold': {
                            'line': {'color': "white", 'width': 4},
                            'thickness': 0.75,
                            'value': 80}}))
                fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                st.plotly_chart(fig_gauge, use_container_width=True)
                
                st.info(f"💡 **Analyst Note:** {generate_text_insight(final, 'Overall')}")

            with col_viz2:
                st.subheader("Metric Breakdown")
                # Horizontal Bar Chart for granular comparison
                breakdown_data = pd.DataFrame({
                    'Metric': ['Energy Eff.', 'Water Mgmt', 'Recycling', 'Social Turnover', 'Safety', 'Diversity', 'Board', 'Ethics'],
                    'Score': [
                        max(0, 100 - inputs['energy']/1000), 
                        max(0, 100 - inputs['water']/500), 
                        inputs['recycling'], 
                        max(0, 100 - inputs['turnover']*2), 
                        max(0, 100 - inputs['incidents']*10),
                        inputs['diversity'],
                        inputs['board'],
                        inputs['ethics']
                    ]
                })
                # Cap scores at 100 for visual
                breakdown_data['Score'] = breakdown_data['Score'].clip(0, 100)
                
                fig_bar = px.bar(breakdown_data, x='Score', y='Metric', orientation='h', 
                                 text='Score', color='Score', 
                                 color_continuous_scale=['#FF5252', '#FFD740', '#00FF99'])
                fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                                      font={'color': "white"}, xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
                st.plotly_chart(fig_bar, use_container_width=True)

            # Detailed Text Explanation Section
            with st.expander("📚 View Detailed Metric Definitions"):
                st.markdown("""
                * **Energy Efficiency:** Derived from total kWh. Lower consumption yields higher scores.
                * **Turnover:** Inverse metric. High turnover reduces your score.
                * **Board Independence:** Higher independence correlates with better governance.
                """)

        with tab2:
            st.subheader("🎯 Strategic Roadmap & Objectives")
            st.write("Based on your data, here are recommended actions to improve your ranking.")
            
            col_obj1, col_obj2 = st.columns(2)
            
            with col_obj1:
                st.markdown("#### 🚨 Priority 1: Critical Fixes")
                if e < 60:
                    st.error(f"**Environment Critical (Score: {e:.1f})**")
                    st.markdown("- **Action:** Audit energy usage.")
                    st.markdown("- **Impact:** Potential 15% cost reduction.")
                    [st.image("https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?auto=format&fit=crop&q=80&w=1000", caption="LED Upgrade needed", width=300)]
                elif s < 60:
                    st.error(f"**Social Critical (Score: {s:.1f})**")
                    st.markdown("- **Action:** Implement safety protocols.")
                    st.markdown("- **Impact:** Reduce liability insurance premiums.")
                else:
                    st.success("No critical vulnerabilities detected.")

            with col_obj2:
                st.markdown("#### 📈 Priority 2: Optimization")
                if inputs['renewable'] < 50:
                    st.warning("**Transition to Renewables**")
                    st.markdown(f"Current Renewable: {inputs['renewable']}%. Target: 50%.")
                    st.progress(inputs['renewable']/100)
                if inputs['diversity'] < 40:
                    st.warning("**Improve Leadership Diversity**")
                    st.markdown(f"Current: {inputs['diversity']}%. Target: 40%.")

        with tab3:
            st.subheader("💰 Financial Rewards & Benefits")
            st.markdown("Higher ESG scores unlock real-world financial advantages.")
            
            c_rew1, c_rew2, c_rew3 = st.columns(3)
            with c_rew1:
                st.markdown("**🏦 Green Loan Eligibility**")
                if final > 70:
                    st.success("✅ **APPROVED**")
                    st.caption("Eligible for 0.5% interest rate reduction.")
                else:
                    st.error("❌ **DENIED**")
                    st.caption("Requires Score > 70")
            
            with c_rew2:
                st.markdown("**🏛️ Government Grants**")
                if e > 75:
                    st.success("✅ **ELIGIBLE**")
                    st.caption("Eligible for Clean Energy Tax Credits.")
                else:
                    st.error("❌ **INELIGIBLE**")
                    st.caption("Requires Env Score > 75")
            
            with c_rew3:
                st.markdown("**📉 Insurance Premium**")
                if s > 80:
                    st.success("✅ **DISCOUNT UNLOCKED**")
                    st.caption("Risk assessment qualifies for 10% premium drop.")
                else:
                    st.error("❌ **STANDARD RATE**")
                    st.caption("Requires Social Score > 80")

        with tab4:
            st.subheader("🕰️ Historical Performance Trends")
            hist_df = get_history(username)
            if not hist_df.empty:
                # Convert timestamps to clearer dates
                hist_df['Date'] = pd.to_datetime(hist_df['Date']).dt.strftime('%Y-%m-%d %H:%M')
                
                fig_line = px.line(hist_df, x='Date', y=['Overall', 'Environmental', 'Social', 'Governance'], 
                                   markers=True, title="Score Progression Over Time")
                fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                                       font={'color': "white"}, hovermode="x unified")
                st.plotly_chart(fig_line, use_container_width=True)
                
                with st.expander("View Raw Historical Data"):
                    st.dataframe(hist_df, use_container_width=True)
            else:
                st.info("No historical data found. Run your first analysis to see trends here.")

        with tab5:
            st.subheader("🧪 Scenario Simulator")
            st.markdown("Adjust parameters to see how they impact your score in real-time.")
            
            col_sim_input, col_sim_output = st.columns([1, 2])
            
            with col_sim_input:
                st.markdown("**Simulation Controls**")
                sim_energy = st.slider("Energy (kWh)", 0, 100000, int(inputs['energy']), key="sim_e")
                sim_turnover = st.slider("Turnover (%)", 0, 50, int(inputs['turnover']), key="sim_t")
                sim_recycling = st.slider("Recycling (%)", 0, 100, int(inputs['recycling']), key="sim_r")
            
            with col_sim_output:
                # Calculate Sim Scores
                s_e_raw = ((max(0, 100 - sim_energy/1000)) + (max(0, 100 - inputs['water']/500)) + (sim_recycling) + (inputs['renewable'] * 1.5)) / 4
                s_e_score = min(100, max(0, s_e_raw))
                s_s_raw = ((max(0, 100 - sim_turnover*2)) + (max(0, 100 - inputs['incidents']*10)) + (inputs['diversity'])) / 3
                s_s_score = min(100, max(0, s_s_raw))
                s_final = (s_e_score + s_s_score + g) / 3
                
                # Visual Comparison
                st.markdown("#### Projected Impact")
                c_sim1, c_sim2, c_sim3 = st.columns(3)
                
                c_sim1.metric("Current Score", f"{final:.1f}")
                c_sim2.metric("Simulated Score", f"{s_final:.1f}", delta=f"{s_final - final:.1f}")
                
                # Stacked Bar for comparison
                sim_data = pd.DataFrame({
                    'Scenario': ['Current', 'Simulated'],
                    'Score': [final, s_final]
                })
                fig_sim = px.bar(sim_data, x='Score', y='Scenario', orientation='h', 
                                 color='Scenario', color_discrete_map={'Current': 'gray', 'Simulated': '#00FF99'})
                fig_sim.update_layout(height=200, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                                      font={'color': "white"})
                st.plotly_chart(fig_sim, use_container_width=True)
