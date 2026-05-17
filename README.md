# HalalVest — Shariah-Compliant Indian Stock Screener

A production-grade platform screening the entire Nifty 500 for AAOIFI Shariah compliance, with real-time NSE market data integration.

## 🌐 Live: http://3.7.157.216

## Features
- **272 Halal Stocks** from Nifty 500, screened with AAOIFI standards
- **Real-time NSE data** — prices, volume, change% updated live
- **Interactive Dashboard** — Top Gainers/Losers/Volume/Market Cap tabs
- **Full Screener** — sortable, searchable, paginated stock table
- **Dual Pipeline** — Monthly screening + Daily market data updates

## Architecture

```
halal-stocks/
├── web/                    # Next.js 16 frontend
│   ├── app/
│   │   ├── page.js         # Landing page (client component)
│   │   ├── screener/       # Stock screener page
│   │   ├── methodology/    # AAOIFI methodology page
│   │   ├── api/stocks/     # API route (NSE + screening merge)
│   │   └── components/     # Navbar, Footer
│   └── public/data/        # Static data fallback
├── scripts/
│   ├── shariah_screener.py     # Monthly Shariah screening (Screener.in)
│   ├── daily_market_update.py  # Daily EOD update (NSE API)
│   ├── nse_market_data.py      # NSE API client
│   └── setup_cron.sh           # Cron installer
├── data/
│   ├── halal_stocks.json       # 272 halal stocks + market data
│   ├── screening_results.json  # Full screening audit
│   └── market_snapshot.json    # Nifty 500 EOD snapshot
└── deploy/
    ├── setup_server.sh         # EC2 first-time setup
    ├── deploy.sh               # Local → EC2 deploy
    ├── nginx/halalvest.conf    # Nginx reverse proxy
    └── systemd/halalvest.service
```

## Deployment

### First-time EC2 Setup
```bash
# SSH into EC2
ssh -i ~/Downloads/halal-stocks.pem ubuntu@3.7.157.216

# Clone repo
git clone https://github.com/rabeeh20/halah-stocks.git /home/ubuntu/halal-stocks

# Run setup
cd /home/ubuntu/halal-stocks
sudo bash deploy/setup_server.sh
```

### Subsequent Deployments
```bash
# From your Mac
bash deploy/deploy.sh
```

## Cron Schedules
| Pipeline | Schedule | Duration | Source |
|----------|----------|----------|--------|
| Daily Market Update | 3:45 PM IST, Mon-Fri | ~10 sec | NSE API |
| Monthly Screening | 1st of month, 6 AM | ~25 min | Screener.in |

## Tech Stack
- **Frontend**: Next.js 16, React 19, CSS (dark theme)
- **Backend**: Node.js API Routes, Python scripts
- **Server**: AWS EC2 (Ubuntu), Nginx, systemd
- **Data**: NSE India API, Screener.in
- **Database**: Supabase (planned: user watchlists)
