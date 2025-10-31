"""
Auditor dashboard - main interface for auditors
"""
import streamlit as st
import pandas as pd
import sqlite3
import json
from io import StringIO, BytesIO
import re
import datetime as dt
from data.db_manager import DatabaseManager
from email_sync.sync_manager import EmailSyncManager
from utils.encryption import encrypt_email_config, decrypt_email_config, _is_cloud_mode
from auth.session_manager import get_current_user
from config import MAIN_DB_PATH
from email_sync.imap_handler import IMAPHandler


def show_auditor_dashboard():
    """Display auditor dashboard"""
    user = get_current_user()
    if not user:
        st.error("Not authenticated")
        return
    
    # Fetch profile details for display
    full_name = None
    email_addr = None
    try:
        conn = sqlite3.connect(MAIN_DB_PATH)
        cur = conn.cursor()
        row = cur.execute("SELECT full_name, email FROM users WHERE id = ?", (user['id'],)).fetchone()
        if row:
            full_name = row[0]
            email_addr = row[1]
        conn.close()
    except Exception:
        pass
    display_name = (full_name or '').strip() or user['username']
    st.title(f"👤 Auditor Dashboard - {display_name}")
    if email_addr:
        st.caption(f"{email_addr} • @{user['username']}")
    
    # Get database path
    db = DatabaseManager()
    db_path = db.get_auditor_db_path(user['id'])
    
    # Tabs (reordered: Overview, Overdue, Company List, Email Sync)
    tab0, tab3, tab1, tab2 = st.tabs(["📊 Overview", "⏰ Overdue Follow-ups", "📋 Company List", "📧 Email Sync"])
    
    with tab0:
        show_overview_tab(user['id'], db_path)
    
    with tab3:
        show_overdue_tab(user['id'], db_path)
    
    with tab1:
        show_company_list_tab(user['id'], db_path)
    
    with tab2:
        show_email_sync_tab(user, db_path)


