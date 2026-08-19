import streamlit as st
import requests
import json
import os
from datetime import datetime

# Configuration
BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="GitPro Backend Tester", page_icon="🚀", layout="wide")

# Session State Management
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user' not in st.session_state:
    st.session_state.user = None
if 'repos' not in st.session_state:
    st.session_state.repos = []
if 'current_repo' not in st.session_state:
    st.session_state.current_repo = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'session_id' not in st.session_state:
    st.session_state.session_id = None

def login(pat):
    try:
        response = requests.post(f"{BACKEND_URL}/api/dev/login", json={"token": pat})
        if response.status_code == 200:
            data = response.json()
            st.session_state.token = data['token']
            st.session_state.user = data['user']
            st.success(f"Logged in as {data['user']['username']}")
            st.rerun()
        else:
            st.error(f"Login failed: {response.text}")
    except Exception as e:
        st.error(f"Connection error: {e}")

def handle_api_error(response):
    if response.status_code == 401:
        st.error("Session expired. Please login again.")
        st.session_state.token = None
        st.session_state.user = None
        st.rerun()
    else:
        st.error(f"Error: {response.text}")

def fetch_repos():
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    try:
        response = requests.get(f"{BACKEND_URL}/api/repos", headers=headers)
        if response.status_code == 200:
            st.session_state.repos = response.json()
        else:
            handle_api_error(response)
    except Exception as e:
        st.error(f"Error: {e}")

def create_chat_session(repo_id):
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    data = {
        "user_id": st.session_state.user['id'],
        "repo_id": repo_id,
        "title": f"Chat about Repo {repo_id}"
    }
    try:
        response = requests.post(f"{BACKEND_URL}/api/chat/sessions", json=data, headers=headers)
        if response.status_code == 201:
            st.session_state.session_id = response.json()['session_id']
            st.session_state.chat_history = []
            st.success("Chat session created!")
        else:
            handle_api_error(response)
    except Exception as e:
        st.error(f"Error creating session: {e}")

def send_message(message):
    if not st.session_state.session_id:
        st.warning("No active chat session")
        return

    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    data = {
        "session_id": st.session_state.session_id,
        "message": message
    }
    
    # Add user message immediately
    st.session_state.chat_history.append({"role": "user", "content": message})
    
    try:
        response = requests.post(f"{BACKEND_URL}/api/chat/message", json=data, headers=headers)
        if response.status_code == 200:
            ai_response = response.json()['response']
            st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
            st.rerun()
        else:
            handle_api_error(response)
    except Exception as e:
        st.error(f"Error: {e}")

def analyze_repo(repo_id):
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    with st.spinner("Analyzing repository... this may take a minute"):
        try:
            response = requests.post(f"{BACKEND_URL}/api/repos/{repo_id}/analyze", headers=headers)
            if response.status_code == 200:
                st.success("Analysis complete!")
                return response.json()
            else:
                handle_api_error(response)
        except Exception as e:
            st.error(f"Error: {e}")
    return None

# UI Layout
st.title("🚀 GitPro Backend Tester")

if not st.session_state.token:
    st.header("Login")
    pat = st.text_input("Enter GitHub Personal Access Token (PAT)", type="password")
    if st.button("Connect"):
        if pat:
            login(pat)
        else:
            st.warning("Please enter a token")
else:
    # Sidebar: User & Repo Selection
    with st.sidebar:
        st.header(f"User: {st.session_state.user['username']}")
        if st.button("Logout"):
            st.session_state.token = None
            st.rerun()
        
        st.divider()
        st.subheader("Repositories")
        if st.button("Refresh List"):
            fetch_repos()
        
        if st.session_state.repos:
            for repo in st.session_state.repos:
                # Highlight selected repo
                label = repo['full_name']
                if st.session_state.current_repo and st.session_state.current_repo['id'] == repo['id']:
                    label = f"🔵 {label}"
                
                if st.button(label, key=f"repo_{repo['id']}"):
                    st.session_state.current_repo = repo
                    create_chat_session(repo['id'])
                    st.rerun()

    # Main Interface
    if st.session_state.current_repo:
        st.header(f"Context: {st.session_state.current_repo['name']}")
        st.caption(st.session_state.current_repo['description'])
        
        # Analysis Section (Collapsible or separate column)
        with st.expander("📊 Repository Analysis"):
            if st.button("Run Analysis"):
                analysis = analyze_repo(st.session_state.current_repo['id'])
                if analysis:
                    st.markdown(analysis['analysis'])
            elif st.session_state.current_repo.get('id') in [r.get('repo_id') for r in st.session_state.get('analyses', [])]:
                 # Retrieve cached analysis if we were storing it (simplified here)
                 pass

        st.divider()
        st.subheader("Chat")
        
        # Display Chat History
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        # Chat Input (Must be at main level)
        prompt = st.chat_input("Ask about this repository...")
        if prompt:
            send_message(prompt)
            
    else:
        st.info("👈 Please select a repository from the sidebar to start.")
