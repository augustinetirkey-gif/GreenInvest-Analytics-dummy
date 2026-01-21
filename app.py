import streamlit as st
import pandas as pd
import plotly.graph_objects as go
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
    page_title="GreenInvest Analytics",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
    <style>
        /* Enhanced Banner Animation */
        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .welcome-banner {
            animation: slideDown 0.8s ease-out;
            background: linear-gradient(135deg, #2e7d32 0%, #66bb6a 100%);
            color: white;
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        .banner-title { font-size: 2.5rem; font-weight: bold; margin-bottom: 0.5rem; }
        .banner-subtitle { font-size: 1.2rem; opacity: 0.9; }

        /* General Styling */
        .stApp { background-color: #f4f9f4; }
        .metric-card {
            background-color: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE FUNCTIONS ---
DATABASE_NAME = 'esg_data.db'

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS esg_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, timestamp TEXT NOT NULL, overall_score REAL, e_score REAL, s_score REAL, g_score REAL, env_data TEXT, social_data TEXT, gov_data TEXT, FOREIGN KEY (user_id) REFERENCES users (id))''')
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

def save_esg_history(user_id, timestamp, overall, e, s, g, env, soc, gov):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO esg_history (user_id, timestamp, overall_score, e_score, s_score, g_score, env_data, social_data, gov_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (user_id, timestamp, overall, e, s, g, json.dumps(env), json.dumps(soc), json.dumps(gov)))
    conn.commit()
    conn.close()

def get_esg_history(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT timestamp, overall_score, e_score, s_score, g_score, env_data, social_data, gov_data FROM esg_history WHERE user_id = ? ORDER BY timestamp ASC", (user_id,))
    data = c.fetchall()
    conn.close()
    return [{'timestamp': pd.to_datetime(r[0]), 'overall_score': r[1], 'e_score': r[2], 's_score': r[3], 'g_score': r[4], 
             'env_data': json.loads(r[5]), 'social_data': json.loads(r[6]), 'gov_data': json.loads(r[7])} for r in data]

def get_all_users_for_authenticator():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT name, username, password_hash FROM users")
    data = c.fetchall()
    conn.close()
    return {"usernames": {r[1]: {"name": r[0], "password": r[2]} for r in data}}

init_db()

# --- CALCULATION LOGIC ---
def calculate_esg_score(env, soc, gov):
    # Weights
    w_e, w_s, w_g = 0.4, 0.3, 0.3
    
    # Logic with explanation: Lower usage = Higher score
    e_energy_score = max(0, 100 - (env['energy']/1000))
    e_water_score = max(0, 100 - (env['water']/500))
    e_waste_score = max(0, 100 - (env['waste']/100))
    e_recycle_score = env['recycling'] # Direct percentage
    
    e = (e_energy_score + e_water_score + e_waste_score + e_recycle_score) / 4

    s_turnover_score = max(0, 100 - (soc['turnover']*2)) # Lower turnover is better
    s_incidents_score = max(0, 100 - (soc['incidents']*10)) # Fewer incidents is better
    s_diversity_score = soc['diversity'] # Higher is better
    
    s = (s_turnover_score + s_incidents_score + s_diversity_score) / 3

    g_indep_score = gov['independence'] # Higher is better
    g_ethics_score = gov['ethics'] # Higher is better
    
    g = (g_indep_score + g_ethics_score) / 2
    
    final = (e * w_e) + (s * w_s) + (g * w_g)
    
    # Return scores AND breakdown for explanation
    details = {
        "E": {"Energy": e_energy_score, "Water": e_water_score, "Waste": e_waste_score, "Recycling": e_recycle_score},
        "S": {"Turnover": s_turnover_score, "Safety": s_incidents_score, "Diversity": s_diversity_score},
        "G": {"Independence": g_indep_score, "Ethics": g_ethics_score}
    }
    
    return final, e, s, g, details

# --- VISUALIZATION HELPERS ---
def create_gauge(value, title, color):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        title = {'text': title},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 50], 'color': "#ffebee"},
                {'range': [50, 80], 'color': "#fff3e0"},
                {'range': [80, 100], 'color': "#e8f5e9"}],
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
    return fig

# --- AUTHENTICATION SETUP ---
credentials = get_all_users_for_authenticator()

authenticator = stauth.Authenticate(
    credentials,
    'greeninvest_cookie',
    'random_secret_key_123',
    cookie_expiry_days=30
)

# Login handling
authenticator.login(location='main')

if st.session_state["authentication_status"]:
    # LOGGED IN
    username = st.session_state["username"]
    name = st.session_state["name"]
    st.session_state.user_id = get_user_id(username)
    st.session_state.name = name
    authenticator.logout('Logout', 'sidebar')

    # --- 1. ENHANCED WELCOME BANNER ---
    st.markdown(f"""
        <div class="welcome-banner">
            <div class="banner-title">🌿 GreenInvest Analytics</div>
            <div class="banner-subtitle">Welcome back, {name}! Let's measure your impact.</div>
        </div>
    """, unsafe_allow_html=True)

    # Input Selection
    method = st.sidebar.radio("Input Method", ["Manual", "Upload CSV"])
    
    def get_csv():
        d = {'metric': ['energy_consumption_kwh', 'water_usage_m3', 'waste_generation_kg', 'recycling_rate_pct', 'employee_turnover_pct', 'safety_incidents_count', 'management_diversity_pct', 'board_independence_pct', 'ethics_training_pct'],
             'value': [50000, 2500, 1000, 40, 15, 3, 30, 50, 85]}
        return pd.DataFrame(d).to_csv(index=False).encode('utf-8')

    env_d, soc_d, gov_d = {}, {}, {}
    calc_triggered = False

    if method == "Manual":
        with st.sidebar.form("input_form"):
            st.subheader("Environmental")
            e1 = st.number_input("Energy (kWh)", 50000)
            e2 = st.number_input("Water (m3)", 2500)
            e3 = st.number_input("Waste (kg)", 1000)
            e4 = st.slider("Recycling (%)", 0, 100, 40)
            st.subheader("Social")
            s1 = st.slider("Turnover (%)", 0, 100, 15)
            s2 = st.number_input("Incidents", 0)
            s3 = st.slider("Diversity (%)", 0, 100, 30)
            st.subheader("Governance")
            g1 = st.slider("Board Indep (%)", 0, 100, 50)
            g2 = st.slider("Ethics Train (%)", 0, 100, 85)
            if st.form_submit_button("Calculate Score"):
                env_d = {'energy': e1, 'water': e2, 'waste': e3, 'recycling': e4}
                soc_d = {'turnover': s1, 'incidents': s2, 'diversity': s3}
                gov_d = {'independence': g1, 'ethics': g2}
                calc_triggered = True
    else:
        st.sidebar.download_button("Download Template", get_csv(), "template.csv")
        up = st.sidebar.file_uploader("Upload CSV", type=['csv'])
        if up:
            try:
                df = pd.read_csv(up)
                get = lambda m: float(df.loc[df['metric']==m, 'value'].values[0])
                env_d = {'energy': get('energy_consumption_kwh'), 'water': get('water_usage_m3'), 'waste': get('waste_generation_kg'), 'recycling': get('recycling_rate_pct')}
                soc_d = {'turnover': get('employee_turnover_pct'), 'incidents': get('safety_incidents_count'), 'diversity': get('management_diversity_pct')}
                gov_d = {'independence': get('board_independence_pct'), 'ethics': get('ethics_training_pct')}
                if st.sidebar.button("Process CSV"):
                    calc_triggered = True
            except Exception as e:
                st.error(f"Error processing CSV: {e}")

    if calc_triggered:
        final, e, s, g, details = calculate_esg_score(env_d, soc_d, gov_d)
        save_esg_history(st.session_state.user_id, datetime.datetime.now().isoformat(), final, e, s, g, env_d, soc_d, gov_d)
        
        # --- 2. GAUGE CHARTS (Visual Understanding) ---
        st.subheader("📊 Score Dashboard")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.plotly_chart(create_gauge(final, "Overall ESG", "#1b5e20"), use_container_width=True)
        with col2:
            st.plotly_chart(create_gauge(e, "Environmental", "#4caf50"), use_container_width=True)
        with col3:
            st.plotly_chart(create_gauge(s, "Social", "#2196f3"), use_container_width=True)
        with col4:
            st.plotly_chart(create_gauge(g, "Governance", "#ff9800"), use_container_width=True)

        # --- 3. EXPLAINER SECTION (Detailed Breakdown) ---
        st.divider()
        st.subheader("🔍 Why did I get this score?")
        st.write("Here is the breakdown of how your inputs translated into scores (0-100 scale):")
        
        exp_col1, exp_col2, exp_col3 = st.columns(3)
        
        with exp_col1:
            st.info("**Environmental Factors**")
            
            for key, val in details['E'].items():
                icon = "✅" if val > 70 else "⚠️" if val > 40 else "❌"
                st.write(f"{icon} **{key}:** {val:.1f}")
            st.caption("*Based on energy, water, and waste efficiency.*")

        with exp_col2:
            st.info("**Social Factors**")
            
            for key, val in details['S'].items():
                icon = "✅" if val > 70 else "⚠️" if val > 40 else "❌"
                st.write(f"{icon} **{key}:** {val:.1f}")
            st.caption("*Based on turnover, safety, and diversity.*")

        with exp_col3:
            st.info("**Governance Factors**")
            
            for key, val in details['G'].items():
                icon = "✅" if val > 70 else "⚠️" if val > 40 else "❌"
                st.write(f"{icon} **{key}:** {val:.1f}")
            st.caption("*Based on board independence and ethics.*")

        # History Chart
        hist = get_esg_history(st.session_state.user_id)
        if hist:
            st.divider()
            st.subheader("📈 Performance Trend")
            hf = pd.DataFrame(hist)
            fig = go.Figure(go.Scatter(x=hf['timestamp'], y=hf['overall_score'], mode='lines+markers', line=dict(color='#2e7d32', width=3)))
            fig.update_layout(title="Your Improvement Over Time", height=300)
            st.plotly_chart(fig, use_container_width=True)

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')
    
    st.divider()
    with st.expander("Register New Account"):
        with st.form("reg"):
            n = st.text_input("Name")
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Register"):
                if u and p and len(p) > 3:
                    try:
                        hashed_bytes = bcrypt.hashpw(p.encode('utf-8'), bcrypt.gensalt())
                        hashed_str = hashed_bytes.decode('utf-8')
                        if add_user(u, hashed_str, n):
                            st.success("Registered! Please login above.")
                        else:
                            st.error("Username already taken.")
                    except Exception as e:
                        st.error(f"Error creating account: {e}")
                else:
                    st.error("Invalid details.")
