import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import json
import sqlite3
import datetime
import streamlit_authenticator as stauth  # ✅ Corrected import

# --- Page Configuration ---
st.set_page_config(
    page_title="GreenInvest Analytics",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for animations and styling ---
st.markdown("""
    <style>
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .welcome-banner { animation: fadeInUp 1s ease-out; }

        .stApp {
            background: linear-gradient(to right, #f0fff0, #e6f5d0, #e0f7fa);
            animation: gradient 15s ease infinite;
            background-size: 400% 400%;
            color: #1b3a2f;
        }
        @keyframes gradient {
            0% {background-position: 0% 50%;}
            50% {background-position: 100% 50%;}
            100% {background-position: 0% 50%;}
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(to bottom, #2e7d32, #388e3c);
        }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] .stTabs [data-baseweb="tab"],
        section[data-testid="stSidebar"] .stTextInput label {
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT
        )
    ''')
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
    c.execute(
        "INSERT INTO esg_history (user_id, timestamp, overall_score, e_score, s_score, g_score, env_data, social_data, gov_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, timestamp, overall, e, s, g, json.dumps(env_data), json.dumps(social_data), json.dumps(gov_data))
    )
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

# Initialize DB
init_db()

# --- MOCK DATA AND FUNCTIONS ---
FINANCE_OPPORTUNITIES = [
    {"name": "GreenStart Grant Program", "type": "Grant", "description": "A grant for businesses starting their sustainability journey.", "minimum_esg_score": 0, "icon": "🌱", "url": "https://www.sba.gov/funding-programs/grants"},
    {"name": "Eco-Efficiency Business Loan", "type": "Loan", "description": "Low-interest loans for SMEs investing in energy-efficient equipment.", "minimum_esg_score": 60, "icon": "💡", "url": "https://www.bankofamerica.com/smallbusiness/business-financing/"},
    {"name": "Sustainable Supply Chain Fund", "type": "Venture Capital", "description": "Equity investment for companies demonstrating strong ESG performance.", "minimum_esg_score": 75, "icon": "🤝", "url": "https://www.blackrock.com/corporate/sustainability"},
    {"name": "Circular Economy Innovators Fund", "type": "Venture Capital", "description": "Seed funding for businesses pioneering waste reduction models.", "minimum_esg_score": 80, "icon": "♻️", "url": "https://www.closedlooppartners.com/"},
    {"name": "Impact Investors Alliance - Premier Partner", "type": "Private Equity", "description": "Top-tier ESG performers gain growth capital.", "minimum_esg_score": 90, "icon": "🏆", "url": "https://thegiin.org/"}
]

INDUSTRY_AVERAGES = {'Environmental': 70,'Social': 65,'Governance': 75,'Overall ESG': 70}
CO2_EMISSION_FACTORS = {'energy_kwh_to_co2': 0.4,'water_m3_to_co2': 0.1,'waste_kg_to_co2': 0.5}

def calculate_esg_score(env_data, social_data, gov_data):
    weights = {'E': 0.4, 'S': 0.3, 'G': 0.3}
    e_score = (max(0, 100 - (env_data['energy'] / 1000)) + max(0, 100 - (env_data['water'] / 500)) + max(0, 100 - (env_data['waste'] / 100)) + env_data['recycling']) / 4
    s_score = (max(0, 100 - (social_data['turnover'] * 2)) + max(0, 100 - (social_data['incidents'] * 10)) + social_data['diversity']) / 3
    g_score = (gov_data['independence'] + gov_data['ethics']) / 2
    final_score = (e_score * weights['E']) + (s_score * weights['S']) + (g_score * weights['G'])
    return final_score, e_score, s_score, g_score

def get_recommendations(e_score, s_score, g_score):
    recs = {'E': [], 'S': [], 'G': []}
    if e_score < 70: recs['E'].append("**High Impact:** Conduct an energy audit.")
    if e_score < 80: recs['E'].append("**Medium Impact:** Switch to LED lighting & optimize HVAC.")
    if e_score < 60: recs['E'].append("**Critical:** Develop waste reduction strategy.")

    if s_score < 70: recs['S'].append("**High Impact:** Implement anonymous employee feedback.")
    if s_score < 80: recs['S'].append("**Medium Impact:** Diversity & inclusion training.")
    if s_score < 60: recs['S'].append("**Critical:** Mandatory safety training sessions.")

    if g_score < 75: recs['G'].append("**High Impact:** Add an independent director to board.")
    if g_score < 85: recs['G'].append("**Medium Impact:** Update & communicate ethics policy.")
    if g_score < 65: recs['G'].append("**Critical:** Establish whistleblower policy & board accountability.")

    if not recs['E']: recs['E'].append("Strong performance! Explore new green technologies.")
    if not recs['S']: recs['S'].append("Excellent metrics! Maintain positive culture & well-being.")
    if not recs['G']: recs['G'].append("Solid governance. Stay updated with best practices.")
    return recs

def get_financial_opportunities(esg_score):
    return [opp for opp in FINANCE_OPPORTUNITIES if esg_score >= opp['minimum_esg_score']]

def calculate_environmental_impact(env_data):
    energy_co2 = env_data.get('energy',0) * CO2_EMISSION_FACTORS['energy_kwh_to_co2']
    water_co2 = env_data.get('water',0) * CO2_EMISSION_FACTORS['water_m3_to_co2']
    waste_co2 = env_data.get('waste',0) * CO2_EMISSION_FACTORS['waste_kg_to_co2']
    return {'total_co2_kg': energy_co2+water_co2+waste_co2,'energy_co2_kg': energy_co2,'water_co2_kg': water_co2,'waste_co2_kg': waste_co2}

# --- AUTHENTICATION SETUP ---
def get_all_users_for_authenticator():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT name, username, password_hash FROM users")
    users_data = c.fetchall()
    conn.close()
    credentials = {"usernames": {}}
    for name, username, password_hash in users_data:
        credentials["usernames"][username] = {"name": name, "password": password_hash}
    return credentials

credentials = get_all_users_for_authenticator()
authenticator = stauth.Authenticate(credentials,'greeninvest_cookie','abcdefgh',cookie_expiry_days=30)

# --- LOGIN ---
name, auth_status, username = authenticator.login(form_name='Login', location='main')

# --- MAIN APP LOGIC ---
if st.session_state.get("authentication_status"):
    st.session_state.username = username
    st.session_state.name = name
    st.session_state.user_id = get_user_id(username)
    authenticator.logout('Logout', location='sidebar')
    st.title("🌿 GreenInvest Analytics")
    st.markdown(f"Welcome back, **{st.session_state.name}**! Analyze your ESG performance and unlock green finance opportunities.")
    
    # --- THE REST OF YOUR SIDEBAR INPUT & DASHBOARD CODE ---
    st.info("Your full ESG input & dashboard code goes here...")  # You can paste the rest of the code here

elif auth_status is False:
    st.error("Username/password is incorrect. Please try again or register.")
elif auth_status is None:
    st.info("Please log in or register to access GreenInvest Analytics.")

