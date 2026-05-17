#!/bin/bash
# ============================================================================
#  HalalVest — Cron Job Setup
#  
#  Two pipelines:
#    1. DAILY (3:45 PM IST, Mon-Fri)  → Market data refresh from NSE
#    2. MONTHLY (1st of month, 6 AM)  → Full Shariah screening from Screener.in
# ============================================================================

set -euo pipefail

# ── Configuration ───────────────────────────────────────────────────────────

SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPTS_DIR")"
PYTHON="$(which python3)"
LOG_DIR="${PROJECT_DIR}/logs"

# Create log directory
mkdir -p "$LOG_DIR"

echo "============================================"
echo "  HalalVest Cron Job Setup"
echo "============================================"
echo ""
echo "Project:  $PROJECT_DIR"
echo "Scripts:  $SCRIPTS_DIR"
echo "Python:   $PYTHON"
echo "Logs:     $LOG_DIR"
echo ""

# ── Define Cron Jobs ────────────────────────────────────────────────────────

# Daily Market Update: 3:45 PM IST, Monday–Friday
DAILY_CRON="45 15 * * 1-5 cd ${SCRIPTS_DIR} && ${PYTHON} daily_market_update.py >> ${LOG_DIR}/daily_market.log 2>&1"

# Monthly Shariah Screening: 1st of every month, 6:00 AM IST
MONTHLY_CRON="0 6 1 * * cd ${SCRIPTS_DIR} && ${PYTHON} shariah_screener.py >> ${LOG_DIR}/monthly_screening.log 2>&1"

# ── Install Cron Jobs ───────────────────────────────────────────────────────

echo "📋 Current crontab:"
crontab -l 2>/dev/null || echo "  (empty)"
echo ""

# Remove any existing HalalVest cron entries
EXISTING_CRON=$(crontab -l 2>/dev/null || true)
CLEAN_CRON=$(echo "$EXISTING_CRON" | grep -v "daily_market_update.py" | grep -v "shariah_screener.py" || true)

# Add new entries
NEW_CRON="${CLEAN_CRON}

# ── HalalVest: Daily Market Data Update (3:45 PM IST, Mon-Fri) ──
${DAILY_CRON}

# ── HalalVest: Monthly Shariah Screening (1st of month, 6 AM IST) ──
${MONTHLY_CRON}
"

# Install
echo "$NEW_CRON" | crontab -

echo "✅ Cron jobs installed!"
echo ""
echo "📅 Schedule:"
echo "  DAILY   → 3:45 PM IST, Mon–Fri  → daily_market_update.py"
echo "  MONTHLY → 1st of month, 6 AM     → shariah_screener.py"
echo ""
echo "📝 Logs:"
echo "  Daily:   ${LOG_DIR}/daily_market.log"
echo "  Monthly: ${LOG_DIR}/monthly_screening.log"
echo ""
echo "🔍 Verify with: crontab -l"
echo ""

# ── Verify ──────────────────────────────────────────────────────────────────

echo "📋 Updated crontab:"
crontab -l
