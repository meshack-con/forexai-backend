# CLAUDE.md — ForexAI Trading Bot

This file gives any AI coding assistant (Claude Code or otherwise) full context on this project. Read this before making any changes.

## Project Summary

ForexAI is a Forex trading automation backend built with **FastAPI**, **MetaTrader 5**, and **Supabase**. The core principle of this project is that **no strategy is allowed to trade real money until it proves itself statistically**. Backtesting, validation, and risk management come before live trading — not after.

The owner (Meshack) is a cybersecurity student building this as a personal project, with plans to eventually connect an Android app (already partially built separately) for monitoring.

## Non-Negotiable Rules

These rules must be respected in all code changes, no exceptions, no shortcuts:

1. **No trade without a stop-loss.** Every row inserted into `trades` must have a non-null `stop_loss`. This is enforced at the database level (`not null` constraint) and must also be enforced in application logic.
2. **No live trading without validation.** `risk_settings.allow_live` must never be manually set to `true` without a corresponding `backtest_results` row where `passed_validation = true` (i.e. `win_rate >= 55.0`).
3. **`passed_validation` has exactly ONE source of truth: the database.** It is a `generated always as (win_rate >= 55.0) stored` column on `backtest_results`. Application code must NEVER attempt to compute or insert this value manually — read it back from the DB response after insert.
4. **Risk management is layered, not optional.** Position sizing must be a percentage of account balance (not fixed lot size), and daily loss limits / max drawdown limits must be checked before any trade is allowed to execute.
5. **Every trade is tagged with a `mode`:** `backtest`, `demo`, or `live`. Never mix these — a query or report must always be able to isolate which mode produced which data.
6. **The backend uses `SUPABASE_SERVICE_ROLE_KEY`, never the anon key.** This key bypasses RLS and must never be exposed to any frontend, mobile app, or committed to git.

## Tech Stack

- **API:** FastAPI (Python)
- **Market data / execution:** MetaTrader5 Python package, connecting to a real MT5 terminal installed locally
- **Database:** Supabase (PostgreSQL), accessed via `supabase-py`, service-role key
- **Analysis:** pandas, numpy

## Project Structure

```
forexai/
├── main.py
├── app/
│   ├── core/
│   │   ├── config.py
│   │   └── logger.py
│   ├── api/routers/
│   │   ├── health.py        # GET /api/health, GET /api/health/supabase
│   │   └── bot.py           # POST /api/bot/start, /stop, GET /status, /backtests, /risk-settings
│   ├── models/
│   │   ├── schemas.py       # Pydantic models
│   │   └── db.py            # All Supabase read/write functions
│   ├── services/
│   │   ├── backtester.py    # Backtesting engine + strategy logic
│   │   └── risk_management.py
│   ├── mt5_client.py
│   └── supabase_client.py
├── scripts/                 # Standalone manual test scripts (not part of the API)
├── tests/                   # Automated regression tests (unittest)
├── requirements.txt
└── .env                      # NEVER commit this
```

## Database Schema (Supabase / PostgreSQL)

### `users`
`id (uuid, pk)`, `email`, `full_name`, `created_at`, `updated_at`

### `risk_settings`
`id (uuid, pk)`, `account_id (fk -> users.id)`, `position_size_pct`, `stop_loss_pct`, `take_profit_pct`, `daily_loss_limit_pct`, `max_drawdown_pct`, `max_concurrent_trades_per_symbol`, `allow_live (bool, default false)`, `updated_at`

### `backtest_results`
`id (uuid, pk)`, `account_id (fk)`, `symbol`, `period_start`, `period_end`, `win_rate`, `profit_factor`, `max_drawdown`, `sharpe_ratio`, `total_trades`, `winning_trades`, `losing_trades`, `passed_validation (generated: win_rate >= 55.0)`, `report_json`, `created_at`

### `trades`
`id (uuid, pk)`, `account_id (fk)`, `backtest_id (fk, nullable)`, `symbol`, `mode ('backtest'|'demo'|'live')`, `type ('buy'|'sell')`, `entry_time`, `exit_time`, `entry_price`, `exit_price`, `lot_size`, `stop_loss (NOT NULL)`, `take_profit`, `profit_loss`, `status ('open'|'closed'|'cancelled')`, `reason`, `created_at`

### `bot_status`
`id (uuid, pk)`, `account_id (fk)`, `status ('running'|'stopped'|'validation-pending')`, `current_mode`, `last_checked`, `notes`

### `audit_logs`
`id (uuid, pk)`, `account_id (fk)`, `trade_id (fk, nullable)`, `event_type`, `message`, `metadata (jsonb)`, `created_at`

RLS is enabled on all tables. Backend writes use the service-role key, which bypasses RLS by design.

## Current Status (update this section as the project progresses)

**Last updated:** July 2026

- ✅ FastAPI backend scaffolded and running (`uvicorn main:app --reload`)
- ✅ Supabase connected via service-role key, schema fully created
- ✅ MT5 connected successfully to a real demo account
- ✅ End-to-end flow works: MT5 historical data → backtester → Supabase persistence
- ✅ Validation gate confirmed working correctly (rejects strategies under 55% win rate)
- ⚠️ Current baseline strategy (EMA crossover + RSI) achieved only ~34.78% win rate on EUR/USD, M15, 180 days — **does not pass validation yet**
- ❌ No demo or live trading has been enabled — project is strictly in the backtesting/strategy-development phase
- ❌ No CI/automated pipeline yet
- ❌ No mobile app integration endpoints yet (balance, live trades, history)

## What NOT to do

- Do not enable `allow_live = true` for any account without a passing `backtest_results` row.
- Do not hardcode credentials anywhere in source files — everything sensitive goes in `.env` (gitignored).
- Do not remove the `stop_loss NOT NULL` constraint or bypass it in application code.
- Do not reintroduce `response.error` checks on Supabase responses — the installed postgrest-py version raises `APIError` exceptions directly instead.
- Do not assume deposit/withdrawal can be automated through the MT5 API — those are broker account-management operations, not trading-terminal operations.

## Typical Next Steps

When picking this project back up, in priority order:
1. Check `git log` and this file's "Current Status" section to see what's done.
2. If continuing strategy development: focus on improving `backtester.py`'s signal logic to consistently exceed 55% win rate before touching anything else.
3. If continuing infra work: build out monitoring endpoints (`/api/trades/live`, `/api/account/balance`) for future mobile app integration.
4. Always run existing tests (`tests/` folder) before and after changes to confirm nothing regresses.