import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv

# Load master env configuration
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(script_dir, "../.env"))

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/chat")

st.set_page_config(
    page_title="Agentic RAG Security Sandbox",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
st.markdown("""
<style>
    /* Main Background & Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Header Styling */
    .header-container {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        padding: 2.5rem;
        border-radius: 16px;
        border: 1px solid #312e81;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }
    
    .header-container::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 60%);
        pointer-events: none;
    }
    
    .header-title {
        color: #f8fafc;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .header-subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        font-weight: 300;
    }
    
    /* Document Cards */
    .doc-card {
        background: #1e293b;
        border-radius: 12px;
        padding: 1.25rem;
        border: 1px solid #334155;
        margin-bottom: 1rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .doc-card:hover {
        transform: translateY(-2px);
        border-color: #6366f1;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.15);
    }
    
    .badge {
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        display: inline-block;
        margin-bottom: 8px;
    }
    
    .badge-public {
        background-color: rgba(16, 185, 129, 0.2);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .badge-private {
        background-color: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    /* Sidebar User Info Card */
    .user-profile-card {
        background: #0f172a;
        padding: 1.25rem;
        border-radius: 12px;
        border: 1px solid #1e293b;
        margin-top: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .profile-title {
        color: #94a3b8;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 12px;
        letter-spacing: 0.05em;
    }
    
    .profile-name {
        color: #f8fafc;
        font-size: 1.25rem;
        font-weight: 700;
        margin-bottom: 4px;
    }
    
    .profile-role-badge {
        background: linear-gradient(90deg, #6366f1 0%, #4338ca 100%);
        color: #ffffff;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin-top: 6px;
    }
    
    .profile-role-badge.admin {
        background: linear-gradient(90deg, #db2777 0%, #be185d 100%);
    }
</style>
""", unsafe_allow_html=True)

# Application Header
st.markdown("""
<div class="header-container">
    <div class="header-title">🛡️ Secure Agentic RAG Platform</div>
    <div class="header-subtitle">LangGraph multi-agent orchestration gated by Auth0 Fine-Grained Authorization (OpenFGA)</div>
</div>
""", unsafe_allow_html=True)

# Load Mock Users DB
mock_users_file = os.path.join(script_dir, "mock_users.json")
try:
    with open(mock_users_file, "r") as f:
        users_db = json.load(f)
except Exception as e:
    st.error(f"Error loading mock users database: {str(e)}")
    users_db = {}

# Sidebar Configuration
st.sidebar.markdown("<h3 style='margin-top:0;'>🔑 Identity & Access Management</h3>", unsafe_allow_html=True)
st.sidebar.caption("Simulate Enterprise Single Sign-On (SSO) to claim different Fine-Grained Authorization roles.")

selected_email = st.sidebar.selectbox("Select Active SSO Profile", list(users_db.keys()))
user_profile = users_db.get(selected_email, {"name": "Unknown", "role": "collaborator", "id": "user:guest"})

# Show User Profile Card in Sidebar
role_badge_class = "profile-role-badge admin" if user_profile["role"] == "admin" else "profile-role-badge"
st.sidebar.markdown(f"""
<div class="user-profile-card">
    <div class="profile-title">Active Session Identity</div>
    <div class="profile-name">{user_profile['name']}</div>
    <div style="color: #64748b; font-size: 0.9rem;">{selected_email}</div>
    <div class="{role_badge_class}">{user_profile['role'].upper()} ROLE CLAIM</div>
</div>
""", unsafe_allow_html=True)

# Show Authorization Policies Context in Sidebar
st.sidebar.markdown("### 📑 Policy Catalog")
st.sidebar.markdown(
    "<div class='doc-card'>"
    "<span class='badge badge-public'>Public Policy</span>"
    "<h4>grievance_policy.pdf</h4>"
    "<p style='font-size:0.85rem; color:#94a3b8; margin:0;'>Accessible by <b>Collaborator</b> & <b>Admin</b>. Rules for dispute resolution.</p>"
    "</div>", unsafe_allow_html=True
)
st.sidebar.markdown(
    "<div class='doc-card'>"
    "<span class='badge badge-public'>Public Policy</span>"
    "<h4>whistleblower_policy.pdf</h4>"
    "<p style='font-size:0.85rem; color:#94a3b8; margin:0;'>Accessible by <b>Collaborator</b> & <b>Admin</b>. Protection framework.</p>"
    "</div>", unsafe_allow_html=True
)
st.sidebar.markdown(
    "<div class='doc-card'>"
    "<span class='badge badge-public'>Public Policy</span>"
    "<h4>terms_and_conditions.pdf</h4>"
    "<p style='font-size:0.85rem; color:#94a3b8; margin:0;'>Accessible by <b>Collaborator</b> & <b>Admin</b>. Terms of service agreement.</p>"
    "</div>", unsafe_allow_html=True
)
st.sidebar.markdown(
    "<div class='doc-card'>"
    "<span class='badge badge-public'>Public Policy</span>"
    "<h4>service_guide.pdf</h4>"
    "<p style='font-size:0.85rem; color:#94a3b8; margin:0;'>Accessible by <b>Collaborator</b> & <b>Admin</b>. Operational service desk guidelines.</p>"
    "</div>", unsafe_allow_html=True
)
st.sidebar.markdown(
    "<div class='doc-card'>"
    "<span class='badge badge-private'>Restricted Document</span>"
    "<h4>chatbot_takehome_assignment.pdf</h4>"
    "<p style='font-size:0.85rem; color:#94a3b8; margin:0;'>Accessible by <b>Admin Only</b>. Confidential takehome assignment details.</p>"
    "</div>", unsafe_allow_html=True
)

# Chat Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []

# Clear chat if user changes profile to avoid cross-profile history leakage simulation
if "current_user_profile" not in st.session_state:
    st.session_state.current_user_profile = selected_email
elif st.session_state.current_user_profile != selected_email:
    st.session_state.messages = []
    st.session_state.current_user_profile = selected_email
    st.toast("Profile switched. Chat history cleared to prevent data leaks.")

# Main Chat View
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_input := st.chat_input("Query internal policy database..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
        
    payload = {
        "message": user_input,
        "user_id": user_profile["id"],
        "role": user_profile["role"]
    }
    
    with st.chat_message("assistant"):
        with st.spinner("Orchestrating agents (Retriever → Specialist → Reviewer)..."):
            try:
                res = requests.post(BACKEND_API_URL, json=payload)
                if res.status_code == 200:
                    answer = res.json()["response"]
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    st.error(f"Execution Failure (HTTP {res.status_code}): {res.text}")
            except Exception as e:
                st.error(f"Connection to backend API failed: {str(e)}")
                st.caption(f"Verify that backend service is running locally on: `{BACKEND_API_URL}`")
