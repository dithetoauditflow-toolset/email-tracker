"""
Login page for authentication
"""
import streamlit as st
from data.db_manager import DatabaseManager
from auth.session_manager import login_user, init_session


def show_login_page():
    """Display login page"""
    init_session()
    
    st.title("🔐 Email Follow-Up Audit Tool")
    st.subheader("Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if not username or not password:
                st.error("Please enter both username and password")
                return
            
            # Verify credentials
            db = DatabaseManager()
            user = db.verify_user(username, password)
            
            if user:
                login_user(user)
                st.success(f"Welcome, {username}!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    # First-time setup instructions
    with st.expander("ℹ️ First Time Setup"):
        st.info("""
        **For Administrators:**
        
        If this is the first time running the application, you need to create an admin account.
        
        Run the following in your terminal:
        ```python
        python -c "from data.db_manager import DatabaseManager; db = DatabaseManager(); db.create_admin('admin', 'your_password')"
        ```
        
        Then login with those credentials.
        """)
