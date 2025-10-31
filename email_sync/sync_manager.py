"""
Email synchronization manager - coordinates IMAP fetching and database storage
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from email_sync.imap_handler import IMAPHandler
from utils.encryption import decrypt_email_config
from utils.logger import setup_logger
from config import SYNC_DAYS_BACK

logger = setup_logger()


class EmailSyncManager:
    """Manage email synchronization for an auditor"""
    
    def __init__(self, auditor_id: int, db_path: str, encrypted_config: str):
        self.auditor_id = auditor_id
        self.db_path = db_path
        
        # Decrypt email configuration
        self.email_config = decrypt_email_config(encrypted_config)
        
        # Initialize IMAP handler
        self.imap = IMAPHandler(
            host=self.email_config["imap_host"],
            port=self.email_config["imap_port"],
            email_addr=self.email_config["email"],
            password=self.email_config["password"]
        )
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_company_emails(self) -> List[str]:
        """Get list of company email addresses from database"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT email, alt_email FROM companies")
        rows = cursor.fetchall()
        conn.close()
        
        emails = []
        for row in rows:
            if row['email']:
                emails.append(row['email'].lower())
            if row['alt_email']:
                emails.append(row['alt_email'].lower())
        
        return list(set(emails))  # Remove duplicates
    
    def get_last_sync_date(self) -> Optional[datetime]:
        """Get last successful sync date"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT last_sync FROM sync_log WHERE id = 1")
        result = cursor.fetchone()
        conn.close()
        
        if result and result['last_sync']:
            return datetime.fromisoformat(result['last_sync'])
        return None
    
    def update_sync_log(self, status: str = "success"):
        """Update sync log with current timestamp"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE sync_log 
            SET last_sync = ?, last_sync_status = ?
            WHERE id = 1
        """, (datetime.now().isoformat(), status))
        
        conn.commit()
        conn.close()
    
    def get_company_id_by_email(self, email_addr: str) -> Optional[int]:
        """Get company ID by email address"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        email_lower = email_addr.lower()
        cursor.execute("""
            SELECT id FROM companies 
            WHERE LOWER(email) = ? OR LOWER(alt_email) = ?
        """, (email_lower, email_lower))
        
        result = cursor.fetchone()
        conn.close()
        
        return result['id'] if result else None
    
    def save_emails(self, emails: List[Dict], callback=None) -> int:
        """Save emails to database, skip duplicates, report progress if callback provided"""
        conn = self._get_connection()
        cursor = conn.cursor()
        saved_count = 0
        total = len(emails)
        processed = 0
        matched_companies = set()
        
        for email_data in emails:
            try:
                # Determine company ID based on email addresses
                company_id = None
                if email_data['direction'] == 'incoming':
                    company_id = self.get_company_id_by_email(email_data['from_addr'])
                else:
                    company_id = self.get_company_id_by_email(email_data['to_addr'])
                
                if not company_id:
                    processed += 1
                    if callback and total:
                        callback(f"Saving emails {processed}/{total} | matched companies: {len(matched_companies)}", 0.85 + 0.1 * (processed/total))
                    continue  # Skip if not from/to a tracked company
                else:
                    matched_companies.add(company_id)
                
                # Insert email (skip if message_id already exists)
                cursor.execute("""
                    INSERT OR IGNORE INTO emails 
                    (company_id, direction, from_addr, to_addr, subject, date, message_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    company_id,
                    email_data['direction'],
                    email_data['from_addr'],
                    email_data['to_addr'],
                    email_data['subject'],
                    email_data['date'].isoformat(),
                    email_data['message_id']
                ))
                
                if cursor.rowcount > 0:
                    saved_count += 1
            
            except Exception as e:
                logger.error(f"Error saving email: {e}")
                continue
            finally:
                processed += 1
                if callback and total:
                    callback(f"Saving emails {processed}/{total} | matched companies: {len(matched_companies)}", 0.85 + 0.1 * (processed/total))
        
        conn.commit()
        conn.close()
        
        return saved_count
    
    def filter_internal_domains(self, emails: List[Dict], internal_domains: List[str]) -> List[Dict]:
        """Filter out emails from internal domains"""
        filtered = []
        internal_domains_lower = [d.lower() for d in internal_domains]
        
        for email_data in emails:
            from_domain = email_data['from_addr'].split('@')[-1] if '@' in email_data['from_addr'] else ''
            to_domain = email_data['to_addr'].split('@')[-1] if '@' in email_data['to_addr'] else ''
            
            # Skip if both from and to are internal
            is_from_internal = any(from_domain.endswith(d.lstrip('@')) for d in internal_domains_lower)
            is_to_internal = any(to_domain.endswith(d.lstrip('@')) for d in internal_domains_lower)
            
            if not (is_from_internal and is_to_internal):
                filtered.append(email_data)
        
        return filtered
    
    def sync(self, internal_domains: List[str] = None, callback=None) -> Dict[str, any]:
        """
        Perform email synchronization.
        Returns statistics about the sync.
        """
        internal_domains = internal_domains or []
        
        try:
            if callback:
                callback("Preparing sync...", 0.01)
            # Get company emails to filter
            company_emails = self.get_company_emails()
            if not company_emails:
                return {
                    "success": False,
                    "message": "No companies found. Please upload company list first.",
                    "emails_synced": 0
                }
            
            # Get last sync date or default to N days back
            since_date = self.get_last_sync_date()
            if not since_date:
                since_date = datetime.now() - timedelta(days=SYNC_DAYS_BACK)
            
            logger.info(f"Starting sync for auditor {self.auditor_id} since {since_date}")
            if callback:
                callback(f"Company list loaded: {len(company_emails)} emails", 0.05)
            
            # Connect to IMAP
            if not self.imap.connect(callback=callback):
                return {
                    "success": False,
                    "message": "Failed to connect to email server. Check credentials.",
                    "emails_synced": 0
                }
            
            # Fetch incoming emails
            incoming = self.imap.fetch_emails(
                folder="INBOX",
                since_date=since_date,
                filter_addresses=company_emails,
                callback=lambda msg, prog: callback(f"INBOX: {msg}", prog) if callback and msg else (callback(None, prog) if callback else None)
            )
            if callback:
                callback(f"Fetched {len(incoming)} incoming emails", 0.45)
            
            # Fetch outgoing emails
            outgoing = self.imap.fetch_sent_emails(
                sent_folder="Sent",
                since_date=since_date,
                filter_addresses=company_emails,
                callback=lambda msg, prog: callback(f"Sent: {msg}", prog) if callback and msg else (callback(None, prog) if callback else None)
            )
            if callback:
                callback(f"Fetched {len(outgoing)} sent emails", 0.7)
            
            self.imap.disconnect()
            
            # Combine and filter
            all_emails = incoming + outgoing
            filtered_emails = self.filter_internal_domains(all_emails, internal_domains)
            if callback:
                callback(f"Filtered internal traffic -> {len(filtered_emails)} emails to save", 0.8)
            
            # Save to database
            saved_count = self.save_emails(filtered_emails, callback=callback)
            if callback:
                callback(f"Saved {saved_count} emails to database", 0.95)
            
            # Update sync log
            self.update_sync_log(status="success")
            
            logger.info(f"Sync completed: {saved_count} new emails saved")
            if callback:
                callback("Sync complete", 1.0)
            
            return {
                "success": True,
                "message": f"Successfully synced {saved_count} new emails",
                "emails_synced": saved_count,
                "total_fetched": len(all_emails),
                "filtered": len(filtered_emails)
            }
        
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            self.update_sync_log(status=f"failed: {str(e)}")
            
            return {
                "success": False,
                "message": f"Sync failed: {str(e)}",
                "emails_synced": 0
            }
