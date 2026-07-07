# ForexAI Trading Bot

Algorithmic Forex trading system built with **FastAPI**, **MetaTrader 5**, and **Supabase**. The system enforces backtest validation (minimum 55% win rate) and strict risk management controls before any strategy is allowed to trade with real funds.

## Overview

ForexAI is a backend service that connects to MetaTrader 5 to fetch market data, run trading strategies through rigorous backtesting, and only promote strategies to demo/live trading once they pass a statistical validation gate. Every trade is logged for full auditability, and risk parameters (position sizing, stop-loss, daily loss limits, drawdown limits) are enforced at both the application and database level.

## Key Features

- **MT5 Integration** — Direct connection to MetaTrader 5 for real market data and trade execution
- **Backtesting Engine** — Simulates strategies against historical data and produces win rate, profit factor, max drawdown, and Sharpe ratio
- **Validation Gate** — Strategies cannot go live until `win_rate >= 55%` (enforced as a database-generated column, not just application logic)
- **Risk Management** — Mandatory stop-loss on every trade, position sizing as a percentage of balance, daily loss limits, and max drawdown circuit breakers
- **Full Audit Trail** — Every trade and bot decision is logged to Supabase for later analysis
- **Row-Level Security** — Supabase RLS policies protect user data while the backend uses a service role for controlled writes

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python) |
| Trading Data | MetaTrader 5 (MetaTrader5 Python package) |
| Database | Supabase (PostgreSQL) |
| Data Analysis | pandas, numpy |

## Project Structure

```
forexai/
├── main.py                      # FastAPI entry point
├── app/
│   ├── core/
│   │   ├── config.py             # Environment configuration
│   │   └── logger.py             # Logging setup
│   ├── api/
│   │   └── routers/
│   │       ├── health.py         # Health check + Supabase check endpoints
│   │       └── bot.py            # Bot start/stop/status/risk endpoints
│   ├── models/
│   │   ├── schemas.py            # Pydantic request/response models
│   │   └── db.py                 # Supabase data access layer
│   ├── services/
│   │   ├── backtester.py         # Backtesting engine + validation gate
│   │   └── risk_management.py    # Position sizing & risk rules
│   ├── mt5_client.py             # MetaTrader 5 connection handler
│   └── supabase_client.py        # Supabase client initialization
├── scripts/                      # Standalone test/debug scripts
├── tests/                        # Unit & regression tests
├── requirements.txt
└── .env                          # Local secrets (not committed)
```

## Database Schema (Supabase)

| Table | Purpose |
|---|---|
| `users` | Account owners |
| `risk_settings` | Per-account risk configuration (position size %, stop loss %, daily loss limit, `allow_live` flag) |
| `backtest_results` | Backtest performance metrics, including the generated `passed_validation` column |
| `trades` | Every trade executed, tagged by `mode` (`backtest` / `demo` / `live`) |
| `bot_status` | Current bot state per account |
| `audit_logs` | Event log for every significant bot decision |

## Setup

### Prerequisites
- Python 3.10+
- MetaTrader 5 desktop terminal installed
- A Supabase project
- An MT5 demo (or live) trading account

### Installation

```bash
git clone https://github.com/<your-username>/forexai-backend.git
cd forexai-backend/forexai
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```dotenv
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

MT5_LOGIN=your-mt5-login
MT5_PASSWORD=your-mt5-password
MT5_SERVER=YourBroker-Server
MT5_PATH=C:/Program Files/MetaTrader 5/terminal64.exe
```

> **Warning:** `SUPABASE_SERVICE_ROLE_KEY` bypasses Row-Level Security. Never commit `.env`, never expose this key in a mobile/frontend app.

### Running the server

```bash
uvicorn main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for the interactive API documentation.

## Validation Gate Logic

No strategy is allowed to trade live capital until it passes backtesting:

1. Backtest is run against historical MT5 data
2. Results (win rate, profit factor, drawdown, Sharpe ratio) are stored in `backtest_results`
3. `passed_validation` is automatically computed by the database (`win_rate >= 55.0`)
4. `risk_settings.allow_live` can only be set to `true` for strategies with a passing backtest

## Roadmap

- [ ] Improve signal strategy beyond baseline EMA/RSI to consistently exceed 55% win rate
- [ ] Add demo/forward-testing phase before live promotion
- [ ] Build monitoring endpoints for mobile app integration (balance, live trades, history)
- [ ] Android client integration via Retrofit
- [ ] CI pipeline for automated regression testing

## Disclaimer

This project is for educational and personal use. Forex trading carries substantial risk of loss. No component of this system guarantees profitability, and live trading should only be enabled after thorough validation on demo accounts.