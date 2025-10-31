"""
Main entry point for the Email Follow-Up Audit Tool
Handles routing between login, admin panel, and auditor dashboard
"""
import streamlit as st
from auth.login import show_login_page
from auth.session_manager import init_session, is_authenticated, is_admin, logout_user
from ui.admin_panel import show_admin_panel
from ui.auditor_dashboard import show_auditor_dashboard
from config import APP_TITLE


# Page configuration
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    """Main application logic"""
    init_session()
    
    # Check authentication
    if not is_authenticated():
        show_login_page()
        return
    
    # Sidebar
    with st.sidebar:
        st.title("📧 Audit Tracker")
        st.write(f"**User:** {st.session_state.username}")
        st.write(f"**Role:** {st.session_state.role.title()}")
        
        st.divider()
        
        # Navigation based on role
        if is_admin():
            page = st.radio(
                "Navigation",
                ["Admin Panel"],
                label_visibility="collapsed"
            )
        else:
            page = st.radio(
                "Navigation",
                ["Dashboard"],
                label_visibility="collapsed"
            )
        
        st.divider()
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.rerun()
        
        # Footer
        st.caption("---")
        st.caption("Email Follow-Up Audit Tool v1.0")
        st.caption("Built for Ditheto Accountants")
    
    # Main content area
    if is_admin():
        show_admin_panel()
    else:
        show_auditor_dashboard()


if __name__ == "__main__":
    main()
