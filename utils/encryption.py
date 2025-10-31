"""
Encryption utilities for storing email credentials securely.
Uses Fernet (symmetric encryption) from cryptography library.
"""
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import streamlit as st


def _is_cloud_mode() -> bool:
    try:
        # Default True if running with secrets available
        return bool(st.secrets.get("cloud", True))
    except Exception:
        return False


def get_encryption_key() -> bytes:
    """
    Get encryption key from Streamlit secrets or generate one.
    For production, store this in .streamlit/secrets.toml
    """
    # Try to get from Streamlit secrets
    try:
        key = st.secrets.get("encryption_key", None)
        if key:
            return key.encode()
    except Exception:
        # st.secrets not available (likely local dev)
        pass

    # If cloud mode, do not allow fallback
    if _is_cloud_mode():
        raise RuntimeError("Missing encryption_key in Streamlit secrets. Set it in .streamlit/secrets.toml on the host.")

    # Local dev fallback (NOT SECURE): derive a key from static password/salt
    password = b"audit_email_tracker_2025"
    salt = b"rbrgroup_salt_2025"

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key


def encrypt_email_config(imap_host: str, imap_port: int, smtp_host: str, 
                         smtp_port: int, email: str, password: str) -> str:
    """Encrypt email configuration to store in database"""
    config = {
        "imap_host": imap_host,
        "imap_port": imap_port,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "email": email,
        "password": password
    }
    
    key = get_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(json.dumps(config).encode())
    return base64.b64encode(encrypted).decode()


def decrypt_email_config(encrypted_config: str) -> dict:
    """Decrypt email configuration from database"""
    key = get_encryption_key()
    f = Fernet(key)
    
    encrypted_bytes = base64.b64decode(encrypted_config.encode())
    decrypted = f.decrypt(encrypted_bytes)
    return json.loads(decrypted.decode())
