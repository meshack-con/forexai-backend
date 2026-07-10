# ForexAI Trading Bot

Algorithmic Forex trading system built with **FastAPI**, **MetaTrader 5**, and **Supabase**. The system enforces backtest validation and strict risk management controls before any strategy is allowed to trade — first in a demo account, and only much later, if ever, with real funds.

## Overview

ForexAI connects to MetaTrader 5 to fetch market data, runs trading strategies through rigorous backtesting with out-of-sample validation, and only promotes strategies to demo trading once they pass a statistical validation gate. Every trade is logged for full auditability, and risk parameters (position sizing, stop-loss, daily loss limits, drawdown limits) are enforced at both the application and database level.

**Current stage: demo trading engine is being built and verified.** A validated strategy configuration exists for EURUSD (see below); no live trading has been enabled anywhere in this project.

## Key Features

- **MT5 Integration** — Direct connection to MetaTrader 5 for real market data and trade execution
- **Backtesting Engine** — Simulates strategies against historical data, with configurable ATR-based stop-loss/take-profit and ADX trend-strength filtering
- **Profit-Factor Validation Gate** — Strategies must achieve `profit_factor >= 1.5` over at least 30 trades before being considered validated. This replaced an earlier win-rate-only gate, because profit factor properly accounts for risk:reward ratio rather than win rate alone.
- **Out-of-Sample Testing** — Winning parameter combinations are re-tested on a separate, non-overlapping historical window before being trusted, to guard against overfitting to a single backtest period.
- **Frozen Strategy Configs** — Validated parameters are locked into a `strategy_configs` table per symbol; the live/demo engine only ever reads from there, never from ad-hoc constants.
- **Demo Trading Engine** — A standalone worker process that polls for new signals using the exact same logic as the backtester, applies risk management, and places real orders on a demo MT5 account.
- **Risk Management** — Mandatory stop-loss on every trade, position sizing as a percentage of balance, daily loss limits, and max drawdown circuit breakers.
- **Full Audit Trail** — Every trade and bot decision is logged to Supabase for later analysis.
- **Row-Level Security** — Supabase RLS policies protect user data while the backend uses a service role for controlled writes.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python) |
| Trading Data / Execution | MetaTrader5 Python package (**Windows-only** — does not run on Linux) |
| Database | Supabase (PostgreSQL) |
| Data Analysis | pandas, numpy |

## Project Structure

```
FOREX/                          # repo root
├── forexai/
│   ├── main.py                   # FastAPI entry point
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── logger.py
│   │   ├── api/routers/
│   │   │   ├── health.py         # GET /api/health, /api/health/supabase
│   │   │   └── bot.py            # POST /api/bot/start, /stop, GET /status, /backtests, /risk-settings
│   │   ├── models/
│   │   │   ├── schemas.py
│   │   │   └── db.py             # all Supabase read/write functions
│   │   ├── services/
│   │   │   ├── backtester.py     # backtesting engine + get_latest_signal()
│   │   │   ├── risk_management.py
│   │   │   └── demo_engine.py    # live/demo trading loop logic
│   │   ├── mt5_client.py
│   │   └── supabase_client.py
├── scripts/                      # NOTE: sits at repo root, sibling of forexai/, not inside it
│   ├── compare_strategies.py     # runs multiple strategy_version backtests side by side
│   ├── sweep_atr_combos.py       # sweeps SL/TP ATR multiplier combinations
│   ├── sweep_atr_fine.py
│   ├── sweep_adx_threshold.py    # sweeps ADX trend-strength threshold
│   ├── oos_check.py              # cross-symbol sanity check
│   ├── time_split_validation.py  # proper out-of-sample time-split validation
│   └── run_demo_bot.py           # standalone worker — run this to trade demo
├── tests/
├── requirements.txt
├── README.md
├── CLAUDE.md                     # detailed AI-assistant context (rules, schema, status)
└── .env                           # never committed
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
| `strategy_configs` | Frozen, validated strategy parameters per account+symbol — the single source of truth the demo/live engine reads from |

## Setup

### Prerequisites
- Python 3.10+
- MetaTrader 5 desktop terminal installed and running
- A Supabase project
- An MT5 demo (or live) trading account

### Installation

```powershell
git clone https://github.com/<your-username>/forexai-backend.git
cd forexai-backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file at the repo root:

```dotenv
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

MT5_LOGIN=your-mt5-login
MT5_PASSWORD=your-mt5-password
MT5_SERVER=YourBroker-Server
MT5_PATH=C:/Program Files/MetaTrader 5/terminal64.exe
```

> **Warning:** `SUPABASE_SERVICE_ROLE_KEY` bypasses Row-Level Security. Never commit `.env`, never expose this key in a mobile/frontend app.

### Running the API server

```powershell
cd forexai
uvicorn main:app --reload
```
Visit `http://127.0.0.1:8000/docs` for interactive API documentation.

### Running the demo trading bot

The demo engine runs as a **separate, standalone worker** — it does not need the API server running, but it does need the MT5 desktop terminal open and logged in.

```powershell
cd C:\path\to\FOREX
.venv\Scripts\Activate.ps1
& '.venv\Scripts\python.exe' scripts\run_demo_bot.py
```

Leave this running in its own terminal window while the market is open. It polls every 60 seconds, prints its status to the console, and places real (demo-account) orders when a validated signal appears.

## Validation Gate Logic

No strategy is allowed to trade even demo capital until it passes a two-stage check:

1. **Backtest gate:** `profit_factor >= 1.5 AND total_trades >= 30`, computed automatically as a generated column on `backtest_results` — application code never sets this value directly.
2. **Out-of-sample confirmation:** the same parameters are re-tested on an older, non-overlapping historical window. If performance collapses on that window, the result is treated as overfit and rejected, regardless of how good the original backtest looked.

Only after both checks pass are parameters written into `strategy_configs` with `is_active = true`.

## Current Validated Strategy

| Symbol | Timeframe | SL (×ATR) | TP (×ATR) | ADX min | Tuning-window PF | OOS-window PF |
|---|---|---|---|---|---|---|
| EURUSD | M15 | 1.25 | 2.0 | 30 | 1.62 | 1.75 |

⚠️ This configuration is **EURUSD-specific**. It was tested on GBPUSD and failed (profit_factor 0.83) — parameters must be independently swept and validated per symbol, never assumed to transfer.

## Roadmap

- [x] Backtesting engine with configurable ATR/ADX-based strategy
- [x] Profit-factor-based validation gate (replacing win-rate-only gate)
- [x] Out-of-sample time-split validation
- [x] EURUSD strategy parameters found, validated, and frozen
- [ ] Verify the demo trading engine runs reliably end-to-end over multiple days
- [ ] Repeat sweep + OOS validation for additional symbols (e.g. GBPUSD, USDJPY) independently
- [ ] Build monitoring endpoints for mobile app integration (balance, live trades, history)
- [ ] Android client integration via Retrofit
- [ ] CI pipeline for automated regression testing

## Disclaimer

This project is for educational and personal use. Forex trading carries substantial risk of loss. No component of this system guarantees profitability. Live trading is not enabled and should only be considered after a sustained, successful demo-trading track record.