def show_overview_tab(auditor_id: int, db_path: str):
    """Overview dashboard: recent activity chart and company stats"""
    from utils.date_utils import WorkingDayCalculator
    
    st.subheader("Overview")
    
    # Load emails
    conn = sqlite3.connect(db_path)
    emails_df = pd.read_sql_query("SELECT company_id, direction, date FROM emails", conn)
    companies_df = pd.read_sql_query("SELECT id, uif_ref, trade_name, email, alt_email FROM companies", conn)
    conn.close()
    
    # Normalize timestamps to naive UTC
    def to_naive_utc_series(s):
        ts = pd.to_datetime(s, errors='coerce', utc=True)
        return ts.dt.tz_convert('UTC').dt.tz_localize(None)
    
    if len(emails_df) > 0:
        emails_df['date'] = to_naive_utc_series(emails_df['date'])
        emails_df['date_only'] = emails_df['date'].dt.date
    
    # Current time (naive UTC) for consistent comparisons
    now_naive_utc = pd.Timestamp.now(tz='UTC').tz_convert('UTC').tz_localize(None)
    
    # Stats summary section
    st.write("### Stats")
    total_companies = len(companies_df)
    sent_today = 0
    overdue_count = 0
    due_tomorrow = 0
    zero_replies = 0
    emailed_gt_10 = 0

    if len(emails_df) > 0:
        # Sent today (UTC naive)
        sent_today = int((emails_df[(emails_df['direction'] == 'outgoing') & (emails_df['date'].dt.date == now_naive_utc.date())]).shape[0])

        # Precompute counts by company for speed
        by_company = emails_df.groupby(['company_id', 'direction']).size().unstack(fill_value=0)

    # Working day calculator
    calc = WorkingDayCalculator()
    now_d = now_naive_utc

    for _, c in companies_df.iterrows():
        cid = c['id']
        c_emails = emails_df[emails_df['company_id'] == cid] if len(emails_df) > 0 else pd.DataFrame(columns=['date','direction'])
        last_sent = c_emails.loc[c_emails['direction']=='outgoing','date'].max() if len(c_emails)>0 else pd.NaT
        sent_count = int((c_emails[c_emails['direction']=='outgoing']).shape[0]) if len(c_emails)>0 else 0

        # zero replies (only count if we ever sent something)
        if sent_count > 0:
            total_incoming = int((c_emails[c_emails['direction']=='incoming']).shape[0]) if len(c_emails)>0 else 0
            if total_incoming == 0:
                zero_replies += 1

        # emailed more than 10 times
        if sent_count >= 10:
            emailed_gt_10 += 1

        # Overdue and due tomorrow: must have a last outgoing and NO incoming after that
        if pd.notna(last_sent):
            last_reply_after = c_emails.loc[(c_emails['direction']=='incoming') & (c_emails['date'] > last_sent), 'date'].max() if len(c_emails)>0 else pd.NaT
            if pd.isna(last_reply_after):
                # No reply after last sent
                try:
                    dbm = DatabaseManager()
                    threshold = int(dbm.get_setting('followup_days') or 3)
                except Exception:
                    threshold = 3
                days_since = calc.working_days_between(pd.to_datetime(last_sent), now_d)
                if days_since > threshold:
                    overdue_count += 1
                elif days_since == threshold:
                    due_tomorrow += 1

    # Render stat cards
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.metric("Total Companies", total_companies)
    with sc2:
        st.metric("Overdue Companies", overdue_count)
    with sc3:
        st.metric("Emails Sent Today", sent_today)

    sc4, sc5, sc6 = st.columns(3)
    with sc4:
        st.metric("Due Tomorrow", due_tomorrow)
    with sc5:
        st.metric("Companies with 0 Replies", zero_replies)
    with sc6:
        st.metric(">=10 Emails Sent", emailed_gt_10)

    # Last sync and quick sync action
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT last_sync, last_sync_status FROM sync_log WHERE id = 1")
    sync_row = cur.fetchone()
    conn.close()

    last_sync_str = None
    if sync_row and sync_row[0]:
        try:
            last_sync_str = pd.to_datetime(sync_row[0]).strftime("%Y-%m-%d %H:%M")
        except Exception:
            last_sync_str = str(sync_row[0])

    st.write("### Sync")
    c1, c2 = st.columns([2,1])
    with c1:
        st.caption(f"Last Sync: {last_sync_str or 'Never'}" + (f"  •  Status: {sync_row[1]}" if sync_row and sync_row[1] else ""))
    with c2:
        if _is_cloud_mode():
            st.info("Email sync via IMAP is disabled on Cloud. Use local deployment or API-based sync.")
        else:
            if st.button("🔄 Sync Emails Now", type="primary", key="overview_sync_now"):
                progress = st.progress(0.0)
                log_container = st.container()
                log_ph = log_container.empty()
                logs = []

                def emit(msg, p):
                    nonlocal logs
                    if msg:
                        logs.append(msg)
                        log_ph.write("\n".join(logs[-10:]))
                    if p is not None:
                        try:
                            progress.progress(max(0.0, min(1.0, float(p))))
                        except Exception:
                            pass

                with st.spinner("Synchronizing emails from last checkpoint..."):
                    try:
                        db = DatabaseManager()
                        internal_domains_json = db.get_setting('internal_domains')
                        internal_domains = json.loads(internal_domains_json) if internal_domains_json else []

                        sync_manager = EmailSyncManager(
                            auditor_id=auditor_id,
                            db_path=db_path,
                            encrypted_config=sqlite3.connect(MAIN_DB_PATH).execute("SELECT email_config FROM users WHERE id = ?", (auditor_id,)).fetchone()[0]
                        )
                        result = sync_manager.sync(internal_domains=internal_domains, callback=emit)
                        if result['success']:
                            progress.progress(1.0)
                            st.success(result['message'])
                            st.rerun()
                        else:
                            st.error(result['message'])
                    except Exception as e:
                        st.error(f"Sync failed: {e}")
    
    st.write("### Company activity")
    if len(companies_df) == 0:
        st.info("No companies found. Upload a company list to begin.")
        return

    with st.form("company_search_form"):
        q_input = st.text_input("Search companies (UIF Ref, Trade Name, Email)", key="company_search")
        submitted_search = st.form_submit_button("Search")
    q = (q_input or "").strip()
    if q:
        ql = q.lower()
        def _m(s):
            s = '' if pd.isna(s) else str(s)
            return ql in s.lower()
        msk = (
            companies_df['uif_ref'].apply(_m) |
            companies_df['trade_name'].apply(_m) |
            companies_df['email'].apply(_m) |
            companies_df['alt_email'].apply(_m)
        )
        companies_view = companies_df[msk].reset_index(drop=True)
    else:
        companies_view = companies_df

    now_d = now_naive_utc
    calc = WorkingDayCalculator()
    cards_per_row = 3
    rows = []
    for _, c in companies_view.iterrows():
        cid = c['id']
        c_emails = emails_df[emails_df['company_id'] == cid] if len(emails_df) > 0 else pd.DataFrame(columns=['date','direction'])
        last_sent = c_emails.loc[c_emails['direction']=='outgoing','date'].max() if len(c_emails)>0 else pd.NaT
        last_in = c_emails.loc[c_emails['direction']=='incoming','date'].max() if len(c_emails)>0 else pd.NaT
        last_contact = max([d for d in [last_sent, last_in] if pd.notna(d)], default=pd.NaT)
        replies_since = 0
        if pd.notna(last_sent) and len(c_emails) > 0:
            replies_since = int((c_emails[(c_emails['direction']=='incoming') & (c_emails['date']> last_sent)]).shape[0])
        sent_count = int((c_emails[c_emails['direction']=='outgoing']).shape[0]) if len(c_emails)>0 else 0
        non_compliant = sent_count >= 10
        # Days since last contact (working days); if no contact yet, leave blank
        if pd.notna(last_contact):
            try:
                days_since_contact = int(calc.working_days_between(pd.to_datetime(last_contact), now_d))
            except Exception:
                days_since_contact = None
        else:
            days_since_contact = None

        rows.append({
            'uif_ref': c.get('uif_ref',''),
            'trade_name': c.get('trade_name',''),
            'email': c.get('email',''),
            'alt_email': c.get('alt_email',''),
            'sent': sent_count,
            'replies_since': replies_since,
            'last_contact': (pd.to_datetime(last_contact).strftime('%Y-%m-%d') if pd.notna(last_contact) else ''),
            'days_since_contact': days_since_contact,
            'non_compliant': non_compliant,
        })

    # Render grid of cards (pure Streamlit widgets)
    for i in range(0, len(rows), cards_per_row):
        cols = st.columns(cards_per_row)
        for j, col in enumerate(cols):
            if i + j >= len(rows):
                continue
            r = rows[i + j]
            with col:
                with st.container(border=True):
                    st.markdown(f"**{r['trade_name']}**")
                    st.caption(f"UIF Ref: {r['uif_ref']}")
                    if r['email']:
                        st.markdown(f"[{r['email']}](mailto:{r['email']})")
                    if r['alt_email']:
                        st.caption(f"Alt Email: {r['alt_email']}")
                    m1, m2, m3 = st.columns(3)
                    with m1:
                        st.metric("Sent", r['sent'])
                    with m2:
                        st.metric("Replies Since", r['replies_since'])
                    with m3:
                        dsc = r.get('days_since_contact', None)
                        st.metric("Days Since", dsc if dsc is not None else "—")
                    st.caption(f"Last Contact: {r['last_contact'] or '—'}")
                    b1, b2 = st.columns(2)
                    with b1:
                        if r['non_compliant']:
                            st.markdown(
                                "<div style='width:100%;text-align:center;background:#b00020;color:#fff;padding:6px 10px;border-radius:6px;font-weight:600'>Non-compliant</div>",
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                "<div style='width:100%;text-align:center;background:#2e7d32;color:#fff;padding:6px 10px;border-radius:6px;font-weight:600'>Compliant</div>",
                                unsafe_allow_html=True,
                            )
                    with b2:
                        if st.button("Copy UIF", key=f"copyuif_{i}_{j}"):
                            st.session_state["last_copied_uif"] = r['uif_ref']
                            st.success("UIF Ref copied (ready to paste)")
                            st.text_input("Copied UIF", value=r['uif_ref'], key=f"copied_uif_{i}_{j}", disabled=True, label_visibility="collapsed")


