import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import json
import sqlite3
import datetime

# Import Authenticate and Hasher from streamlit_authenticator
# Note: Ensure you have streamlit-authenticator installed (pip install streamlit-authenticator)
from streamlit_authenticator import Authenticate, Hasher

# --- Page Configuration ---
st.set_page_config(
    page_title="GreenInvest Analytics",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
    <style>
        /* Fade-in-up animation for the welcome banner */
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .welcome-banner {
            animation: fadeInUp 1s ease-out;
        }

        /* Main App Background - light eco gradient */
        .stApp {
            background: linear-gradient(to right, #f0fff0, #e6f5d0, #e0f7fa);
            background-size: 400% 400%;
            animation: gradient 15s ease infinite;
            color: #1b3a2f;
        }

        @keyframes gradient {
            0% {background-position: 0% 50%;}
            50% {background-position: 100% 50%;}
            100% {background-position: 0% 50%;}
        }

        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background: linear-gradient(to bottom, #2e7d32, #388e3c);
        }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] .stTabs [data-baseweb="tab"],
        section[data-testid="stSidebar"] .stTextInput label,
        section[data-testid="stSidebar"] p {
            color: #ffffff !important;
        }
        
        section[data-testid="stSidebar"] .stTabs [aria-selected="true"] {
            font-weight: bold;
            border-bottom: 2px solid #dcedc8;
        }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE FUNCTIONS ---
DATABASE_NAME = 'esg_data.db'

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    # Create users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT
        )
    ''')
    # Create ESG history table
    c.execute('''
        CREATE TABLE IF NOT EXISTS esg_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            overall_score REAL,
            e_score REAL,
            s_score REAL,
            g_score REAL,
            env_data TEXT,
            social_data TEXT,
            gov_data TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

def add_user(username, password_hash, name):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash, name) VALUES (?, ?, ?)",
                  (username, password_hash, name))
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
    user_id = c.fetchone()
    conn.close()
    return user_id[0] if user_id else None

def save_esg_history(user_id, timestamp, overall, e, s, g, env_data, social_data, gov_data):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO esg_history (user_id, timestamp, overall_score, e_score, s_score, g_score, env_data, social_data, gov_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (user_id, timestamp, overall, e, s, g, json.dumps(env_data), json.dumps(social_data), json.dumps(gov_data)))
    conn.commit()
    conn.close()

