# ETL Weather - VPS Deployment Guide

Complete guide to deploy your ETL Weather application to a VPS (Ubuntu/Debian).

## Prerequisites

- Ubuntu 20.04+ or Debian 11+ VPS
- Root or sudo access
- Domain name (optional, but recommended)
- Git installed on VPS
- Your GEMINI_API_KEY ready

## Quick Deployment

### Method 1: Automated Script (Recommended)

1. **Clone repository on your VPS:**
```bash
ssh user@your-vps-ip
sudo su
cd /var/www
git clone https://github.com/Velubby/etl-weather.git
cd etl-weather
```

2. **Run deployment script:**
```bash
chmod +x deploy.sh
sudo ./deploy.sh
```

3. **Configure your API key:**
```bash
sudo nano /var/www/etl-weather/.env
# Add your GEMINI_API_KEY
```

4. **Restart the service:**
```bash
sudo systemctl restart etl-weather
```

5. **Access your app:**
```
http://your-vps-ip
```

---

### Method 2: Manual Setup

If you prefer step-by-step manual configuration:

#### 1. System Updates & Dependencies

```bash
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-venv nginx git
```

#### 2. Create Application Directory

```bash
sudo mkdir -p /var/www/etl-weather
sudo chown -R $USER:$USER /var/www/etl-weather
cd /var/www/etl-weather
```

#### 3. Clone Repository

```bash
git clone https://github.com/Velubby/etl-weather.git .
# or use git pull if already cloned
```

#### 4. Setup Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 5. Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

Add your configuration:
```env
GEMINI_API_KEY=your_actual_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp,gemini-1.5-flash
```

#### 6. Test the Application

```bash
source venv/bin/activate
uvicorn etl_weather.web:app --host 0.0.0.0 --port 8000
```

Visit `http://your-vps-ip:8000` to verify it works. Press Ctrl+C to stop.

#### 7. Setup Systemd Service

```bash
sudo cp etl-weather.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable etl-weather
sudo systemctl start etl-weather
sudo systemctl status etl-weather
```

#### 8. Configure Nginx

```bash
sudo cp nginx-etl-weather.conf /etc/nginx/sites-available/etl-weather
```

Edit the config with your domain/IP:
```bash
sudo nano /etc/nginx/sites-available/etl-weather
# Replace 'your-domain.com' with your actual domain or IP
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/etl-weather /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 9. Configure Firewall

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

---

## SSL/HTTPS Setup (Recommended)

### Using Let's Encrypt (Free SSL)

1. **Install Certbot:**
```bash
sudo apt-get install certbot python3-certbot-nginx
```

2. **Get SSL certificate:**
```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

3. **Auto-renewal:**
Certbot automatically sets up renewal. Test it:
```bash
sudo certbot renew --dry-run
```

---

## Maintenance Commands

### View Logs
```bash
# Application logs
sudo journalctl -u etl-weather -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### Service Management
```bash
# Restart service
sudo systemctl restart etl-weather

# Stop service
sudo systemctl stop etl-weather

# Start service
sudo systemctl start etl-weather

# Check status
sudo systemctl status etl-weather
```

### Update Deployment
```bash
cd /var/www/etl-weather
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart etl-weather
```

### Nginx Management
```bash
# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

# Restart nginx
sudo systemctl restart nginx
```

---

## Performance Tuning

### Adjust Worker Processes

Edit `/etc/systemd/system/etl-weather.service`:
```ini
# For VPS with 2 CPU cores, use 2 workers
ExecStart=/var/www/etl-weather/venv/bin/uvicorn etl_weather.web:app --host 0.0.0.0 --port 8000 --workers 2

# For VPS with 4 CPU cores, use 4 workers
ExecStart=/var/www/etl-weather/venv/bin/uvicorn etl_weather.web:app --host 0.0.0.0 --port 8000 --workers 4
```

After editing:
```bash
sudo systemctl daemon-reload
sudo systemctl restart etl-weather
```

### Nginx Caching (Optional)

Add to your nginx config inside `location /` block:
```nginx
# Cache API responses for 5 minutes
proxy_cache_valid 200 5m;
proxy_cache_key $scheme$request_method$host$request_uri;
```

---

## Troubleshooting

### Service Won't Start

1. Check logs:
```bash
sudo journalctl -u etl-weather -n 50
```

2. Check if port 8000 is already in use:
```bash
sudo lsof -i :8000
```

3. Verify Python environment:
```bash
cd /var/www/etl-weather
source venv/bin/activate
python -c "import etl_weather.web"
```

### Nginx 502 Bad Gateway

1. Ensure the app is running:
```bash
sudo systemctl status etl-weather
```

2. Check if port 8000 is listening:
```bash
sudo netstat -tulpn | grep 8000
```

3. Check nginx error log:
```bash
sudo tail -f /var/log/nginx/error.log
```

### Permission Errors

```bash
sudo chown -R www-data:www-data /var/www/etl-weather
sudo chmod -R 755 /var/www/etl-weather
```

### Python Module Not Found

```bash
cd /var/www/etl-weather
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart etl-weather
```

---

## Security Best Practices

1. **Keep system updated:**
```bash
sudo apt-get update && sudo apt-get upgrade -y
```

2. **Configure fail2ban (optional):**
```bash
sudo apt-get install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

3. **Disable root SSH login:**
Edit `/etc/ssh/sshd_config`:
```
PermitRootLogin no
```

4. **Use SSH keys instead of passwords**

5. **Set up automatic security updates:**
```bash
sudo apt-get install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

---

## Monitoring (Optional)

### Simple uptime monitoring with cron

Create a monitoring script:
```bash
sudo nano /usr/local/bin/check-etl-weather.sh
```

Add:
```bash
#!/bin/bash
if ! systemctl is-active --quiet etl-weather; then
    systemctl restart etl-weather
    echo "ETL Weather service was down, restarted at $(date)" >> /var/log/etl-weather-monitor.log
fi
```

Make executable and add to cron:
```bash
sudo chmod +x /usr/local/bin/check-etl-weather.sh
sudo crontab -e
# Add: */5 * * * * /usr/local/bin/check-etl-weather.sh
```

---

## Backup Strategy

### Backup script

```bash
#!/bin/bash
BACKUP_DIR="/backup/etl-weather"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cd /var/www/etl-weather

# Backup .env and data
tar -czf $BACKUP_DIR/etl-weather-$DATE.tar.gz .env data/

# Keep only last 7 backups
find $BACKUP_DIR -name "etl-weather-*.tar.gz" -mtime +7 -delete
```

---

## Support

If you encounter issues:
1. Check logs: `sudo journalctl -u etl-weather -f`
2. Verify .env configuration
3. Ensure GEMINI_API_KEY is valid
4. Check VPS resources (RAM, CPU, disk space)

## Quick Reference URLs

- Application: `http://your-domain.com`
- API Docs: `http://your-domain.com/docs`
- Health Check: `http://your-domain.com/`

---

## Architecture

```
Internet → Nginx (Port 80/443) → FastAPI App (Port 8000) → Python Backend
                ↓
          Static Files Served Directly
```

**Components:**
- **Nginx**: Reverse proxy, SSL termination, static file serving
- **Systemd**: Process management, auto-restart on failure
- **Uvicorn**: ASGI server running FastAPI
- **Virtual Environment**: Isolated Python dependencies