def show_company_list_tab(auditor_id: int, db_path: str):
    """Show company list management"""
    st.subheader("Company Contact List")
    
    # Quick add single company
    with st.form("add_company_form"):
        st.write("### Add Company")
        ac1, ac2 = st.columns(2)
        with ac1:
            add_uif = st.text_input("UIF Ref")
            add_trade = st.text_input("Trade Name")
        with ac2:
            add_email = st.text_input("Email")
            add_alt = st.text_input("Alt Email", value="")
        submit_add = st.form_submit_button("Add Company")
    if submit_add:
        add_uif_norm = (add_uif or "").strip()
        add_trade_norm = (add_trade or "").strip()
        add_email_norm = (add_email or "").strip()
        if not add_uif_norm or not add_trade_norm or not add_email_norm:
            st.error("UIF Ref, Trade Name and Email are required")
        else:
            try:
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                # skip if UIF exists
                normalized_uif = add_uif_norm.lower()
                if normalized_uif:
                    exists = cur.execute("SELECT 1 FROM companies WHERE LOWER(IFNULL(uif_ref,'')) = ? LIMIT 1", (normalized_uif,)).fetchone()
                    if exists:
                        st.warning("A company with this UIF Ref already exists. Skipping add.")
                    else:
                        cur.execute("INSERT INTO companies (uif_ref, trade_name, email, alt_email) VALUES (?, ?, ?, ?)", (add_uif_norm, add_trade_norm, add_email_norm, add_alt))
                        conn.commit()
                        st.success("Company added")
                        st.rerun()
            except Exception as e:
                st.error(f"Add failed: {e}")
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
    
    # Display current companies
    st.write("### Current Companies")
    conn = sqlite3.connect(db_path)
    df_companies = pd.read_sql_query("SELECT * FROM companies ORDER BY trade_name", conn)
    conn.close()
    
    if len(df_companies) > 0:
        # Show editable dataframe
        st.write(f"Total: {len(df_companies)} companies")
        
        edited_df = st.data_editor(
            df_companies,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "uif_ref": "UIF Ref",
                "trade_name": "Trade Name",
                "email": "Email",
                "alt_email": "Alt Email"
            }
        )
        
        if st.button("💾 Save Changes"):
            try:
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()

                # Get existing company IDs
                existing_ids = set(r[0] for r in cur.execute("SELECT id FROM companies").fetchall())

                # Determine edited IDs (present) and rows
                edited_df = edited_df.copy()
                # Normalize NaN ids to None
                if 'id' in edited_df.columns:
                    edited_df['id'] = edited_df['id'].apply(lambda v: int(v) if pd.notna(v) and str(v).strip() != '' else None)

                edited_ids_present = set(int(v) for v in edited_df['id'].dropna().astype(int).tolist()) if 'id' in edited_df.columns else set()

                # Deletions: existing not in edited
                ids_to_delete = existing_ids - edited_ids_present
                for del_id in ids_to_delete:
                    cur.execute("DELETE FROM companies WHERE id = ?", (del_id,))

                # Upserts
                for _, row in edited_df.iterrows():
                    rid = row.get('id', None)
                    vals = (
                        row.get('uif_ref', '') or '',
                        row.get('trade_name', '') or '',
                        row.get('email', '') or '',
                        row.get('alt_email', '') or ''
                    )
                    if rid is None:
                        # Insert new
                        cur.execute(
                            "INSERT INTO companies (uif_ref, trade_name, email, alt_email) VALUES (?, ?, ?, ?)",
                            vals
                        )
                    else:
                        # Update existing
                        cur.execute(
                            "UPDATE companies SET uif_ref = ?, trade_name = ?, email = ?, alt_email = ? WHERE id = ?",
                            (*vals, int(rid))
                        )

                conn.commit()
                conn.close()
                st.success("✅ Changes saved")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving: {e}")
    else:
        st.info("No companies yet. Upload a CSV file to get started.")

    # Upload CSV/XLSX (moved to bottom)
    st.write("### Upload Company List")
    # Downloadable Excel template for users to fill and re-upload (exact headers)
    tmpl_df = pd.DataFrame(columns=["UIF_REF_NUMBER", "TRADENAME", "EMAIL_ADDRESS", "ALTENATIVE_EMAIL"])
    xbuf = BytesIO()
    with pd.ExcelWriter(xbuf, engine="openpyxl") as writer:
        tmpl_df.to_excel(writer, index=False, sheet_name="Template")
    xbuf.seek(0)
    st.download_button(
        label="📥 Download Company List Template (Excel)",
        data=xbuf.getvalue(),
        file_name="company_list_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    uploaded_file = st.file_uploader(
        "Upload CSV or Excel file (UIF_REF_NUMBER, TRADENAME, EMAIL_ADDRESS, ALTENATIVE_EMAIL)",
        type=['csv', 'xlsx', 'xls'],
        key="company_upload"
    )
    
    if uploaded_file:
        try:
            name_lower = uploaded_file.name.lower()
            if name_lower.endswith((".xlsx", ".xls")):
                df = pd.read_excel(uploaded_file)
            else:
                df = pd.read_csv(uploaded_file)
            
            # Normalize and map headers to expected internal names
            def norm(s: str) -> str:
                s = str(s).strip().upper()
                s = re.sub(r"[^A-Z0-9]+", "_", s)
                s = re.sub(r"_+", "_", s).strip("_")
                return s

            alias_map = {
                # UIF Ref
                "UIF_REF": "UIF Ref",
                "UIF_REF_NUMBER": "UIF Ref",
                "UIF_REF__NUMBER": "UIF Ref",
                "UIF_REFERENCE": "UIF Ref",
                "UIF_REFERENCE_NUMBER": "UIF Ref",
                "UIFNO": "UIF Ref",
                "UIF_NUMBER": "UIF Ref",
                # Trade name
                "TRADENAME": "Trade Name",
                "TRADE_NAME": "Trade Name",
                "COMPANY_NAME": "Trade Name",
                "NAME": "Trade Name",
                # Email
                "EMAIL": "Email",
                "EMAIL_ADDRESS": "Email",
                "PRIMARY_EMAIL": "Email",
                # Alt Email (note common misspellings)
                "ALT_EMAIL": "Alt Email",
                "ALTERNATE_EMAIL": "Alt Email",
                "ALTERNATIVE_EMAIL": "Alt Email",
                "ALTENATIVE_EMAIL": "Alt Email",
                "SECONDARY_EMAIL": "Alt Email",
            }

            normalized_columns = {}
            for col in df.columns:
                key = norm(col)
                target = alias_map.get(key)
                if target:
                    normalized_columns[col] = target

            if normalized_columns:
                df = df.rename(columns=normalized_columns)

            # Validate columns after normalization
            required_cols = ['UIF Ref', 'Trade Name', 'Email']
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                st.error(
                    "Missing required columns after normalization: " + ", ".join(missing) +
                    "\nAccepted headers include variations like: UIF_REF_NUMBER, TRADENAME, EMAIL_ADDRESS, ALTENATIVE_EMAIL"
                )
            else:
                # Show preview
                st.write("Preview:")
                st.dataframe(df.head())
                
                if st.button("Import Companies", key="import_companies_bottom"):
                    # Save to database skipping duplicates on UIF Ref
                    conn = sqlite3.connect(db_path)
                    cur = conn.cursor()
                    existing = cur.execute("SELECT IFNULL(uif_ref,'') FROM companies").fetchall()
                    existing_uifs = { (r[0] or '').strip().lower() for r in existing }
                    inserted = 0
                    for _, row in df.iterrows():
                        uif_val = str(row.get('UIF Ref', '') or '').strip()
                        if uif_val and uif_val.strip().lower() in existing_uifs:
                            continue
                        cur.execute(
                            "INSERT INTO companies (uif_ref, trade_name, email, alt_email) VALUES (?, ?, ?, ?)",
                            (
                                uif_val,
                                row.get('Trade Name', ''),
                                row.get('Email', ''),
                                row.get('Alt Email', '')
                            )
                        )
                        inserted += 1
                        if uif_val:
                            existing_uifs.add(uif_val.strip().lower())
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Imported {inserted} new companies (duplicates by UIF Ref skipped)")
                    st.rerun()
        
        except Exception as e:
            st.error(f"Error reading CSV: {e}")


