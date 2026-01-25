# Investment Platform Deployment Guide

## Overview

This guide covers deploying the Investment Platform to an IBM z/OS mainframe environment with DB2 database and Python runtime.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation Steps](#installation-steps)
3. [Database Setup](#database-setup)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [Production Checklist](#production-checklist)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **Python:** 3.9 - 3.13 (tested and compatible)
- **Database:** IBM DB2 for z/OS (or DB2 LUW for development)
- **Memory:** Minimum 512MB RAM per worker
- **Disk:** 100MB for application, plus space for logs and cache

### Required Packages

Verify these packages are available:
- Flask and extensions
- SQLAlchemy with ibm_db_sa driver
- Dash and Plotly
- NumPy and Pandas

### Network Requirements

- Outbound HTTPS access to Yahoo Finance (for market data)
- Internal access to DB2 database
- Port 8000 (or configured port) open for web traffic

---

## Installation Steps

### 1. Clone the Repository

```bash
# On the mainframe or deployment server
cd /opt/apps
git clone <repository-url> investment-platform
cd investment-platform/investment_platform
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate (Unix/z/OS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install required packages
pip install --upgrade pip
pip install -r requirements.txt

# For mainframe, also install IBM DB2 driver
pip install ibm_db ibm_db_sa
```

### 4. Verify Installation

```bash
# Check Python version
python --version

# Verify key packages
python -c "import flask; print(f'Flask {flask.__version__}')"
python -c "import dash; print(f'Dash {dash.__version__}')"
python -c "import sqlalchemy; print(f'SQLAlchemy {sqlalchemy.__version__}')"

# Test DB2 connection (if driver installed)
python -c "import ibm_db; print('IBM DB2 driver OK')"
```

---

## Database Setup

### 1. Create Database Schema (DB2)

Connect to DB2 and create the schema if needed:

```sql
-- Create schema (if needed)
CREATE SCHEMA INVPLATFORM;
```

### 2. Initialize Database Tables

```bash
# Create all tables and initialize with default data
python scripts/init_database.py

# Or create tables AND fetch market data from Yahoo Finance
python scripts/init_database.py --with-market-data --days 365
```

### 3. Fetch Market Data from Yahoo Finance

```bash
# Fetch all symbols (last 30 days by default)
python scripts/fetch_yahoo_data.py

# Fetch 1 year of history for all stocks
python scripts/fetch_yahoo_data.py --days 365

# Check what's in the cache
python scripts/fetch_yahoo_data.py --status
```

---

## Configuration

### 1. Create Environment File

```bash
# Copy template
cp production.env.template production.env

# Edit with production values
vi production.env
```

### 2. Required Environment Variables

```bash
# Flask Configuration
FLASK_ENV=production
FLASK_APP=wsgi.py
DEBUG=False
SECRET_KEY=<generate-64-char-key>

# Database Configuration
DB2_DATABASE=INVPLATFORM
DB2_HOSTNAME=your-mainframe.company.com
DB2_PORT=50000
DB2_UID=your_db_user
DB2_PWD=your_db_password

# Logging
LOG_LEVEL=INFO
LOG_DIR=/var/log/investment-platform
```

### 3. Generate Secret Key

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Create Log Directory

```bash
sudo mkdir -p /var/log/investment-platform
sudo chown <app_user>:<app_group> /var/log/investment-platform
```

---

## Running the Application

### Development Mode

```bash
# Load environment
source production.env

# Run development server
python run.py
```

### Production with Gunicorn

```bash
# Load environment
export $(cat production.env | xargs)

# Start Gunicorn
gunicorn wsgi:app -c gunicorn.conf.py
```

### Production with uWSGI

```bash
# Start uWSGI
uwsgi --ini uwsgi.ini
```

### Using Systemd (Recommended)

Create service file `/etc/systemd/system/investment-platform.service`:

```ini
[Unit]
Description=Investment Platform
After=network.target

[Service]
User=appuser
Group=appgroup
WorkingDirectory=/opt/apps/investment-platform/investment_platform
Environment="PATH=/opt/apps/investment-platform/venv/bin"
EnvironmentFile=/opt/apps/investment-platform/production.env
ExecStart=/opt/apps/investment-platform/venv/bin/gunicorn wsgi:app -c gunicorn.conf.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable investment-platform
sudo systemctl start investment-platform
sudo systemctl status investment-platform
```

---

## Production Checklist

### Before Deployment

- [ ] All tests passing (`pytest tests/ -v`)
- [ ] Secret key generated and secured
- [ ] Database credentials secured
- [ ] Log directory created with proper permissions
- [ ] Firewall rules configured
- [ ] SSL certificate installed (if using HTTPS directly)

### Deployment

- [ ] Environment file configured
- [ ] Database migrations applied
- [ ] Application starts without errors
- [ ] Health endpoint responds: `curl http://localhost:8000/api/health`

### Post-Deployment

- [ ] Dashboard accessible: `http://hostname:8000/dashboard/`
- [ ] API responds correctly
- [ ] Logs being written
- [ ] Market data fetching works
- [ ] Auto-trading executes (if enabled)

---

## Monitoring

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/api/health

# Expected response:
# {"status": "ok", "timestamp": "...", "database": "connected"}
```

### Log Monitoring

```bash
# Watch application logs
tail -f /var/log/investment-platform/app.log

# Watch error logs
tail -f /var/log/investment-platform/error.log

# Watch trade audit log
tail -f /var/log/investment-platform/trades.log
```

### Performance Metrics

Monitor these metrics:
- API response times (should be <500ms)
- Database connection pool usage
- Memory usage per worker
- Cache hit rate for market data

### Alerts

Set up alerts for:
- Health endpoint failures
- Error log entries
- High response times
- Database connection failures
- Yahoo Finance API failures

---

## Troubleshooting

### Common Issues

#### Database Connection Fails

```
Error: Connection refused to DB2
```

**Solution:**
1. Verify DB2 is running
2. Check hostname and port in config
3. Verify credentials
4. Check network/firewall rules

```bash
# Test DB2 connection
python -c "
from sqlalchemy import create_engine
engine = create_engine('ibm_db_sa://user:pass@host:port/database')
conn = engine.connect()
print('Connection successful')
conn.close()
"
```

#### Market Data Not Fetching

```
Error: Failed to fetch data from Yahoo Finance
```

**Solution:**
1. Check outbound HTTPS connectivity
2. Verify no rate limiting (check for 429 errors)
3. Use fallback simulation mode if needed

```bash
# Test Yahoo Finance connectivity
curl -I https://query1.finance.yahoo.com/v8/finance/chart/AAPL
```

#### Application Won't Start

```
Error: Address already in use
```

**Solution:**
```bash
# Find process using port
lsof -i :8000

# Kill existing process
kill -9 <PID>

# Or change port in config
export GUNICORN_BIND=0.0.0.0:8001
```

#### High Memory Usage

**Solution:**
1. Reduce number of workers
2. Enable max_requests to recycle workers
3. Check for memory leaks in custom code

```python
# In gunicorn.conf.py
workers = 2  # Reduce from 4
max_requests = 500  # Restart workers periodically
```

### Getting Help

1. Check application logs
2. Enable debug logging temporarily
3. Review error messages in browser console
4. Contact support with:
   - Error messages
   - Log excerpts
   - Steps to reproduce

---

## Backup and Recovery

### Database Backup

```bash
# DB2 backup (adjust for your environment)
db2 backup database INVPLATFORM to /backup/
```

### Application Backup

```bash
# Backup configuration
cp production.env production.env.backup

# Backup logs
tar -czf logs-backup-$(date +%Y%m%d).tar.gz /var/log/investment-platform/
```

### Recovery Steps

1. Restore database from backup
2. Restore environment configuration
3. Restart application
4. Verify health endpoint
5. Check recent trades processed correctly

---

## Scaling

### Horizontal Scaling

1. Add more Gunicorn workers:
   ```python
   workers = 8  # Increase based on CPU cores
   ```

2. Use load balancer for multiple instances

3. Share sessions via Redis:
   ```python
   SESSION_TYPE = 'redis'
   SESSION_REDIS = redis.from_url('redis://localhost:6379')
   ```

### Database Scaling

1. Configure connection pooling
2. Add read replicas for queries
3. Optimize slow queries

---

## Security Hardening

See `docs/SECURITY.md` for detailed security configuration.

Quick checklist:
- [ ] HTTPS enabled
- [ ] Strong secret key
- [ ] Database credentials secured
- [ ] Rate limiting enabled
- [ ] CORS restricted to known domains
- [ ] Input validation on all endpoints
- [ ] Regular security updates applied