def get_esg_history(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT timestamp, overall_score, e_score, s_score, g_score, env_data, social_data, gov_data FROM esg_history WHERE user_id = ? ORDER BY timestamp ASC", (user_id,))
    history_data = c.fetchall()
    conn.close()
    
    parsed_history = []
    for row in history_data:
        parsed_history.append({
            'timestamp': pd.to_datetime(row[0]),
            'overall_score': row[1],
            'e_score': row[2],
            's_score': row[3],
            'g_score': row[4],
            'env_data': json.loads(row[5]) if row[5] else None,
            'social_data': json.loads(row[6]) if row[6] else None,
            'gov_data': json.loads(row[7]) if row[7] else None,
        })
    return parsed_history

def get_all_users_for_authenticator():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT name, username, password_hash FROM users")
    users_data = c.fetchall()
    conn.close()
    
    credentials = {"usernames": {}}
    for row in users_data:
        name_val, username_val, password_hash_val = row
        credentials["usernames"][username_val] = {
            "name": name_val,
            "password": password_hash_val
        }
    return credentials

# Initialize DB on load
init_db()

# --- BUSINESS LOGIC & MOCK DATA ---
FINANCE_OPPORTUNITIES = [
    {"name": "GreenStart Grant Program", "type": "Grant", "description": "A grant for businesses starting their sustainability journey. Covers up to 50% of the cost for an initial energy audit.", "minimum_esg_score": 0, "icon": "🌱", "url": "#"},
    {"name": "Eco-Efficiency Business Loan", "type": "Loan", "description": "Low-interest loans for SMEs investing in energy-efficient equipment.", "minimum_esg_score": 60, "icon": "💡", "url": "#"},
    {"name": "Sustainable Supply Chain Fund", "type": "Venture Capital", "description": "Equity investment for companies demonstrating strong ESG performance.", "minimum_esg_score": 75, "icon": "🤝", "url": "#"},
    {"name": "Circular Economy Innovators Fund", "type": "Venture Capital", "description": "Seed funding for businesses pioneering models in waste reduction.", "minimum_esg_score": 80, "icon": "♻️", "url": "#"},
    {"name": "Impact Investors Alliance", "type": "Private Equity", "description": "For top-tier ESG performers. Provides significant growth capital.", "minimum_esg_score": 90, "icon": "🏆", "url": "#"}
]

INDUSTRY_AVERAGES = {'Environmental': 70, 'Social': 65, 'Governance': 75, 'Overall ESG': 70}

CO2_EMISSION_FACTORS = {
    'energy_kwh_to_co2': 0.4, 
    'water_m3_to_co2': 0.1,  
    'waste_kg_to_co2': 0.5   
}

def calculate_esg_score(env_data, social_data, gov_data):
    weights = {'E': 0.4, 'S': 0.3, 'G': 0.3}
    e_score = (max(0, 100 - (env_data['energy'] / 1000)) + max(0, 100 - (env_data['water'] / 500)) + max(0, 100 - (env_data['waste'] / 100)) + env_data['recycling']) / 4
    s_score = (max(0, 100 - (social_data['turnover'] * 2)) + max(0, 100 - (social_data['incidents'] * 10)) + social_data['diversity']) / 3
    g_score = (gov_data['independence'] + gov_data['ethics']) / 2
    final_score = (e_score * weights['E']) + (s_score * weights['S']) + (g_score * weights['G'])
    return final_score, e_score, s_score, g_score

def get_recommendations(e_score, s_score, g_score):
    recs = {'E': [], 'S': [], 'G': []}
    if e_score < 70: recs['E'].append("**High Impact:** Conduct a professional energy audit.")
    if e_score < 80: recs['E'].append("**Medium Impact:** Switch to LED lighting and optimize HVAC.")
    if e_score < 60: recs['E'].append("**Critical:** Develop a waste reduction strategy.")
    if s_score < 70: recs['S'].append("**High Impact:** Introduce an anonymous employee feedback system.")
    if s_score < 80: recs['S'].append("**Medium Impact:** Implement diversity training.")
    if s_score < 60: recs['S'].append("**Critical:** Review safety protocols immediately.")
    if g_score < 75: recs['G'].append("**High Impact:** Appoint an independent director.")
    if g_score < 85: recs['G'].append("**Medium Impact:** Update ethics policy.")
    
    if not recs['E']: recs['E'].append("Strong performance! Explore new green tech.")
    if not recs['S']: recs['S'].append("Excellent metrics! Focus on maintaining culture.")
    if not recs['G']: recs['G'].append("Solid governance. Maintain internal controls.")
    return recs

def get_financial_opportunities(esg_score):
    return [opp for opp in FINANCE_OPPORTUNITIES if esg_score >= opp['minimum_esg_score']]

def calculate_environmental_impact(env_data):
    energy_co2 = env_data.get('energy', 0) * CO2_EMISSION_FACTORS['energy_kwh_to_co2']
    water_co2 = env_data.get('water', 0) * CO2_EMISSION_FACTORS['water_m3_to_co2']
    waste_co2 = env_data.get('waste', 0) * CO2_EMISSION_FACTORS['waste_kg_to_co2']
    total_co2 = energy_co2 + water_co2 + waste_co2
    return {'total_co2_kg': total_co2, 'energy_co2_kg': energy_co2, 'water_co2_kg': water_co2, 'waste_co2_kg': waste_co2}

# --- DASHBOARD UI ---
def display_dashboard(final_score, e_score, s_score, g_score, env_data, social_data, gov_data, current_user_id):
    st.markdown("""
        <div class="welcome-banner" style="text-align:center; padding: 2rem 1rem; border-radius: 15px; background: linear-gradient(to right, #a5d6a7, #81d4fa); color: #003300; font-size: 2.5rem; font-weight: bold; margin-bottom: 20px;">
            🌿 Welcome to <span style="color: #1b5e20;">GreenInvest Analytics</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.header(f"Your ESG Performance Dashboard, {st.session_state.name}!") 

    # Animated Score
    col_score, col_blank = st.columns([1,3])
    with col_score:
        st.metric(label="Overall ESG Score", value=f"{final_score:.1f}", delta="out of 100")

    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Performance Overview", "🎯 Recommendations", "💰 Finance Marketplace", "🕰️ Trends", "🧪 Scenario Planner"])

    with tab1:
        col_e, col_s, col_g = st.columns(3)
        col_e.metric("🌳 Environmental", f"{e_score:.1f}")
        col_s.metric("❤️ Social", f"{s_score:.1f}")
        col_g.metric("⚖️ Governance", f"{g_score:.1f}")
        
        st.divider()
        impact = calculate_environmental_impact(env_data)
        st.info(f"Estimated Annual CO2 Emissions: **{impact['total_co2_kg']:.2f} kg**")

        c1, c2 = st.columns(2)
        with c1:
            fig_spider = go.Figure()
            fig_spider.add_trace(go.Scatterpolar(r=[e_score, s_score, g_score, e_score], theta=['Env', 'Soc', 'Gov', 'Env'], fill='toself', name='Your Score'))
            fig_spider.add_trace(go.Scatterpolar(r=[70, 65, 75, 70], theta=['Env', 'Soc', 'Gov', 'Env'], fill='none', name='Industry Avg', line_dash='dot'))
            fig_spider.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), title="Balanced Scorecard")
            st.plotly_chart(fig_spider, use_container_width=True)
        with c2:
            fig_bar = go.Figure(go.Bar(x=[e_score, s_score, g_score], y=['Env', 'Soc', 'Gov'], orientation='h', marker_color=['#4CAF50', '#8BC34A', '#CDDC39']))
            fig_bar.update_layout(title="Score Breakdown")
            st.plotly_chart(fig_bar, use_container_width=True)

    with tab2:
        recs = get_recommendations(e_score, s_score, g_score)
        c1, c2, c3 = st.columns(3)
        with c1: 
            st.subheader("Environmental")
            for r in recs['E']: st.write(f"- {r}")
        with c2: 
            st.subheader("Social")
            for r in recs['S']: st.write(f"- {r}")
        with c3: 
            st.subheader("Governance")
            for r in recs['G']: st.write(f"- {r}")

    with tab3:
        st.subheader("Unlocked Opportunities")
        opps = get_financial_opportunities(final_score)
        if not opps: st.warning("Improve your score to unlock financing.")
        for opp in opps:
            with st.container(border=True):
                st.write(f"**{opp['icon']} {opp['name']}** ({opp['type']})")
                st.write(opp['description'])

    with tab4:
        history = get_esg_history(current_user_id)
        if history:
            df_hist = pd.DataFrame(history)
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(x=df_hist['timestamp'], y=df_hist['overall_score'], mode='lines+markers', name='Overall'))
            st.plotly_chart(fig_line, use_container_width=True)
            st.dataframe(df_hist[['timestamp', 'overall_score', 'e_score', 's_score', 'g_score']])
        else:
            st.info("No history yet.")

    with tab5:
        st.write("Adjust metrics to see potential impact.")
        # Simplified scenario planner inputs
        sc_energy = st.number_input("Scenario Energy", value=env_data['energy'])
        sc_div = st.slider("Scenario Diversity", 0, 100, social_data['diversity'])
        
        # Recalculate based on simple scenario
        sc_env = env_data.copy(); sc_env['energy'] = sc_energy
        sc_soc = social_data.copy(); sc_soc['diversity'] = sc_div
        sc_score, _, _, _ = calculate_esg_score(sc_env, sc_soc, gov_data)
        st.metric("Projected Score", f"{sc_score:.1f}", delta=f"{sc_score - final_score:.1f}")

    # JSON Export
    report_data = {
        "User": st.session_state.username,
        "Date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "Scores": {"Overall": final_score, "E": e_score, "S": s_score, "G": g_score}
    }
    st.download_button("Download Report JSON", json.dumps(report_data, indent=2), "report.json", "application/json")


# --- AUTHENTICATION & MAIN FLOW ---

# Get credentials from database
credentials = get_all_users_for_authenticator()

# Initialize authenticator
authenticator = Authenticate(
    credentials,
    'greeninvest_cookie', 
    'abcdefgh_secret_key_change_me', 
    cookie_expiry_days=30
)

# Login Widget
name, authentication_status, username = authenticator.login(location='main')

if st.session_state["authentication_status"]:
    # --- LOGGED IN USER VIEW ---
    st.session_state.username = username
    st.session_state.name = name
    st.session_state.user_id = get_user_id(username)
    
    authenticator.logout('Logout', location='sidebar')
    
    st.sidebar.header("Data Input")
    input_method = st.sidebar.radio("Method:", ("Manual Input", "Upload CSV"))

    # Template CSV generator
    @st.cache_data
    def get_template_csv():
        data = {
            'metric': ['energy_consumption_kwh', 'water_usage_m3', 'waste_generation_kg', 'recycling_rate_pct',
                       'employee_turnover_pct', 'safety_incidents_count', 'management_diversity_pct',
                       'board_independence_pct', 'ethics_training_pct'],
            'value': [50000, 2500, 1000, 40, 15, 3, 30, 50, 85]
        }
        return pd.DataFrame(data).to_csv(index=False).encode('utf-8')

    if input_method == "Manual Input":
        # Load last data or defaults
        if 'last_env' not in st.session_state:
            hist = get_esg_history(st.session_state.user_id)
            if hist:
                last = hist[-1]
                st.session_state.last_env = last['env_data']
                st.session_state.last_soc = last['social_data']
                st.session_state.last_gov = last['gov_data']
            else:
                st.session_state.last_env = {'energy': 50000, 'water': 2500, 'waste': 1000, 'recycling': 40}
                st.session_state.last_soc = {'turnover': 15, 'incidents': 3, 'diversity': 30}
                st.session_state.last_gov = {'independence': 50, 'ethics': 85}

        with st.sidebar.expander("Environmental", expanded=True):
            en = st.number_input("Energy (kWh)", value=st.session_state.last_env['energy'])
            wa = st.number_input("Water (m3)", value=st.session_state.last_env['water'])
            ws = st.number_input("Waste (kg)", value=st.session_state.last_env['waste'])
            re = st.slider("Recycling (%)", 0, 100, value=st.session_state.last_env['recycling'])
        
        with st.sidebar.expander("Social", expanded=True):
            tu = st.slider("Turnover (%)", 0, 100, value=st.session_state.last_soc['turnover'])
            inc = st.number_input("Incidents", value=st.session_state.last_soc['incidents'])
            div = st.slider("Diversity (%)", 0, 100, value=st.session_state.last_soc['diversity'])

        with st.sidebar.expander("Governance", expanded=True):
            ind = st.slider("Board Indep (%)", 0, 100, value=st.session_state.last_gov['independence'])
            eth = st.slider("Ethics Train (%)", 0, 100, value=st.session_state.last_gov['ethics'])

        if st.sidebar.button("Calculate Score", type="primary"):
            env_d = {'energy': en, 'water': wa, 'waste': ws, 'recycling': re}
            soc_d = {'turnover': tu, 'incidents': inc, 'diversity': div}
            gov_d = {'independence': ind, 'ethics': eth}
            
            # Update session
            st.session_state.last_env = env_d
            st.session_state.last_soc = soc_d
            st.session_state.last_gov = gov_d
            
            final, e, s, g = calculate_esg_score(env_d, soc_d, gov_d)
            save_esg_history(st.session_state.user_id, datetime.datetime.now().isoformat(), final, e, s, g, env_d, soc_d, gov_d)
            display_dashboard(final, e, s, g, env_d, soc_d, gov_d, st.session_state.user_id)

    else: # CSV Upload
        st.sidebar.download_button("Download Template", get_template_csv(), "template.csv", "text/csv")
        uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                def get_val(m): 
                    v = df.loc[df['metric'] == m, 'value']
                    return float(v.values[0]) if not v.empty else 0

                env_d = {'energy': get_val('energy_consumption_kwh'), 'water': get_val('water_usage_m3'), 
                         'waste': get_val('waste_generation_kg'), 'recycling': get_val('recycling_rate_pct')}
                soc_d = {'turnover': get_val('employee_turnover_pct'), 'incidents': get_val('safety_incidents_count'), 
                         'diversity': get_val('management_diversity_pct')}
                gov_d = {'independence': get_val('board_independence_pct'), 'ethics': get_val('ethics_training_pct')}
                
                final, e, s, g = calculate_esg_score(env_d, soc_d, gov_d)
                st.success("CSV Processed!")
                
                if st.button("Generate Dashboard"):
                    save_esg_history(st.session_state.user_id, datetime.datetime.now().isoformat(), final, e, s, g, env_d, soc_d, gov_d)
                    display_dashboard(final, e, s, g, env_d, soc_d, gov_d, st.session_state.user_id)
            except Exception as e:
                st.error(f"Error parsing CSV: {e}")

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
    
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')

    # --- REGISTRATION FORM ---
    st.divider()
    st.markdown("### 🌱 New to GreenInvest? Create an Account")
    
    with st.expander("Register New Account", expanded=False):
        with st.form("registration_form"):
            new_name = st.text_input("Full Name")
            new_username = st.text_input("Choose a Username")
            new_password = st.text_input("Choose a Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            submit_registration = st.form_submit_button("Register")
            
            if submit_registration:
                if new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif len(new_password) < 4:
                    st.error("Password must be at least 4 characters.")
                elif not new_username or not new_name:
                    st.error("Please fill in all fields.")
                else:
                    # Generate bcrypt hash
                    hashed_pass = Hasher([new_password]).generate()[0]
                    success = add_user(new_username, hashed_pass, new_name)
                    
                    if success:
                        st.success("🎉 Account created! Please log in above.")
                    else:
                        st.error("Username already exists.")