def show_email_sync_tab(user: dict, db_path: str):
    """Show email synchronization interface"""
    st.subheader("Email Synchronization")
    cloud = _is_cloud_mode()
    if cloud:
        st.info("Email synchronization via IMAP is disabled on Streamlit Cloud. Run locally or switch to API-based sync (Microsoft Graph/Gmail) in a future phase.")
        return
    
    # Check if email config exists
    if not user.get('email_config'):
        st.warning("⚠️ Email configuration not set up yet")
        
        with st.expander("🔧 Configure Email Settings"):
            with st.form("email_config_form"):
                st.write("Enter your company email server details:")
                
                imap_host = st.text_input("IMAP Host", placeholder="imap.company.com")
                imap_port = st.number_input("IMAP Port", value=993, min_value=1, max_value=65535)
                smtp_host = st.text_input("SMTP Host", placeholder="smtp.company.com")
                smtp_port = st.number_input("SMTP Port", value=587, min_value=1, max_value=65535)
                email_addr = st.text_input("Email Address", placeholder="auditor@company.com")
                password = st.text_input("Password", type="password")
                
                c1, c2 = st.columns(2)
                with c1:
                    test_btn = st.form_submit_button("Test IMAP Connection")
                with c2:
                    submit = st.form_submit_button("Save Configuration")

                if test_btn:
                    if not all([imap_host, imap_port, email_addr, password]):
                        st.error("Please fill IMAP host, port, email and password to test")
                    else:
                        handler = IMAPHandler(imap_host, int(imap_port), email_addr, password)
                        ok = handler.connect()
                        handler.disconnect()
                        if ok:
                            st.success("IMAP connection successful")
                        else:
                            st.error("IMAP connection failed. Check credentials and server.")

                if submit:
                    if not all([imap_host, smtp_host, email_addr, password]):
                        st.error("Please fill in all fields")
                    else:
                        # Encrypt and save
                        encrypted = encrypt_email_config(
                            imap_host, imap_port, smtp_host, smtp_port, email_addr, password
                        )
                        
                        # Update database
                        conn = sqlite3.connect(MAIN_DB_PATH)
                        conn.execute(
                            "UPDATE users SET email_config = ? WHERE id = ?",
                            (encrypted, user['id'])
                        )
                        conn.commit()
                        conn.close()
                        
                        # Update session so UI reflects the saved config immediately
                        try:
                            st.session_state.user['email_config'] = encrypted
                        except Exception:
                            pass
                        
                        st.success("✅ Email configuration saved!")
                        st.rerun()
        
        return
    
    # Show sync interface
    # Indicate configuration status clearly
    try:
        cfg = decrypt_email_config(user['email_config']) if user.get('email_config') else None
    except Exception:
        cfg = None

    if cfg:
        masked_email = cfg.get('email', '')
        if masked_email and '@' in masked_email:
            local, domain = masked_email.split('@', 1)
            masked_email = (local[:2] + '***@' + domain) if len(local) > 2 else ('***@' + domain)
        col_a, col_b, col_c = st.columns([2,2,2])
        with col_a:
            st.success(f"Email sync configured for: {masked_email}")
        with col_b:
            st.caption(f"IMAP: {cfg.get('imap_host','')}:{cfg.get('imap_port','')}")
        with col_c:
            st.caption(f"SMTP: {cfg.get('smtp_host','')}:{cfg.get('smtp_port','')}")
        
        # Reconfigure form
        with st.expander("🔁 Reconfigure Email Settings"):
            with st.form("email_reconfig_form"):
                imap_host = st.text_input("IMAP Host", value=str(cfg.get('imap_host') or ''))
                imap_port = st.number_input("IMAP Port", value=int(cfg.get('imap_port') or 993), min_value=1, max_value=65535)
                smtp_host = st.text_input("SMTP Host", value=str(cfg.get('smtp_host') or ''))
                smtp_port = st.number_input("SMTP Port", value=int(cfg.get('smtp_port') or 587), min_value=1, max_value=65535)
                email_addr = st.text_input("Email Address", value=str(cfg.get('email') or ''))
                password = st.text_input("Password (leave blank to keep existing)", type="password")

                c1, c2 = st.columns(2)
                with c1:
                    test_btn = st.form_submit_button("Test IMAP Connection")
                with c2:
                    save_btn = st.form_submit_button("Save Changes")

                effective_pw = password if password else (cfg.get('password') or '')

                if test_btn:
                    if not all([imap_host, imap_port, email_addr, effective_pw]):
                        st.error("Please ensure IMAP host, port, email and password are provided to test")
                    else:
                        handler = IMAPHandler(imap_host, int(imap_port), email_addr, effective_pw)
                        ok = handler.connect()
                        handler.disconnect()
                        if ok:
                            st.success("IMAP connection successful")
                        else:
                            st.error("IMAP connection failed. Check credentials and server.")

                if save_btn:
                    if not all([imap_host, smtp_host, email_addr]):
                        st.error("IMAP host, SMTP host, and Email are required")
                    else:
                        final_pw = effective_pw
                        if not final_pw:
                            st.error("Password is required to save if it isn't present in existing config")
                        else:
                            encrypted = encrypt_email_config(
                                imap_host, imap_port, smtp_host, smtp_port, email_addr, final_pw
                            )
                            conn = sqlite3.connect(MAIN_DB_PATH)
                            conn.execute(
                                "UPDATE users SET email_config = ? WHERE id = ?",
                                (encrypted, user['id'])
                            )
                            conn.commit()
                            conn.close()
                            try:
                                st.session_state.user['email_config'] = encrypted
                            except Exception:
                                pass
                            st.success("✅ Email configuration updated!")
                            st.rerun()
    st.write("### Sync Status")
    
    # Get last sync info
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT last_sync, last_sync_status FROM sync_log WHERE id = 1")
    sync_log = cursor.fetchone()
    
    # Get email count
    cursor.execute("SELECT COUNT(*) as count FROM emails")
    email_count = cursor.fetchone()[0]
    
    conn.close()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Emails", email_count)
    
    with col2:
        if sync_log and sync_log[0]:
            st.metric("Last Sync", pd.to_datetime(sync_log[0]).strftime("%Y-%m-%d %H:%M"))
        else:
            st.metric("Last Sync", "Never")
    
    if sync_log and sync_log[1]:
        if "success" in sync_log[1]:
            st.success(f"Status: {sync_log[1]}")
        else:
            st.error(f"Status: {sync_log[1]}")
    
    # Sync button
    if st.button("🔄 Sync Emails Now", type="primary", key="sync_tab_sync_now"):
        # Live progress UI
        progress = st.progress(0.0)
        log_container = st.container()
        log_placeholder = log_container.empty()
        logs = []

        def emit(msg: str | None, p: float | None):
            nonlocal logs
            if msg:
                logs.append(msg)
                # show last 12 lines to keep it compact
                log_placeholder.write("\n".join(logs[-12:]))
            if p is not None:
                try:
                    progress.progress(max(0.0, min(1.0, float(p))))
                except Exception:
                    pass

        with st.spinner("Synchronizing emails..."):
            try:
                # Get internal domains setting
                db = DatabaseManager()
                internal_domains_json = db.get_setting('internal_domains')
                internal_domains = json.loads(internal_domains_json) if internal_domains_json else []
                
                # Perform sync
                sync_manager = EmailSyncManager(
                    auditor_id=user['id'],
                    db_path=db_path,
                    encrypted_config=user['email_config']
                )
                
                result = sync_manager.sync(internal_domains=internal_domains, callback=emit)
                
                if result['success']:
                    progress.progress(1.0)
                    st.success(result['message'])
                    st.info(f"📊 Fetched: {result['total_fetched']}, Filtered: {result['filtered']}, Saved: {result['emails_synced']}")
                    st.rerun()
                else:
                    st.error(result['message'])
            
            except Exception as e:
                st.error(f"Sync failed: {e}")


