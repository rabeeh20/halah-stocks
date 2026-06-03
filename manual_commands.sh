#!/bin/bash
# ============================================================================
#  HalalVest — Manual Commands Cheat Sheet
#  Run these from your Mac terminal whenever you want.
# ============================================================================

EC2="ubuntu@3.7.157.216"
PEM="$HOME/Downloads/halal-stocks.pem"
SSH="ssh -i $PEM -o StrictHostKeyChecking=no $EC2"

echo "Usage: bash manual_commands.sh [command]"
echo ""
echo "Commands:"
echo "  screen     - Run Shariah screening NOW (replaces monthly cron)"
echo "  update     - Fetch NSE market data NOW (replaces daily cron)"
echo "  status     - Check what data files we have + last update times"
echo "  logs       - View recent logs from both pipelines"
echo "  deploy     - Pull latest code from GitHub + rebuild + restart"
echo "  restart    - Just restart the website"
echo ""

case "$1" in

  # ── Run Shariah Screening manually ─────────────────────────────────────────
  screen)
    echo "🕌 Running Shariah Screening on EC2..."
    echo "   This takes ~25 minutes. You can close terminal — it runs on server."
    echo ""
    $SSH "cd /home/ubuntu/halal-stocks/scripts && nohup /usr/bin/python3 shariah_screener.py >> /home/ubuntu/halal-stocks/logs/monthly_screening.log 2>&1 &
    echo 'Screening started in background. PID: '$!
    echo 'Check logs: tail -f /home/ubuntu/halal-stocks/logs/monthly_screening.log'"
    ;;

  # ── Fetch daily NSE market data manually ───────────────────────────────────
  update)
    echo "📊 Fetching NSE market data on EC2..."
    $SSH "cd /home/ubuntu/halal-stocks/scripts && /usr/bin/python3 daily_market_update.py --force 2>&1"
    echo ""
    echo "✅ Done! Refreshing website..."
    $SSH "sudo systemctl restart halalvest"
    echo "🌐 Visit: http://3.7.157.216"
    ;;

  # ── Check data file status ─────────────────────────────────────────────────
  status)
    echo "📋 Checking data file status on EC2..."
    $SSH 'python3 -c "
import json, os
from datetime import datetime

files = {
    \"halal_stocks.json\": \"/home/ubuntu/halal-stocks/data/halal_stocks.json\",
    \"market_snapshot.json\": \"/home/ubuntu/halal-stocks/data/market_snapshot.json\",
    \"screening_results.json\": \"/home/ubuntu/halal-stocks/data/screening_results.json\",
}

for name, path in files.items():
    if os.path.exists(path):
        mtime = os.path.getmtime(path)
        size = os.path.getsize(path) // 1024
        dt = datetime.fromtimestamp(mtime).strftime(\"%Y-%m-%d %H:%M IST\")
        with open(path) as f:
            data = json.load(f)
        extra = \"\"
        if \"total_halal\" in data:
            extra = f\"  Halal stocks: {data[\"total_halal\"]}\"
        if \"total_stocks\" in data:
            extra = f\"  Total stocks: {data[\"total_stocks\"]}\"
        last_upd = data.get(\"last_market_update\", data.get(\"screening_date\", \"-\"))
        print(f\"{name:30} {size:5} KB  Updated: {dt}  {extra}\")
        print(f\"  → Last data update: {last_upd}\")
    else:
        print(f\"{name:30} NOT FOUND\")
"'
    ;;

  # ── View logs ──────────────────────────────────────────────────────────────
  logs)
    echo "📝 Recent logs from EC2..."
    echo ""
    echo "=== Daily Market Update (last 20 lines) ==="
    $SSH "tail -20 /home/ubuntu/halal-stocks/logs/daily_market.log 2>/dev/null || echo 'No log yet'"
    echo ""
    echo "=== Monthly Screening (last 20 lines) ==="
    $SSH "tail -20 /home/ubuntu/halal-stocks/logs/monthly_screening.log 2>/dev/null || echo 'No log yet'"
    ;;

  # ── Deploy latest code ─────────────────────────────────────────────────────
  deploy)
    echo "🚀 Deploying latest code to EC2..."
    $SSH "cd /home/ubuntu/halal-stocks && git pull origin main && cd web && npm run build 2>&1 && sudo systemctl restart halalvest"
    echo "✅ Deployed! Visit: http://3.7.157.216"
    ;;

  # ── Just restart website ───────────────────────────────────────────────────
  restart)
    echo "🔄 Restarting website..."
    $SSH "sudo systemctl restart halalvest"
    echo "✅ Done! Visit: http://3.7.157.216"
    ;;

  *)
    echo "❌ Unknown command: $1"
    echo "Run: bash manual_commands.sh"
    ;;
esac
