#!/bin/bash

# ETL Weather Deployment Script
# Run this script on your VPS after cloning the repository

set -e  # Exit on error

echo "=== ETL Weather Deployment Script ==="
echo ""

# Configuration
APP_DIR="/var/www/etl-weather"
SERVICE_NAME="etl-weather"
NGINX_CONF="/etc/nginx/sites-available/etl-weather"
USER="www-data"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "Step 1: Installing system dependencies..."
apt-get update
apt-get install -y python3 python3-pip python3-venv nginx

echo ""
echo "Step 2: Setting up application directory..."
mkdir -p $APP_DIR
cd $APP_DIR

# If this is the first deployment, clone the repo
if [ ! -d ".git" ]; then
    echo "Cloning repository..."
    # You'll need to replace this with your actual repo URL
    read -p "Enter your git repository URL: " REPO_URL
    git clone $REPO_URL .
else
    echo "Pulling latest changes..."
    git pull
fi

echo ""
echo "Step 3: Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Step 4: Setting up environment file..."
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << 'EOF'
# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash,gemini-1.5-flash

# Optional: Add other environment variables here
EOF
    echo "⚠️  IMPORTANT: Edit /var/www/etl-weather/.env and add your GEMINI_API_KEY"
else
    echo ".env file already exists, skipping..."
fi

echo ""
echo "Step 5: Setting permissions..."
chown -R $USER:$USER $APP_DIR
chmod -R 755 $APP_DIR

echo ""
echo "Step 6: Installing systemd service..."
cp etl-weather.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

echo ""
echo "Step 7: Configuring nginx..."
cp nginx-etl-weather.conf $NGINX_CONF
# Replace placeholder domain with actual domain or IP
read -p "Enter your domain name or VPS IP address: " DOMAIN
sed -i "s/your-domain.com/$DOMAIN/g" $NGINX_CONF

# Create symlink if it doesn't exist
if [ ! -L "/etc/nginx/sites-enabled/etl-weather" ]; then
    ln -s $NGINX_CONF /etc/nginx/sites-enabled/
fi

# Test nginx config
nginx -t

if [ $? -eq 0 ]; then
    echo "Nginx configuration is valid, reloading..."
    systemctl reload nginx
else
    echo "Nginx configuration has errors, please fix them manually"
    exit 1
fi

echo ""
echo "Step 8: Configuring firewall (if UFW is installed)..."
if command -v ufw &> /dev/null; then
    ufw allow 'Nginx Full'
    ufw allow OpenSSH
    echo "Firewall configured"
else
    echo "UFW not installed, skipping firewall configuration"
fi

echo ""
echo "=== Deployment Complete! ==="
echo ""
echo "Service Status:"
systemctl status $SERVICE_NAME --no-pager

echo ""
echo "Next Steps:"
echo "1. Edit /var/www/etl-weather/.env and add your GEMINI_API_KEY"
echo "2. After editing .env, restart the service: sudo systemctl restart etl-weather"
echo "3. Access your app at: http://$DOMAIN"
echo ""
echo "Optional - Setup HTTPS with Let's Encrypt:"
echo "  sudo apt-get install certbot python3-certbot-nginx"
echo "  sudo certbot --nginx -d $DOMAIN"
echo ""
echo "Useful Commands:"
echo "  - View logs: sudo journalctl -u etl-weather -f"
echo "  - Restart service: sudo systemctl restart etl-weather"
echo "  - Check status: sudo systemctl status etl-weather"
echo "  - Redeploy: cd /var/www/etl-weather && git pull && sudo systemctl restart etl-weather"
