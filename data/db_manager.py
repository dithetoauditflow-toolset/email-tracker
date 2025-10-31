"""
Database manager with per-auditor SQLite databases to avoid concurrency issues.
- main.db: stores users, settings (admin-only writes)
- auditor_{id}.db: per-auditor companies and emails (isolated writes)
"""
import sqlite3
import os
from pathlib import Path
from typing import Optional, Dict, Any
import bcrypt
from config import MAIN_DB_PATH, AUDITOR_DB_PREFIX


class DatabaseManager:
    """Manages both main database and per-auditor databases"""
    
    def __init__(self):
        # Ensure data directory exists
        Path("data").mkdir(exist_ok=True)
        self._init_main_db()
    
    def _get_connection(self, db_path: str) -> sqlite3.Connection:
        """Get database connection with proper settings"""
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_main_db(self):
        """Initialize main database with users and settings tables"""
        conn = self._get_connection(MAIN_DB_PATH)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'auditor')),
                email_config TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Ensure new columns exist for auditor profile fields
        try:
            cursor.execute("PRAGMA table_info(users)")
            cols = {row[1] for row in cursor.fetchall()}
            if 'full_name' not in cols:
                cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
            if 'email' not in cols:
                cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
        except sqlite3.DatabaseError:
            pass
        
        # Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Initialize default settings if not exist
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value) 
            VALUES ('followup_days', '3')
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value) 
            VALUES ('internal_domains', '["@rbrgroup.co.za"]')
        """)
        
        conn.commit()
        conn.close()
    
    def init_auditor_db(self, auditor_id: int):
        """Initialize per-auditor database for companies and emails"""
        db_path = f"{AUDITOR_DB_PREFIX}{auditor_id}.db"
        conn = self._get_connection(db_path)
        cursor = conn.cursor()
        
        # Companies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uif_ref TEXT,
                trade_name TEXT NOT NULL,
                email TEXT NOT NULL,
                alt_email TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Emails table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                direction TEXT NOT NULL CHECK(direction IN ('incoming', 'outgoing')),
                from_addr TEXT NOT NULL,
                to_addr TEXT NOT NULL,
                subject TEXT,
                date DATETIME NOT NULL,
                message_id TEXT UNIQUE,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_emails_date ON emails(date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_emails_company ON emails(company_id)
        """)
        
        # Sync log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                last_sync DATETIME,
                last_sync_status TEXT
            )
        """)
        
        # Initialize sync log
        cursor.execute("""
            INSERT OR IGNORE INTO sync_log (id, last_sync) 
            VALUES (1, NULL)
        """)
        
        conn.commit()
        conn.close()
    
    def create_admin(self, username: str, password: str) -> bool:
        """Create admin user (only if no admin exists)"""
        conn = self._get_connection(MAIN_DB_PATH)
        cursor = conn.cursor()
        
        # Check if admin already exists
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'")
        if cursor.fetchone()['count'] > 0:
            conn.close()
            return False
        
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
            (username, password_hash)
        )
        conn.commit()
        conn.close()
        return True
    
    def create_auditor(self, username: str, password: str, full_name: Optional[str] = None, email: Optional[str] = None, email_config: Optional[str] = None) -> Optional[int]:
        """Create auditor user and their database"""
        conn = self._get_connection(MAIN_DB_PATH)
        cursor = conn.cursor()
        
        try:
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
            cursor.execute(
                "INSERT INTO users (username, password_hash, role, email_config, full_name, email) VALUES (?, ?, 'auditor', ?, ?, ?)",
                (username, password_hash, email_config, full_name, email)
            )
            auditor_id = cursor.lastrowid
            conn.commit()
            
            # Initialize auditor's database
            self.init_auditor_db(auditor_id)
            
            return auditor_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    def verify_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Verify user credentials and return user data"""
        conn = self._get_connection(MAIN_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, username, password_hash, role, email_config FROM users WHERE username = ?",
            (username,)
        )
        user = cursor.fetchone()
        conn.close()
        
        if user:
            stored = user['password_hash']
            # Normalize to bytes for bcrypt
            if isinstance(stored, memoryview):
                stored_bytes = bytes(stored)
            elif isinstance(stored, bytes):
                stored_bytes = stored
            elif isinstance(stored, str):
                # Handle both plain hash string and repr of bytes
                try:
                    if stored.startswith("b'") or stored.startswith('b"'):
                        import ast
                        stored_bytes = ast.literal_eval(stored)
                    else:
                        stored_bytes = stored.encode('utf-8')
                except Exception:
                    stored_bytes = stored.encode('utf-8')
            else:
                try:
                    stored_bytes = bytes(stored)
                except Exception:
                    stored_bytes = None

            if stored_bytes is not None and bcrypt.checkpw(password.encode(), stored_bytes):
                return dict(user)
        return None
    
    def update_user_password(self, user_id: int, new_password: str) -> bool:
        """Update password for a user by id"""
        conn = self._get_connection(MAIN_DB_PATH)
        cursor = conn.cursor()
        new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, user_id)
        )
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    def update_user_profile(self, user_id: int, full_name: Optional[str], email: Optional[str]) -> bool:
        """Update basic profile fields for a user"""
        conn = self._get_connection(MAIN_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET full_name = ?, email = ? WHERE id = ?",
            (full_name, email, user_id)
        )
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated
    
    def get_auditor_db_path(self, auditor_id: int) -> str:
        """Get database path for specific auditor"""
        return f"{AUDITOR_DB_PREFIX}{auditor_id}.db"
    
    def get_setting(self, key: str) -> Optional[str]:
        """Get setting value from main database"""
        conn = self._get_connection(MAIN_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result['value'] if result else None
    
    def update_setting(self, key: str, value: str):
        """Update setting in main database"""
        conn = self._get_connection(MAIN_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, value)
        )
        conn.commit()
        conn.close()
