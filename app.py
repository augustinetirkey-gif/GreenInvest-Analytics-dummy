import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
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
    page_title="GreenInvest Analytics Pro",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS (Hero Banner & Cards) ---
st.markdown("""
    <style>
        /* HERO BANNER */
        .hero-container {
            background-image: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), url('https://images.unsplash.com/photo-1473448912268-2022ce9509d8?q=80&w=2641&auto=format&fit=crop');
            background-size: cover;
            background-position: center;
            padding: 4rem 2rem;
            border-radius: 20px;
            color: white;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .hero-title {
            font-size: 3.5rem;
            font-weight: 800;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        .hero-subtitle {
            font-size: 1.5rem;
            font-weight: 300;
            opacity: 0.9;
        }

        /* METRIC CARDS */
        div[data-testid="metric-container"] {
            background-color: #ffffff;
            border: 1px solid #f0f2f6;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            transition: transform 0.2s;
        }
        div[data-testid="metric-container"]:hover {
            transform: translateY(-5px);
            border-color: #4caf50;
        }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE FUNCTIONS ---
DATABASE_NAME = 'esg_data_v3.db' 

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS esg_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, timestamp TEXT NOT NULL, overall_score REAL, e_score REAL, s_score REAL, g_score REAL, env_data TEXT, social_data TEXT, gov_data TEXT, industry TEXT, FOREIGN KEY (user_id) REFERENCES users (id))''')
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

def save_esg_history(user_id, timestamp, overall, e, s, g, env, soc, gov, industry):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO esg_history (user_id, timestamp, overall_score, e_score, s_score, g_score, env_data, social_data, gov_data, industry) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (user_id, timestamp, overall, e, s, g, json.dumps(env), json.dumps(soc), json.dumps(gov), industry))
    conn.commit()
    conn.close()

def get_esg_history(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT timestamp, overall_score, e_score, s_score, g_score, env_data, social_data, gov_data, industry FROM esg_history WHERE user_id = ? ORDER BY timestamp ASC", (user_id,))
    data = c.fetchall()
    conn.close()
    return [{'timestamp': pd.to_datetime(r[0]), 'overall_score': r[1], 'e_score': r[2], 's_score': r[3], 'g_score': r[4], 
             'env_data': json.loads(r[5]), 'social_data': json.loads(r[6]), 'gov_data': json.loads(r[7]), 'industry': r[8]} for r in data]

def get_all_users_for_authenticator():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT name, username, password_hash FROM users")
    data = c.fetchall()
    conn.close()
    return {"usernames": {r[1]: {"name": r[0], "password": r[2]} for r in data}}

init_db()

# --- ADVANCED CALCULATION LOGIC ---
def calculate_esg_score(env, soc, gov, industry):
    # Dynamic weights based on Industry
    weights = {'E': 0.33, 'S': 0.33, 'G': 0.33}
    if industry == "Manufacturing": weights = {'E': 0.5, 'S': 0.3, 'G': 0.2}
    elif industry == "Technology": weights = {'E': 0.2, 'S': 0.4, 'G': 0.4}
    elif industry == "Finance": weights = {'E': 0.1, 'S': 0.4, 'G': 0.5}

    # --- Environmental Calculation (5 Metrics) ---
    e1 = max(0, 100 - (env['energy'] / 1000))  # Energy (lower better)
    e2 = max(0, 100 - (env['water'] / 500))    # Water (lower better)
    e3 = env['recycling']                      # Recycling % (higher better)
    e4 = min(100, env['renewable'] * 2)        # Renewable % (higher better)
    e5 = min(100, env['offsets'] / 10)         # Carbon Offsets (higher better)
    e_score = (e1 + e2 + e3 + e4 + e5) / 5

    # --- Social Calculation (
