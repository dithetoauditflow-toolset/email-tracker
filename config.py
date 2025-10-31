"""
Configuration settings for the Email Follow-Up Audit Tool
"""

# Database paths
MAIN_DB_PATH = "data/main.db"
AUDITOR_DB_PREFIX = "data/auditor_"

# Default settings
DEFAULT_FOLLOWUP_DAYS = 3
DEFAULT_INTERNAL_DOMAINS = ["@rbrgroup.co.za"]

# Email sync settings
EMAIL_BATCH_SIZE = 100
SYNC_DAYS_BACK = 30  # Initial sync: fetch emails from last 30 days

# App settings
APP_TITLE = "Email Follow-Up Audit Tool"
SESSION_TIMEOUT_MINUTES = 120
