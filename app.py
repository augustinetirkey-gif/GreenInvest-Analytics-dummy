import streamlit as st
import pandas as pd
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

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="GreenInvest Basic",
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
        .hero-subtitle { font-size: 1.2rem; opacity: 0.9; margin-top: 0.5rem; font-weight: 300; }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
DB_FILE = 'esg_basic.db'

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

# --- CALCULATION ENGINE (SIMPLIFIED) ---
def calculate_scores(inputs):
    # 1. Environmental Logic (Removed Offsets)
    # Average of 4 inputs
    e_raw = ((max(0, 100 - inputs['energy']/1000)) + (max(0, 100 - inputs['water']/500)) + (inputs['recycling']) + (inputs['renewable'] * 1.5)) / 4
    e_score = min(100, max(0, e_raw))

    # 2. Social Logic (Unchanged)
    s_raw = ((max(0, 100 - inputs['turnover']*2)) + (max(0, 100 - inputs['incidents']*10)) + (inputs['diversity']) + (inputs['training'] * 2) + (inputs['charity'] * 10)) / 5
    s_score = min(100, max(0, s_raw))

    # 3. Governance Logic (Simplified: Only Board & Ethics)
    g_raw = (inputs['board'] + inputs['ethics']) / 2
    g_score = min(100, max(0, g_raw))

    # 4. Final Calculation (Equal Weighting, No Industry)
    final = (e_score + s_score + g_score) / 3
    return final, e_score, s_score, g_score

# --- AUTHENTICATION FLOW ---
credentials = get_credentials()
authenticator = stauth.Authenticate(credentials, 'green_cookie_basic', 'secure_key_basic', cookie_expiry_days=1)
authenticator.login(location='main')

if st.session_state["authentication_status"]:
    # === LOGGED IN ===
    username = st.session_state["username"]
    name = st.session_state["name"]
    authenticator.logout('Logout', 'sidebar')

    # Hero Banner
    st.markdown(f"""
        <div class="hero-section">
            <h1 class="hero-title">GreenInvest Basic</h1>
            <p class="hero-subtitle">Welcome, {name}. Simple ESG Scoring.</p>
        </div>
    """, unsafe_allow_html=True)

    # --- SIDEBAR INPUTS ---
    st.sidebar.header("🛠️ Data Input Panel")
    input_method = st.sidebar.radio("Choose Input Method:", ["Manual Entry", "Upload CSV"])
    
    inputs = {}
    calc_triggered = False

    # 1. MANUAL INPUT
    if input_method == "Manual Entry":
        with st.sidebar.form("manual_form"):
            with st.expander("🌳 Environmental", expanded=True):
                e1 = st.number_input("Energy (kWh)", 50000)
                e2 = st.number_input("Water (m3)", 2000)
                e3 = st.slider("Recycling Rate (%)", 0, 100, 40)
                e4 = st.slider("Renewable Energy (%)", 0, 100, 20)
                # Removed Carbon Offsets
            with st.expander("🤝 Social"):
                s1 = st.slider("Turnover Rate (%)", 0, 100, 15)
                s2 = st.number_input("Safety Incidents", 0)
                s3 = st.slider("Diversity (%)", 0, 100, 30)
                s4 = st.number_input("Training Hours", 20)
                s5 = st.slider("Charity (%)", 0, 20, 1)
            with st.expander("⚖️ Governance"):
                g1 = st.slider("Board Independence (%)", 0, 100, 60)
                g2 = st.slider("Ethics Compliance (%)", 0, 100, 95)
                # Removed Whistleblower, Privacy, Audit checkboxes
            if st.form_submit_button("🚀 Calculate Score"):
                inputs = {'energy':e1, 'water':e2, 'recycling':e3, 'renewable':e4,
                          'turnover':s1, 'incidents':s2, 'diversity':s3, 'training':s4, 'charity':s5,
                          'board':g1, 'ethics':g2}
                calc_triggered = True

    # 2. CSV UPLOAD
    else:
        # Create Template (Simplified)
        template = pd.DataFrame({'energy': [50000], 'water': [2000], 'recycling': [40], 'renewable': [20],
                                 'turnover': [15], 'incidents': [0], 'diversity': [30], 'training': [20], 'charity': [1],
                                 'board': [60], 'ethics': [95]})
        st.sidebar.download_button("Download Template CSV", template.to_csv(index=False), "esg_basic_template.csv")
        
        uploaded_file = st.sidebar.file_uploader("Upload CSV", type=['csv'])
        if uploaded_file and st.sidebar.button("Process CSV"):
            try:
                df = pd.read_csv(uploaded_file)
                # Handle case sensitivity
                df.columns = df.columns.str.lower().str.strip()
                inputs = df.iloc[0].to_dict()
                calc_triggered = True
            except Exception as e:
                st.error(f"Error reading CSV: {e}")

    # --- MAIN DISPLAY (SIMPLIFIED) ---
    if calc_triggered:
        final, e, s, g = calculate_scores(inputs)
        save_data(username, final, e, s, g, inputs)

        st.subheader("Results Overview")
        c1, c2, c3, c4 = st.columns(4)
        with c1: 
            st.metric("Overall Score", f"{final:.1f}/100")
        with c2: 
            st.metric("Environmental", f"{e:.1f}/100")
        with c3: 
            st.metric("Social", f"{s:.1f}/100")
        with c4: 
            st.metric("Governance", f"{g:.1f}/100")
        
        st.success(f"Score calculated successfully! Your overall ESG rating is **{final:.1f}**.")
        st.write("---")
        st.write("**Breakdown:**")
        st.json({"Environmental": e, "Social": s, "Governance": g})

    else:
        # Default Landing
        st.info("👈 Use the sidebar to input data manually or upload a CSV.")
        hist = get_history(username)
        if not hist.empty:
            st.divider()
            st.subheader("Your History Table")
            st.dataframe(hist)

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
