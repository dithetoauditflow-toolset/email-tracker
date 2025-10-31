# 📧 Email Follow-Up Audit Tool

A Streamlit-based multi-user application for tracking email communication between auditors and clients, identifying clients who haven't replied within a specified number of working days.

## 🎯 Features

- **Multi-user authentication** (Admin + Auditors)
- **Per-auditor database isolation** (no SQLite concurrency issues)
- **IMAP/SMTP email synchronization** from company email servers
- **Working day calculations** (excludes weekends and public holidays)
- **Overdue contact detection** based on configurable thresholds
- **Company list management** (upload CSV, edit contacts)
- **Admin panel** for user and settings management
- **Export overdue contacts** to CSV/Excel

## 🏗️ Architecture

- **main.db**: Stores users, settings, internal domains (admin-managed)
- **auditor_{id}.db**: Per-auditor databases for companies and emails (isolated writes)

This architecture eliminates SQLite concurrency issues when multiple auditors sync simultaneously.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Admin Account

```bash
python create_admin.py
```

Follow the prompts to create your admin account.

### 3. Run the Application

```bash
streamlit run main.py
```

The app will open in your browser at `http://localhost:8501`

### 4. First Login

- Login with the admin credentials you created
- Go to "Manage Auditors" to add auditor accounts
- Each auditor should login and configure their email settings

## 📋 For Auditors

### Step 1: Configure Email Settings
- Go to "Email Sync" tab
- Enter your company IMAP/SMTP server details
- Your credentials are encrypted before storage

### Step 2: Upload Company List
- Go to "Company List" tab
- Upload a CSV with columns: `UIF Ref`, `Trade Name`, `Email`, `Alt Email`
- Edit the table as needed

### Step 3: Sync Emails
- Go to "Email Sync" tab
- Click "Sync Emails Now"
- The system fetches emails from/to your company contacts

### Step 4: View Overdue Follow-ups
- Go to "Overdue Follow-ups" tab
- See contacts who haven't replied within the threshold
- Export to CSV for follow-up actions

## 🔧 For Admins

### Manage Auditors
- Add new auditor accounts
- Delete inactive auditors

### Configure Settings
- **Follow-up Threshold**: Number of working days before marking as overdue
- **Internal Domains**: Domains to exclude from sync (e.g., `@rbrgroup.co.za`)

### View Overview
- See statistics for all auditors
- Monitor last sync times and email counts

## 📁 Project Structure

```
audiflow_email_tracker/
├── main.py                 # Application entry point
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
│
├── auth/                   # Authentication system
│   ├── login.py
│   └── session_manager.py
│
├── data/                   # Database management
│   ├── db_manager.py       # Database operations
│   ├── holidays.json       # Public holidays
│   ├── main.db            # Main database (created on first run)
│   └── auditor_*.db       # Per-auditor databases
│
├── email_sync/            # Email synchronization
│   ├── imap_handler.py    # IMAP email fetching
│   └── sync_manager.py    # Sync orchestration
│
├── ui/                    # User interface
│   ├── admin_panel.py
│   └── auditor_dashboard.py
│
└── utils/                 # Utilities
    ├── encryption.py      # Credential encryption
    ├── date_utils.py      # Working day calculations
    └── logger.py          # Logging
```

## 🔐 Security

- Passwords hashed with bcrypt
- Email credentials encrypted with Fernet (AES)
- Session management with Streamlit

### Production Deployment

For production on Streamlit Cloud, add encryption key to `.streamlit/secrets.toml`:

```toml
encryption_key = "your-secure-encryption-key-here"
```

## 📊 Company CSV Format

Your company list CSV should have these columns:

| UIF Ref | Trade Name | Email | Alt Email |
|---------|------------|-------|-----------|
| UIF001 | Company A | contact@companya.com | alt@companya.com |
| UIF002 | Company B | info@companyb.com | |

## 🛠️ Troubleshooting

### Email Sync Issues

**Problem**: "Failed to connect to email server"
- Check IMAP/SMTP host and port settings
- Verify email credentials
- Ensure firewall allows connections
- Some providers require "app passwords" instead of regular passwords

**Problem**: No emails synced
- Verify company email addresses are correct
- Check that emails exist in the specified date range
- Review internal domain settings (might be filtering too aggressively)

### Database Issues

**Problem**: "Database locked" error
- This shouldn't happen with per-auditor databases
- If it does, check that no other process is accessing the DB file

## 📝 Notes

- Initial sync fetches last 30 days of emails (configurable in `config.py`)
- Working days exclude weekends and public holidays defined in `holidays.json`
- Sync is incremental after first run (only fetches new emails)
- Each auditor's data is completely isolated

## 📞 Support

For issues or questions, contact the development team.

---

**Version**: 1.0  
**Author**: Sir Banya  
**Built for**: Baba Riri & RBR Group
