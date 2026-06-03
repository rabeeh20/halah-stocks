#!/bin/bash
# ============================================================================
#  HalalVest — EC2 Server Setup Script
#  Run this ON the EC2 instance after cloning the repo.
#
#  Usage: sudo bash deploy/setup_server.sh
# ============================================================================

set -euo pipefail

echo "============================================"
echo "  HalalVest — EC2 Server Setup"
echo "  $(date)"
echo "============================================"

# ── Configuration ───────────────────────────────────────────────────────────
APP_DIR="/home/ubuntu/halal-stocks"
DEPLOY_DIR="${APP_DIR}/deploy"

# ── 1. System Update ───────────────────────────────────────────────────────
echo ""
echo "📦 Step 1: Updating system packages..."
apt-get update -y
apt-get upgrade -y

# ── 2. Install Node.js 20 LTS ──────────────────────────────────────────────
echo ""
echo "📦 Step 2: Installing Node.js 20 LTS..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi
echo "  Node.js: $(node --version)"
echo "  npm: $(npm --version)"

# ── 3. Install Python 3 ────────────────────────────────────────────────────
echo ""
echo "📦 Step 3: Installing Python 3..."
apt-get install -y python3 python3-pip python3-venv
echo "  Python: $(python3 --version)"

# Install Python dependencies
pip3 install requests --break-system-packages 2>/dev/null || pip3 install requests

# ── 4. Install Nginx ───────────────────────────────────────────────────────
echo ""
echo "📦 Step 4: Installing Nginx..."
apt-get install -y nginx

# ── 5. Install PM2 (Process Manager) ───────────────────────────────────────
echo ""
echo "📦 Step 5: Installing PM2..."
npm install -g pm2

# ── 6. Setup Application ───────────────────────────────────────────────────
echo ""
echo "🔧 Step 6: Setting up application..."

# Install Node.js dependencies
cd "${APP_DIR}/web"
npm ci --production=false
echo "  Dependencies installed"

# Build Next.js for production
npm run build
echo "  Next.js production build complete"

# ── 7. Configure Nginx ─────────────────────────────────────────────────────
echo ""
echo "🔧 Step 7: Configuring Nginx..."

# Remove default config
rm -f /etc/nginx/sites-enabled/default

# Copy our config
cp "${DEPLOY_DIR}/nginx/halalvest.conf" /etc/nginx/sites-available/halalvest
ln -sf /etc/nginx/sites-available/halalvest /etc/nginx/sites-enabled/halalvest

# Test nginx config
nginx -t

# Restart nginx
systemctl restart nginx
systemctl enable nginx
echo "  Nginx configured and running"

# ── 8. Setup Systemd Service ───────────────────────────────────────────────
echo ""
echo "🔧 Step 8: Setting up systemd service..."

cp "${DEPLOY_DIR}/systemd/halalvest.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable halalvest
systemctl start halalvest
echo "  Service started"

# ── 9. Setup Cron Jobs ─────────────────────────────────────────────────────
echo ""
echo "🕐 Step 9: Setting up cron jobs..."

# Create log directory
mkdir -p "${APP_DIR}/logs"
chown ubuntu:ubuntu "${APP_DIR}/logs"

# Set server timezone to IST so cron times match Indian market
timedatectl set-timezone Asia/Kolkata 2>/dev/null || true
echo "  Timezone: $(date +%Z)"

# Install cron jobs for ubuntu user
PYTHON_PATH=$(which python3)
CRON_CONTENT="# ── HalalVest: Daily Market Data Update (3:36 PM IST, Mon-Fri) ──
36 15 * * 1-5 cd ${APP_DIR}/scripts && ${PYTHON_PATH} daily_market_update.py >> ${APP_DIR}/logs/daily_market.log 2>&1

# ── HalalVest: Monthly Shariah Screening (1st of month, 12 AM IST) ──
0 0 1 * * cd ${APP_DIR}/scripts && ${PYTHON_PATH} shariah_screener.py >> ${APP_DIR}/logs/monthly_screening.log 2>&1

# ── HalalVest: Log rotation (weekly) ──
0 0 * * 0 find ${APP_DIR}/logs -name '*.log' -size +10M -exec truncate -s 0 {} \;
"

echo "$CRON_CONTENT" | crontab -u ubuntu -
echo "  Cron jobs installed for ubuntu user"

# ── 10. Set Permissions ────────────────────────────────────────────────────
echo ""
echo "🔒 Step 10: Setting permissions..."
chown -R ubuntu:ubuntu "${APP_DIR}"
chmod -R 755 "${APP_DIR}/scripts"

# ── 11. Open Firewall ──────────────────────────────────────────────────────
echo ""
echo "🔥 Step 11: Configuring firewall..."
ufw allow 22/tcp   2>/dev/null || true
ufw allow 80/tcp   2>/dev/null || true
ufw allow 443/tcp  2>/dev/null || true
echo "  Ports 22, 80, 443 allowed"

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  ✅ SERVER SETUP COMPLETE!"
echo "============================================"
echo ""
echo "  🌐 Website: http://3.7.157.216"
echo "  📊 API:     http://3.7.157.216/api/stocks"
echo ""
echo "  📅 Cron Jobs:"
echo "     Daily 3:36 PM IST (Mon-Fri)  → Market data update"
echo "     Monthly 1st 12:00 AM IST     → Shariah screening"
echo ""
echo "  🛠️  Management Commands:"
echo "     sudo systemctl status halalvest"
echo "     sudo systemctl restart halalvest"
echo "     sudo journalctl -u halalvest -f"
echo "     pm2 status (alternative)"
echo ""
echo "  📝 Logs:"
echo "     ${APP_DIR}/logs/daily_market.log"
echo "     ${APP_DIR}/logs/monthly_screening.log"
echo ""