def show_overdue_tab(auditor_id: int, db_path: str):
    """Show overdue follow-ups"""
    from utils.date_utils import WorkingDayCalculator
    
    st.subheader("⏰ Overdue Follow-ups")
    
    # Get threshold setting
    db = DatabaseManager()
    threshold = int(db.get_setting('followup_days') or 3)
    
    st.write(f"Showing contacts with no reply after **{threshold} working days**")
    
    # Calculate overdue contacts
    conn = sqlite3.connect(db_path)
    
    # Get all companies
    companies = pd.read_sql_query("SELECT * FROM companies", conn)
    
    calculator = WorkingDayCalculator()
    overdue_list = []
    
    def _to_naive_utc(ts_val):
        ts = pd.to_datetime(ts_val, errors='coerce', utc=True)
        if ts is None or pd.isna(ts):
            return None
        # Convert to naive UTC (no tzinfo) for consistent comparisons
        return ts.tz_convert('UTC').tz_localize(None)

    now_naive_utc = pd.Timestamp.now(tz='UTC').tz_convert('UTC').tz_localize(None)

    for _, company in companies.iterrows():
        company_id = company['id']
        
        # Get last outgoing email
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date FROM emails 
            WHERE company_id = ? AND direction = 'outgoing'
            ORDER BY date DESC LIMIT 1
        """, (company_id,))
        last_sent = cursor.fetchone()
        
        if not last_sent:
            continue  # No emails sent to this company
        
        last_sent_date = _to_naive_utc(last_sent[0])
        if last_sent_date is None:
            continue
        
        # Get last incoming email after that
        cursor.execute("""
            SELECT date FROM emails 
            WHERE company_id = ? AND direction = 'incoming' AND date > ?
            ORDER BY date DESC LIMIT 1
        """, (company_id, last_sent[0]))
        last_reply = cursor.fetchone()
        
        # Calculate days since last sent
        if last_reply:
            last_reply_date = _to_naive_utc(last_reply[0])
            if last_reply_date is None:
                days_since = calculator.working_days_between(last_sent_date, now_naive_utc)
            else:
                days_since = calculator.working_days_between(last_sent_date, last_reply_date)
        else:
            # No reply yet
            days_since = calculator.working_days_between(last_sent_date, now_naive_utc)
        
        # Check if overdue
        if not last_reply and days_since > threshold:
            overdue_list.append({
                'UIF Ref': company['uif_ref'],
                'Trade Name': company['trade_name'],
                'Email': company['email'],
                'Last Sent': last_sent_date.strftime("%Y-%m-%d"),
                'Last Reply': 'No reply',
                'Working Days Since': days_since
            })
    
    conn.close()
    
    if overdue_list:
        df_overdue = pd.DataFrame(overdue_list)
        st.write(f"### {len(df_overdue)} Overdue Contacts")
        st.dataframe(df_overdue, use_container_width=True)
        
        # Export button
        csv = df_overdue.to_csv(index=False)
        st.download_button(
            label="📥 Download as Excel",
            data=csv,
            file_name=f"overdue_followups_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.success("✅ No overdue follow-ups! All contacts are up to date.")
