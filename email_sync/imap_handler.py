"""
IMAP handler for fetching incoming emails
"""
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from utils.logger import setup_logger

logger = setup_logger()


class IMAPHandler:
    """Handle IMAP email fetching operations"""
    
    def __init__(self, host: str, port: int, email_addr: str, password: str):
        self.host = host
        self.port = port
        self.email = email_addr
        self.password = password
        self.connection = None
    
    def connect(self, callback=None) -> bool:
        """Connect to IMAP server"""
        try:
            self.connection = imaplib.IMAP4_SSL(self.host, self.port)
            self.connection.login(self.email, self.password)
            logger.info(f"IMAP connected successfully for {self.email}")
            if callback:
                callback("Connected to IMAP server", None)
            return True
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            if callback:
                callback(f"IMAP connection failed: {e}", None)
            return False
    
    def disconnect(self):
        """Disconnect from IMAP server"""
        if self.connection:
            try:
                self.connection.logout()
            except:
                pass
    
    def _decode_header_value(self, value: str) -> str:
        """Decode email header value"""
        if not value:
            return ""
        
        decoded_parts = decode_header(value)
        decoded_string = ""
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_string += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                decoded_string += part
        
        return decoded_string
    
    def fetch_emails(self, folder: str = "INBOX", since_date: Optional[datetime] = None,
                     filter_addresses: Optional[List[str]] = None, callback=None) -> List[Dict]:
        """
        Fetch emails from specified folder.
        
        Args:
            folder: IMAP folder name (default: INBOX)
            since_date: Only fetch emails after this date
            filter_addresses: Only fetch emails from/to these addresses
        
        Returns:
            List of email dictionaries
        """
        if not self.connection:
            if not self.connect(callback=callback):
                return []
        
        emails = []
        
        try:
            status_select, _ = self.connection.select(folder)
            if callback:
                if status_select == 'OK':
                    callback(f"Selected folder: {folder}", None)
                else:
                    callback(f"Failed to select folder: {folder}", None)
            
            # Build search criteria
            search_criteria = ["ALL"]
            if since_date:
                date_str = since_date.strftime("%d-%b-%Y")
                search_criteria = [f'SINCE {date_str}']
            
            # Search for emails
            status, messages = self.connection.search(None, *search_criteria)
            if status != "OK":
                logger.error(f"IMAP search failed: {status}")
                if callback:
                    callback(f"Search failed in {folder}", None)
                return []
            
            email_ids = messages[0].split()
            logger.info(f"Found {len(email_ids)} emails to process")
            total = len(email_ids)
            if callback:
                callback(f"{folder}: Found {total} messages", None)
            
            # Process each email
            processed = 0
            for email_id in email_ids:
                try:
                    status, msg_data = self.connection.fetch(email_id, "(RFC822)")
                    if status != "OK":
                        continue
                    
                    # Parse email
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # Extract headers
                    from_addr = self._decode_header_value(msg.get("From", ""))
                    to_addr = self._decode_header_value(msg.get("To", ""))
                    subject = self._decode_header_value(msg.get("Subject", ""))
                    date_str = msg.get("Date", "")
                    message_id = msg.get("Message-ID", "")
                    
                    # Parse date
                    try:
                        email_date = email.utils.parsedate_to_datetime(date_str)
                    except:
                        email_date = datetime.now()
                    
                    # Extract email addresses from From/To (remove names)
                    from_email = email.utils.parseaddr(from_addr)[1].lower()
                    to_email = email.utils.parseaddr(to_addr)[1].lower()
                    
                    # Filter by addresses if specified
                    if filter_addresses:
                        filter_addresses_lower = [addr.lower() for addr in filter_addresses]
                        if from_email not in filter_addresses_lower and to_email not in filter_addresses_lower:
                            continue
                    
                    emails.append({
                        "message_id": message_id,
                        "from_addr": from_email,
                        "to_addr": to_email,
                        "subject": subject,
                        "date": email_date,
                        "direction": "incoming"
                    })
                
                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {e}")
                    continue
                finally:
                    processed += 1
                    if callback and total:
                        callback(None, min(processed / total, 1.0))
            
            logger.info(f"Successfully processed {len(emails)} emails")
        
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
        
        return emails
    
    def fetch_sent_emails(self, sent_folder: str = "Sent", 
                          since_date: Optional[datetime] = None,
                          filter_addresses: Optional[List[str]] = None,
                          callback=None) -> List[Dict]:
        """Fetch sent emails (outgoing)"""
        emails = self.fetch_emails(folder=sent_folder, since_date=since_date, 
                                   filter_addresses=filter_addresses, callback=callback)
        
        # Mark as outgoing
        for email_data in emails:
            email_data["direction"] = "outgoing"
        
        return emails
