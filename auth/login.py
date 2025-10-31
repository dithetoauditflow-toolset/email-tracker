"""
Login page for authentication
"""
import streamlit as st
import sqlite3
from data.db_manager import DatabaseManager
from auth.session_manager import login_user, init_session
from config import MAIN_DB_PATH


def show_login_page():
    """Display login page"""
    init_session()
    
    st.title("🔐 Email Follow-Up Audit Tool")
    st.subheader("Login")

    # Bootstrap admin on first run (Cloud-friendly): create admin from secrets if none exists
    try:
        # Ensure database and tables are initialized
        _db_init = DatabaseManager()
        conn = sqlite3.connect(MAIN_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cur.fetchone()[0]
        conn.close()

        admin_user = st.secrets.get("admin_username", None)
        admin_pass = st.secrets.get("admin_password", None)
        force_reset = bool(st.secrets.get("force_reset_admin", False))

        if admin_count == 0:
            if admin_user and admin_pass:
                dbb = DatabaseManager()
                created = dbb.create_admin(admin_user, admin_pass)
                if created:
                    st.success(f"Bootstrap admin created: {admin_user}")
                else:
                    st.info("Admin already initialized.")
            else:
                st.warning(
                    "No admin account found. Set 'admin_username' and 'admin_password' in Streamlit Secrets to bootstrap the first admin."
                )
        else:
            # Optional: force reset admin password if requested via secrets
            if force_reset and admin_user and admin_pass:
                try:
                    conn = sqlite3.connect(MAIN_DB_PATH)
                    cur = conn.cursor()
                    row = cur.execute("SELECT id FROM users WHERE username = ? AND role = 'admin'", (admin_user,)).fetchone()
                    if row:
                        db = DatabaseManager()
                        if db.update_user_password(int(row[0]), admin_pass):
                            st.success("Admin password reset from secrets.")
                        else:
                            st.warning("Failed to reset admin password.")
                    else:
                        # Create a new admin with that username if not found
                        db = DatabaseManager()
                        if db.create_admin(admin_user, admin_pass):
                            st.success(f"Admin '{admin_user}' created from secrets.")
                        else:
                            st.warning("Could not create admin from secrets.")
                    conn.close()
                except Exception:
                    pass
    except Exception:
        pass
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            username = (username or "").strip()
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

    # Optional debug panel (only when enabled via secrets)
    try:
        if bool(st.secrets.get("debug_auth", False)):
            with st.expander("🔎 Debug: Authentication State"):
                try:
                    conn = sqlite3.connect(MAIN_DB_PATH)
                    cur = conn.cursor()
                    total_users = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                    admins = cur.execute("SELECT username FROM users WHERE role = 'admin'").fetchall()
                    sample = cur.execute("SELECT username, role, created_at FROM users LIMIT 10").fetchall()
                    st.write({
                        "total_users": total_users,
                        "admins": [r[0] for r in admins],
                        "sample_users": sample,
                    })
                    # Check if the typed username exists
                    if 'login_form' in st.session_state:
                        pass
                    exists_row = cur.execute("SELECT id, role FROM users WHERE username = ?", (st.session_state.get('username', username or ''),)).fetchone()
                    st.write({"typed_username": (st.session_state.get('username', username or '')), "exists": bool(exists_row), "role": exists_row[1] if exists_row else None})
                    conn.close()
                except Exception as e:
                    st.write({"debug_error": str(e)})
    except Exception:
        pass
    
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
