import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sqlite3
import datetime
import json
import time
import io

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
        .metric-card {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
DB_FILE = 'esg_visual.db'

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

# --- PDF GENERATOR CLASS ---
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
        
        # Title Info
        pdf.cell(200, 10, txt=f"Prepared for: {name}", ln=True, align='L')
        pdf.cell(200, 10, txt=f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}", ln=True, align='L')
        pdf.ln(10)
        
        # Scores
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Executive Summary", ln=True, align='L')
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Overall ESG Score: {overall:.1f} / 100", ln=True)
        pdf.cell(200, 10, txt=f"Environmental: {e:.1f}", ln=True)
        pdf.cell(200, 10, txt=f"Social: {s:.1f}", ln=True)
        pdf.cell(200, 10, txt=f"Governance: {g:.1f}", ln=True)
        pdf.ln(10)

        # Input Data Summary
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Input Data Breakdown", ln=True, align='L')
        pdf.set_font("Arial", size=10)
        for key, value in inputs.items():
            pdf.cell(200, 7, txt=f"{key.capitalize()}: {value}", ln=True)
        
        return pdf.output(dest='S').encode('latin-1')

# --- CALCULATION ENGINE ---
def calculate_scores(inputs):
    # Default values for missing keys (safe fallback)
    energy = inputs.get('energy', 50000)
    water = inputs.get('water', 2000)
    recycling = inputs.get('recycling', 40)
    renewable = inputs.get('renewable', 0) # Default to 0 if missing in CSV
    
    turnover = inputs.get('turnover', 15)
    incidents = inputs.get('incidents', 0)
    diversity = inputs.get('diversity', 30)
    
    board = inputs.get('board', 60)
    ethics = inputs.get('ethics', 95)

    # 1. Environmental Logic
    e_raw = ((max(0, 100 - energy/1000)) + (max(0, 100 - water/500)) + (recycling) + (renewable * 1.5)) / 4
    e_score = min(100, max(0, e_raw))

    # 2. Social Logic
    s_raw = ((max(0, 100 - turnover*2)) + (max(0, 100 - incidents*10)) + (diversity)) / 3
    s_score = min(100, max(0, s_raw))

    # 3. Governance Logic
    g_raw = (board + ethics) / 2
    g_score = min(100, max(0, g_raw))

    # Final Calculation
    final = (e_score + s_score + g_score) / 3
    return final, e_score, s_score, g_score

# --- VISUALIZATION HELPERS ---
def make_gauge(val, title, color):
    return go.Figure(go.Indicator(
        mode="gauge+number", value=val, title={'text': title},
        gauge={'axis': {'range': [None, 100]}, 'bar': {'color': color}, 'steps': [{'range': [0,50], 'color': 'white'}, {'range': [50,100], 'color': '#f1f8e9'}]}
    )).update_layout(height=250, margin=dict(l=10,r=10,t=40,b=10), paper_bgcolor='rgba(0,0,0,0)')

# --- AUTHENTICATION FLOW ---
credentials = get_credentials()
authenticator = stauth.Authenticate(credentials, 'green_cookie_vis', 'secure_key_vis', cookie_expiry_days=1)
authenticator.login(location='main')

if st.session_state["authentication_status"]:
    # === LOGGED IN ===
    username = st.session_state["username"]
    name = st.session_state["name"]
    authenticator.logout('Logout', 'sidebar')

    # Hero Banner
    st.markdown(f"""
        <div class="hero-section">
            <h1 class="hero-title">GreenInvest Analytics</h1>
            <p>Welcome, {name}. Visualizing your Sustainability Journey.</p>
        </div>
    """, unsafe_allow_html=True)

    # --- SIDEBAR INPUTS ---
    st.sidebar.header("🛠️ Data Input Panel")
    input_method = st.sidebar.radio("Choose Input Method:", ["Manual Entry", "Upload CSV"])
    
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
            if st.form_submit_button("🚀 Calculate Score"):
                inputs = {'energy':e1, 'water':e2, 'recycling':e3, 'renewable':e4,
                          'turnover':s1, 'incidents':s2, 'diversity':s3,
                          'board':g1, 'ethics':g2}
                calc_triggered = True

    else:
        # Template without Charity/Training
        template = pd.DataFrame({'energy': [50000], 'water': [2000], 'recycling': [40], 'renewable': [20],
                                 'turnover': [15], 'incidents': [0], 'diversity': [30],
                                 'board': [60], 'ethics': [95]})
        st.sidebar.download_button("Download Template CSV", template.to_csv(index=False), "esg_visual_template.csv")
        
        uploaded_file = st.sidebar.file_uploader("Upload CSV", type=['csv'])
        if uploaded_file and st.sidebar.button("Process CSV"):
            try:
                df = pd.read_csv(uploaded_file)
                
                # --- SMART PARSER FOR STACKED/LONG CSV ---
                if 'metric' in df.columns and 'value' in df.columns:
                    # Convert specific "Long" format to "Wide"
                    # Mapping known CSV keys to app keys
                    key_map = {
                        'energy_consumption_kwh': 'energy',
                        'water_usage_m3': 'water',
                        'recycling_rate_pct': 'recycling',
                        'employee_turnover_pct': 'turnover',
                        'safety_incidents_count': 'incidents',
                        'management_diversity_pct': 'diversity',
                        'board_independence_pct': 'board',
                        'ethics_training_pct': 'ethics'
                        # 'renewable' is missing in your CSV, will default to 0
                    }
                    
                    # Parse the first block of data found
                    parsed_inputs = {}
                    for _, row in df.iterrows():
                        metric = str(row['metric']).strip()
                        if metric in key_map:
                            parsed_inputs[key_map[metric]] = row['value']
                            
                    # Ensure we have something
                    if not parsed_inputs:
                        st.error("Found metric column but no matching keys. Check CSV content.")
                    else:
                        inputs = parsed_inputs
                        calc_triggered = True
                        st.success("✅ Successfully read stacked CSV format!")

                else:
                    # Standard Wide Format
                    df.columns = df.columns.str.lower().str.strip()
                    inputs = df.iloc[0].to_dict()
                    calc_triggered = True
                    
            except Exception as e:
                st.error(f"Error reading CSV: {e}")

    # --- MAIN DASHBOARD LOGIC ---
    if calc_triggered:
        final, e, s, g = calculate_scores(inputs)
        save_data(username, final, e, s, g, inputs)

        # PDF DOWNLOAD SECTION
        if pdf_available:
            col_pdf_dl, _ = st.columns([1, 4])
            with col_pdf_dl:
                pdf_bytes = create_pdf(name, final, e, s, g, inputs)
                st.download_button(
                    label="📄 Download PDF Report",
                    data=pdf_bytes,
                    file_name="ESG_Report.pdf",
                    mime="application/pdf"
                )
        else:
            st.warning("Install 'fpdf' (pip install fpdf) to enable PDF downloads.")

        # TABS
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Performance Overview", "🎯 Recommendations", "💰 Finance Marketplace", "🕰️ Historical Trends", "🧪 Scenario Planner"])

        # TAB 1: VISUAL OVERVIEW
        with tab1:
            st.subheader("Executive Scorecard")
            
            # Top Level Gauges
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.plotly_chart(make_gauge(final, "Overall ESG", "#1b5e20"), use_container_width=True)
            with c2: st.plotly_chart(make_gauge(e, "Environmental", "#43a047"), use_container_width=True)
            with c3: st.plotly_chart(make_gauge(s, "Social", "#1976d2"), use_container_width=True)
            with c4: st.plotly_chart(make_gauge(g, "Governance", "#fbc02d"), use_container_width=True)

            st.divider()

            # Detailed Visuals
            st.subheader("Detailed Impact Analysis")
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.markdown("##### 🌍 Your Carbon Footprint breakdown")
                st.write("Visualizing where your environmental impact comes from.")
                
                # Mock CO2 Calculation for Visualization
                en_val = inputs.get('energy', 0)
                wa_val = inputs.get('water', 0)
                co2_energy = en_val * 0.4
                co2_water = wa_val * 0.1
                co2_data = pd.DataFrame({
                    'Source': ['Energy Consumption', 'Water Usage'],
                    'Emissions (kg CO2)': [co2_energy, co2_water]
                })
                fig_pie = px.pie(co2_data, values='Emissions (kg CO2)', names='Source', 
                                 color_discrete_sequence=['#ff7043', '#42a5f5'], hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_right:
                st.markdown("##### ⚖️ ESG Balance Radar")
                st.write("See which pillar is dragging down your score.")
                
                df_radar = pd.DataFrame(dict(
                    r=[e, s, g, e],
                    theta=['Environmental', 'Social', 'Governance', 'Environmental']
                ))
                fig_radar = px.line_polar(df_radar, r='r', theta='theta', line_close=True)
                fig_radar.update_traces(fill='toself', line_color='#2e7d32')
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
                st.plotly_chart(fig_radar, use_container_width=True)

        # TAB 2: RECOMMENDATIONS
        with tab2:
            st.subheader("Your Action Plan")
            st.info("These recommendations are prioritized based on your lowest scores.")
            
            col_rec1, col_rec2 = st.columns(2)
            
            with col_rec1:
                if e < 70:
                    st.error("🚨 Critical: Environmental")
                    st.markdown("""
                    * **Switch to LED:** Replacing lights can cut energy use by 15%.
                    * **Water Sensors:** Install smart sensors to detect leaks.
                    """)
                else:
                    st.success("✅ Good: Environmental")
                    st.write("Maintain your recycling programs.")

                if s < 70:
                    st.warning("⚠️ Improvement Needed: Social")
                    st.markdown("""
                    * **Safety Audit:** Review your accident logs immediately.
                    * **Feedback Box:** Let employees submit concerns anonymously.
                    """)
            
            with col_rec2:
                if g < 70:
                    st.warning("⚠️ Improvement Needed: Governance")
                    st.markdown("""
                    * **Add Independent Director:** Bring in an outsider to the board.
                    * **Publish Code of Conduct:** Ensure all staff sign ethics forms.
                    """)
                else:
                    st.success("✅ Good: Governance")
                    st.write("Your compliance is strong.")

        # TAB 3: FINANCE MARKETPLACE
        with tab3:
            st.subheader("💰 Unlocked Funding Opportunities")
            st.write("Banks and investors offer special rates for high ESG scores.")
            
            # Using Expander for a cleaner look
            with st.expander("🏦 Green Business Loan (Bank of America)", expanded=(final > 60)):
                st.write("**Requirement:** Score > 60")
                if final > 60:
                    st.success("✅ You Qualify!")
                    st.write("Get 0.5% off interest rates for energy efficient equipment.")
                else:
                    st.error("❌ Locked (Improve score to 60)")

            with st.expander("🌱 Government Sustainability Grant", expanded=(e > 75)):
                st.write("**Requirement:** Environmental Score > 75")
                if e > 75:
                    st.success("✅ You Qualify!")
                    st.write("Eligible for up to $50,000 in direct grants.")
                else:
                    st.error("❌ Locked (Improve Environmental score to 75)")

        # TAB 4: HISTORY
        with tab4:
            st.subheader("📈 Performance Over Time")
            hist = get_history(username)
            if not hist.empty:
                fig_hist = px.area(hist, x='Date', y='Overall', title="Your Growth Trajectory", 
                                   color_discrete_sequence=['#2e7d32'])
                st.plotly_chart(fig_hist, use_container_width=True)
                st.dataframe(hist)
            else:
                st.info("Save your first calculation to see trends here.")

        # TAB 5: SCENARIO PLANNER
        with tab5:
            st.subheader("🧪 What-If Simulator")
            st.write("Adjust these sliders to see how changes affect your score **without** saving data.")
            
            c_sim1, c_sim2 = st.columns(2)
            with c_sim1:
                # Safe fallback for simulation sliders
                safe_energy = int(inputs.get('energy', 50000))
                safe_turnover = int(inputs.get('turnover', 15))
                
                sim_energy = st.slider("Simulate Energy Reduction (kWh)", 0, 100000, safe_energy)
                sim_turnover = st.slider("Simulate Turnover (%)", 0, 100, safe_turnover)
            
            with c_sim2:
                # Real-time calculation for simulation
                # Ensure we have values for calc
                w_val = inputs.get('water', 2000)
                r_val = inputs.get('recycling', 40)
                re_val = inputs.get('renewable', 0)
                i_val = inputs.get('incidents', 0)
                d_val = inputs.get('diversity', 30)

                sim_e_raw = ((max(0, 100 - sim_energy/1000)) + (max(0, 100 - w_val/500)) + (r_val) + (re_val * 1.5)) / 4
                sim_e_score = min(100, max(0, sim_e_raw))
                
                sim_s_raw = ((max(0, 100 - sim_turnover*2)) + (max(0, 100 - i_val*10)) + (d_val)) / 3
                sim_s_score = min(100, max(0, sim_s_raw))
                
                sim_final = (sim_e_score + sim_s_score + g) / 3
                
                st.metric("Projected New Score", f"{sim_final:.1f}", delta=f"{sim_final - final:.1f}")
                if sim_final > final:
                    st.success("This change would improve your rating!")

    else:
        st.info("👈 Use the sidebar to start.")

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
