"""
Simple logging utility for the application
"""
import logging
from datetime import datetime
from pathlib import Path
import os

def _is_cloud_mode() -> bool:
    try:
        import streamlit as st
        # Default to True if secrets exist but key missing
        return bool(st.secrets.get("cloud", True))
    except Exception:
        return False


def setup_logger(name: str = "audit_tracker") -> logging.Logger:
    """Set up application logger"""
    cloud = _is_cloud_mode()
    if not cloud:
        # Only create logs directory when not on cloud
        Path("logs").mkdir(exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Console handler (always)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    ch.setFormatter(formatter)
    
    # File handler only when not on cloud
    if not cloud:
        log_file = f"logs/{datetime.now().strftime('%Y%m%d')}.log"
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger
