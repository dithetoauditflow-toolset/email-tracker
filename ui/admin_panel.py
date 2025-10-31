"""
Admin panel for managing auditors and settings
"""
import streamlit as st
import pandas as pd
import json
import sqlite3
from data.db_manager import DatabaseManager
from config import MAIN_DB_PATH


def show_admin_panel():
    """Display admin panel"""
    st.title("⚙️ Admin Panel")
    
    tab_overview, tab_manage, tab_settings = st.tabs(["📊 Overview", "👥 Manage Auditors", "🔧 Settings"])
    
    with tab_overview:
        show_overview()
    
    with tab_manage:
        show_auditor_management()
    
    with tab_settings:
        show_settings_management()


def show_auditor_management():
    """Manage auditor accounts"""
    st.subheader("Auditor Management")
    
    db = DatabaseManager()
    
    # Add new auditor
    with st.expander("➕ Add New Auditor"):
        with st.form("add_auditor_form"):
            full_name = st.text_input("Full Name")
            email = st.text_input("Email Address")
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            submit = st.form_submit_button("Create Auditor")
            
            if submit:
                if not full_name or not email or not new_username or not new_password:
                    st.error("Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    auditor_id = db.create_auditor(new_username, new_password, full_name=full_name, email=email)
                    if auditor_id:
                        st.success(f"✅ Auditor '{new_username}' created successfully (ID: {auditor_id})")
                        st.rerun()
                    else:
                        st.error("Username already exists")
    
    # List existing auditors
    st.write("### Existing Auditors")
    
    conn = sqlite3.connect(MAIN_DB_PATH)
    df_auditors = pd.read_sql_query(
        "SELECT id, username, full_name, email, created_at FROM users WHERE role = 'auditor' ORDER BY username",
        conn
    )
    conn.close()
    
    if len(df_auditors) > 0:
        for _, auditor in df_auditors.iterrows():
            col1, col2, col3, col4, col5 = st.columns([3, 2, 3, 3, 1])
            
            with col1:
                st.write(f"**{auditor['username']}** (ID: {auditor['id']})")
            
            with col2:
                st.write(f"Created: {pd.to_datetime(auditor['created_at']).strftime('%Y-%m-%d')}")
            
            with col3:
                name_val = st.text_input(
                    "Full Name",
                    value=str(auditor.get('full_name') or ''),
                    key=f"name_{auditor['id']}"
                )
                email_val = st.text_input(
                    "Email",
                    value=str(auditor.get('email') or ''),
                    key=f"email_{auditor['id']}"
                )
                if st.button("Save", key=f"save_{auditor['id']}"):
                    db = DatabaseManager()
                    if not name_val or not email_val:
                        st.error("Name and Email are required")
                    elif db.update_user_profile(int(auditor['id']), name_val, email_val):
                        st.success("Profile updated")
                        st.rerun()
                    else:
                        st.error("Failed to update profile")

            with col4:
                new_pw = st.text_input(
                    "New Password",
                    type="password",
                    key=f"pw_{auditor['id']}",
                    placeholder="Enter new password"
                )
                if st.button("Reset Password", key=f"reset_{auditor['id']}"):
                    if not new_pw or len(new_pw) < 6:
                        st.error("Password must be at least 6 characters")
                    else:
                        db = DatabaseManager()
                        if db.update_user_password(int(auditor['id']), new_pw):
                            st.success("Password updated")
                            st.rerun()
                        else:
                            st.error("Failed to update password")
            
            with col5:
                if st.button("🗑️", key=f"delete_{auditor['id']}"):
                    conn = sqlite3.connect(MAIN_DB_PATH)
                    conn.execute("DELETE FROM users WHERE id = ?", (auditor['id'],))
                    conn.commit()
                    conn.close()
                    
                    st.success(f"Deleted auditor: {auditor['username']}")
                    st.rerun()
            
            st.divider()
    else:
        st.info("No auditors yet")


def show_settings_management():
    """Manage application settings"""
    st.subheader("Application Settings")
    
    db = DatabaseManager()
    
    # Follow-up threshold
    st.write("### Follow-up Threshold")
    current_threshold = int(db.get_setting('followup_days') or 3)
    
    new_threshold = st.number_input(
        "Number of working days before marking as overdue",
        min_value=1,
        max_value=30,
        value=current_threshold
    )
    
    if st.button("Update Threshold"):
        db.update_setting('followup_days', str(new_threshold))
        st.success(f"✅ Threshold updated to {new_threshold} days")
        st.rerun()
    
    st.divider()
    
    # Internal domains
    st.write("### Internal Domains")
    st.caption("Emails between internal domains will be excluded from sync")
    
    current_domains_json = db.get_setting('internal_domains')
    current_domains = json.loads(current_domains_json) if current_domains_json else []
    
    # Display current domains
    domains_text = "\n".join(current_domains)
    new_domains_text = st.text_area(
        "Internal domains (one per line)",
        value=domains_text,
        height=150,
        placeholder="@company.com\n@subsidiary.com"
    )
    
    if st.button("Update Domains"):
        new_domains = [d.strip() for d in new_domains_text.split('\n') if d.strip()]
        db.update_setting('internal_domains', json.dumps(new_domains))
        st.success(f"✅ Updated {len(new_domains)} internal domains")
        st.rerun()


def show_overview():
    """Show system overview"""
    st.subheader("System Overview")
    
    db = DatabaseManager()
    conn = sqlite3.connect(MAIN_DB_PATH)
    
    # Count auditors
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'auditor'")
    auditor_count = cursor.fetchone()[0]
    
    conn.close()
    
    # Gather global and per-auditor stats
    conn = sqlite3.connect(MAIN_DB_PATH)
    auditors = pd.read_sql_query(
        "SELECT id, username FROM users WHERE role = 'auditor' ORDER BY username",
        conn
    )
    conn.close()

    total_companies = 0
    total_emails = 0
    total_sent_today = 0
    stats_data = []

    # Define 'today' in naive UTC for consistency
    now_naive_utc = pd.Timestamp.now(tz='UTC').tz_convert('UTC').tz_localize(None)
    today_date = now_naive_utc.date()

    for _, auditor in auditors.iterrows():
        auditor_db_path = db.get_auditor_db_path(auditor['id'])
        try:
            aconn = sqlite3.connect(auditor_db_path)
            # Companies
            comp_count = pd.read_sql_query("SELECT COUNT(*) AS c FROM companies", aconn).iloc[0]['c']
            # Emails
            email_count = pd.read_sql_query("SELECT COUNT(*) AS c FROM emails", aconn).iloc[0]['c']
            # Emails sent today (outgoing)
            df_em = pd.read_sql_query("SELECT direction, date FROM emails", aconn)
            sent_today = 0
            if len(df_em) > 0:
                ts = pd.to_datetime(df_em['date'], errors='coerce', utc=True)
                ts = ts.dt.tz_convert('UTC').dt.tz_localize(None)
                df_em = df_em.assign(_dt=ts)
                sent_today = int(df_em[(df_em['direction']=='outgoing') & (df_em['_dt'].dt.date == today_date)].shape[0])
            # Last sync
            last_sync_row = pd.read_sql_query("SELECT last_sync FROM sync_log WHERE id = 1", aconn)
            if len(last_sync_row) and pd.notna(last_sync_row.iloc[0]['last_sync']):
                try:
                    last_sync_disp = pd.to_datetime(last_sync_row.iloc[0]['last_sync']).strftime('%Y-%m-%d %H:%M')
                except Exception:
                    last_sync_disp = str(last_sync_row.iloc[0]['last_sync'])
            else:
                last_sync_disp = "Never"
            aconn.close()

            total_companies += int(comp_count)
            total_emails += int(email_count)
            total_sent_today += int(sent_today)

            stats_data.append({
                'Auditor': auditor['username'],
                'Companies': int(comp_count),
                'Emails': int(email_count),
                'Sent Today': int(sent_today),
                'Last Sync': last_sync_disp,
            })
        except Exception:
            stats_data.append({
                'Auditor': auditor['username'],
                'Companies': 0,
                'Emails': 0,
                'Sent Today': 0,
                'Last Sync': 'Error',
            })

    # Display top-level metrics
    st.write("### Global Stats")
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        st.metric("Total Auditors", int(auditor_count))
    with g2:
        st.metric("Total Companies", int(total_companies))
    with g3:
        st.metric("Total Emails", int(total_emails))
    with g4:
        st.metric("Emails Sent Today", int(total_sent_today))

    # Settings quick view
    st.caption(f"Follow-up Threshold: {db.get_setting('followup_days')} days")

    st.divider()

    # Per-auditor statistics table
    st.write("### Auditor Statistics")
    if len(stats_data) > 0:
        df_stats = pd.DataFrame(stats_data)
        st.dataframe(df_stats, use_container_width=True, hide_index=True)
    else:
        st.info("No auditors to display")
