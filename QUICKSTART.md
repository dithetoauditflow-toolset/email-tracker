# 🚀 Quick Start Guide

## Installation & Setup

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: If you encounter build errors with pandas on Python 3.14:
```bash
pip install pandas --only-binary :all:
```

Or use Python 3.11 or 3.12 for best compatibility.

### Step 2: Create Admin Account

```bash
python create_admin.py
```

Enter your desired admin username and password when prompted.

### Step 3: Run the Application

**Option A - Using the batch file (Windows):**
```bash
start.bat
```

**Option B - Manual start:**
```bash
streamlit run main.py
```

The application will open in your browser at `http://localhost:8501`

---

## First Time Usage

### For Admin

1. **Login** with the admin credentials you created
2. **Go to "Manage Auditors" tab**
3. **Add auditor accounts** - create username and password for each auditor
4. **Configure Settings**:
   - Set follow-up threshold (default: 3 working days)
   - Add internal domains to exclude (e.g., @rbrgroup.co.za)

### For Auditors

1. **Login** with credentials provided by admin

2. **Configure Email Settings** (Email Sync tab):
   - IMAP Host: `imap.yourcompany.com`
   - IMAP Port: `993` (usually)
   - SMTP Host: `smtp.yourcompany.com`
   - SMTP Port: `587` (usually)
   - Your email address
   - Your email password
   
   ⚠️ **Note**: Some email providers require "App Passwords" instead of your regular password.

3. **Upload Company List** (Company List tab):
   - Prepare a CSV file with columns: `UIF Ref`, `Trade Name`, `Email`, `Alt Email`
   - Click "Upload CSV file"
   - Review and edit the table if needed

4. **Sync Emails** (Email Sync tab):
   - Click "Sync Emails Now"
   - Wait for sync to complete (first sync may take a few minutes)
   - View sync statistics

5. **Check Overdue Follow-ups** (Overdue Follow-ups tab):
   - See contacts who haven't replied
   - Export to CSV for action

---

## Common Email Server Settings

### Microsoft Outlook/Exchange
- **IMAP**: outlook.office365.com:993
- **SMTP**: smtp.office365.com:587
- **Note**: Enable IMAP in Outlook settings
- **Auth**: May need app password

### Google Workspace
- **IMAP**: imap.gmail.com:993
- **SMTP**: smtp.gmail.com:587
- **Note**: Enable "Less secure app access" or use app password
- **2FA**: Must use app-specific password

### Custom Email Server
- Contact your IT department for:
  - IMAP server address and port
  - SMTP server address and port
  - Whether to use app passwords

---

## Troubleshooting

### "Failed to connect to email server"

**Solutions**:
1. Verify IMAP/SMTP host and port
2. Check credentials (try logging in via webmail)
3. Check if your email provider requires app passwords
4. Ensure firewall allows outbound connections on IMAP/SMTP ports
5. For corporate email, check with IT if IMAP is enabled

### No Emails Syncing

**Solutions**:
1. Verify company email addresses are correct in your company list
2. Check that emails exist in the date range (last 30 days)
3. Review internal domain settings (may be filtering too much)
4. Check sync status for error messages

### "Database locked" Error

This shouldn't happen with per-auditor databases, but if it does:
1. Close all other instances of the app
2. Restart the application
3. Contact admin if persists

---

## Tips

- **Initial Sync**: First sync fetches last 30 days of emails (configurable)
- **Subsequent Syncs**: Only fetch new emails since last sync
- **Working Days**: Calculation excludes weekends and public holidays
- **Data Isolation**: Each auditor's data is completely separate
- **Export**: Download overdue contacts as CSV for Excel

---

## Support

For issues or questions:
- Check the README.md for detailed documentation
- Review the troubleshooting section above
- Contact your system administrator
