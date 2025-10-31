# 🚀 Deployment Guide

## Streamlit Cloud Deployment

### Prerequisites

1. GitHub repository with your code
2. Streamlit Cloud account (free at share.streamlit.io)

### Steps

1. **Prepare Repository**
   - Push all code to GitHub
   - Ensure `.gitignore` excludes `*.db` files
   - Include `requirements.txt`

2. **Configure Secrets**
   
   In Streamlit Cloud dashboard, add secrets in `.streamlit/secrets.toml` format:
   
   ```toml
   encryption_key = "your-32-character-base64-encryption-key-here"
   ```
   
   Generate a secure key:
   ```python
   import base64
   import secrets
   print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
   ```

3. **Deploy**
   - Go to share.streamlit.io
   - Click "New app"
   - Select your repository
   - Set main file path: `main.py`
   - Click "Deploy"

4. **First Time Setup**
   - After deployment, the app will create databases automatically
   - You'll need to create admin via Streamlit Cloud terminal or locally then upload DB

### Database Persistence on Streamlit Cloud

**Important**: Streamlit Cloud's file system is ephemeral. For production:

**Option A**: Use persistent storage
- Mount external storage (AWS S3, Google Cloud Storage)
- Use SQLite with cloud storage backend

**Option B**: Use cloud database
- Migrate to PostgreSQL/MySQL
- Use services like Supabase, PlanetScale, or Railway

**Option C**: Git-based persistence (simple but not ideal)
- Commit database files to Git (separate private repo)
- Pull on startup, push on updates
- Only for small-scale usage

### Recommended: PostgreSQL Migration

For production, migrate to PostgreSQL:

1. Install dependencies:
   ```
   pip install psycopg2-binary
   ```

2. Update `db_manager.py` to use PostgreSQL connection instead of SQLite

3. Use environment variables for connection strings

## Local Network Deployment

### Option 1: Windows Server

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create Windows Service**
   
   Use NSSM (Non-Sucking Service Manager):
   ```bash
   nssm install AuditEmailTracker "C:\Python314\python.exe" "-m" "streamlit" "run" "main.py" "--server.port=8501"
   ```

3. **Configure Firewall**
   - Open port 8501 (or your chosen port)
   - Allow incoming connections

4. **Access**
   - `http://server-ip:8501`

### Option 2: Docker

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY . .
   
   EXPOSE 8501
   
   CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
   ```

2. **Build and Run**
   ```bash
   docker build -t audit-email-tracker .
   docker run -p 8501:8501 -v $(pwd)/data:/app/data audit-email-tracker
   ```

### Option 3: Linux Server

1. **Install Dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Create Systemd Service**
   
   `/etc/systemd/system/audit-tracker.service`:
   ```ini
   [Unit]
   Description=Email Follow-Up Audit Tool
   After=network.target
   
   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/opt/audit-tracker
   Environment="PATH=/opt/audit-tracker/venv/bin"
   ExecStart=/opt/audit-tracker/venv/bin/streamlit run main.py --server.port=8501
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and Start**
   ```bash
   sudo systemctl enable audit-tracker
   sudo systemctl start audit-tracker
   ```

## Security Considerations

### For Production Deployment

1. **HTTPS Only**
   - Use reverse proxy (nginx, Apache, Caddy)
   - Configure SSL/TLS certificates
   - Force HTTPS redirects

2. **Authentication Hardening**
   - Implement rate limiting on login attempts
   - Add 2FA (Time-based OTP)
   - Session timeout configuration

3. **Database Encryption**
   - Encrypt database files at rest
   - Use strong encryption keys
   - Rotate keys periodically

4. **Email Credentials**
   - Use app-specific passwords
   - Never log credentials
   - Implement credential rotation

5. **Network Security**
   - Use VPN for access
   - Whitelist IP addresses
   - Enable firewall rules

6. **Monitoring**
   - Log all authentication attempts
   - Monitor sync failures
   - Alert on suspicious activity

## Backup Strategy

### Automated Backups

```bash
#!/bin/bash
# backup-script.sh

BACKUP_DIR="/backups/audit-tracker"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup databases
mkdir -p "$BACKUP_DIR/$DATE"
cp data/*.db "$BACKUP_DIR/$DATE/"

# Compress
tar -czf "$BACKUP_DIR/backup_$DATE.tar.gz" "$BACKUP_DIR/$DATE"
rm -rf "$BACKUP_DIR/$DATE"

# Keep only last 30 days
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +30 -delete
```

Add to crontab:
```
0 2 * * * /path/to/backup-script.sh
```

## Performance Optimization

### For Large Deployments

1. **Database Indexing**
   - Ensure indexes on email date, company_id
   - Regular VACUUM operations

2. **Caching**
   - Use Streamlit's `@st.cache_data` for expensive operations
   - Cache email sync results

3. **Pagination**
   - Implement pagination for large company lists
   - Limit email fetch batch sizes

4. **Async Operations**
   - Consider async email sync for multiple accounts
   - Background job processing

## Troubleshooting

### Common Deployment Issues

**Port Already in Use**
```bash
# Find process using port 8501
netstat -ano | findstr :8501
# Kill process
taskkill /PID <pid> /F
```

**Database Permissions**
- Ensure write permissions on `data/` directory
- Check file ownership

**Memory Issues**
- Increase swap space
- Limit email sync batch size
- Optimize queries

**Network Connectivity**
- Check firewall rules
- Verify DNS resolution
- Test IMAP/SMTP connectivity

## Monitoring & Logs

### Log Files

- Application logs: `logs/YYYYMMDD.log`
- Streamlit logs: Check Streamlit Cloud dashboard or systemd journal

### Health Checks

```python
# healthcheck.py
import sqlite3
from pathlib import Path

def check_health():
    # Check main database
    if not Path("data/main.db").exists():
        return False
    
    # Check database connectivity
    try:
        conn = sqlite3.connect("data/main.db")
        conn.execute("SELECT 1")
        conn.close()
        return True
    except:
        return False

if __name__ == "__main__":
    print("OK" if check_health() else "FAIL")
```

## Scaling Considerations

### Multi-Server Setup

For very large deployments:

1. **Load Balancer**
   - Distribute traffic across multiple instances
   - Use sticky sessions for Streamlit

2. **Shared Database**
   - Migrate to PostgreSQL
   - Use connection pooling

3. **Centralized Storage**
   - Store databases on network storage
   - Use Redis for session management

4. **Microservices**
   - Separate email sync service
   - API-based architecture
   - Queue-based processing

---

For assistance with deployment, contact your system administrator or DevOps team.
