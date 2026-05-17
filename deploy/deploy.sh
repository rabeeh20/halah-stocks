#!/bin/bash
# ============================================================================
#  HalalVest — Deploy from Local Machine to EC2
#  Run this from your Mac to push code and restart the server.
#
#  Usage: bash deploy/deploy.sh
# ============================================================================

set -euo pipefail

# ── Configuration ───────────────────────────────────────────────────────────
EC2_IP="3.7.157.216"
EC2_USER="ubuntu"
PEM_FILE="$HOME/Downloads/halal-stocks.pem"
REMOTE_DIR="/home/ubuntu/halal-stocks"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "============================================"
echo "  HalalVest — Deploying to EC2"
echo "  $(date)"
echo "============================================"
echo "  Local:  ${LOCAL_DIR}"
echo "  Remote: ${EC2_USER}@${EC2_IP}:${REMOTE_DIR}"
echo ""

# ── Validate PEM ────────────────────────────────────────────────────────────
if [ ! -f "$PEM_FILE" ]; then
    echo "❌ PEM file not found: $PEM_FILE"
    exit 1
fi
chmod 400 "$PEM_FILE"

SSH_CMD="ssh -i ${PEM_FILE} -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP}"
SCP_CMD="scp -i ${PEM_FILE} -o StrictHostKeyChecking=no"

# ── Step 1: Push to GitHub ──────────────────────────────────────────────────
echo "📤 Step 1: Pushing to GitHub..."
cd "$LOCAL_DIR"
git add -A
git commit -m "deploy: $(date '+%Y-%m-%d %H:%M')" 2>/dev/null || echo "  No changes to commit"
git push origin main 2>/dev/null || git push origin master
echo "  ✅ Code pushed"

# ── Step 2: Pull on EC2 ────────────────────────────────────────────────────
echo ""
echo "📥 Step 2: Pulling latest code on EC2..."
$SSH_CMD "cd ${REMOTE_DIR} && git pull origin main 2>/dev/null || git pull origin master"

# ── Step 3: Install dependencies ────────────────────────────────────────────
echo ""
echo "📦 Step 3: Installing dependencies..."
$SSH_CMD "cd ${REMOTE_DIR}/web && npm ci --production=false"

# ── Step 4: Build Next.js ───────────────────────────────────────────────────
echo ""
echo "🔨 Step 4: Building Next.js..."
$SSH_CMD "cd ${REMOTE_DIR}/web && npm run build"

# ── Step 5: Restart services ───────────────────────────────────────────────
echo ""
echo "🔄 Step 5: Restarting services..."
$SSH_CMD "sudo systemctl restart halalvest && sudo systemctl restart nginx"

# ── Step 6: Verify ──────────────────────────────────────────────────────────
echo ""
echo "🔍 Step 6: Verifying deployment..."
sleep 3
HTTP_STATUS=$($SSH_CMD "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000" 2>/dev/null || echo "000")

if [ "$HTTP_STATUS" = "200" ]; then
    echo "  ✅ Application is running (HTTP $HTTP_STATUS)"
else
    echo "  ⚠️  HTTP status: $HTTP_STATUS — checking logs..."
    $SSH_CMD "sudo journalctl -u halalvest --no-pager -n 20"
fi

echo ""
echo "============================================"
echo "  ✅ DEPLOYMENT COMPLETE!"
echo "  🌐 http://${EC2_IP}"
echo "============================================"
