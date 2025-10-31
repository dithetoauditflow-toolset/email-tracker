"""
Session management for Streamlit authentication
"""
import streamlit as st
from typing import Optional, Dict


def init_session():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'role' not in st.session_state:
        st.session_state.role = None


def login_user(user_data: Dict):
    """Set session state for logged-in user"""
    st.session_state.authenticated = True
    st.session_state.user = user_data
    st.session_state.user_id = user_data['id']
    st.session_state.username = user_data['username']
    st.session_state.role = user_data['role']


def logout_user():
    """Clear session state"""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.role = None


def is_authenticated() -> bool:
    """Check if user is authenticated"""
    return st.session_state.get('authenticated', False)


def get_current_user() -> Optional[Dict]:
    """Get current user data"""
    return st.session_state.get('user', None)


def is_admin() -> bool:
    """Check if current user is admin"""
    return st.session_state.get('role', None) == 'admin'


def is_auditor() -> bool:
    """Check if current user is auditor"""
    return st.session_state.get('role', None) == 'auditor'
