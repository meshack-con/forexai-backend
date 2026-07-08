# CLAUDE.md — ForexAI Trading Bot

This file gives any AI coding assistant (Claude Code, Cursor, or otherwise) full context on this project. Read this before making any changes.

## Project Summary

ForexAI is a Forex trading automation backend built with **FastAPI**, **MetaTrader 5**, and **Supabase**. The core principle of this project is that **no strategy is allowed to trade real money until it proves itself statistically**. Backtesting, validation, and risk management come before live trading — not after.

The owner (Meshack) is a cybersecurity student building this as a personal project, with plans to eventually connect an Android app (already partially built separately) for monitoring.

**Note:** More than one AI assistant may work on this codebase across sessions (Claude Code, Cursor, etc.). This file is the shared source of truth — if you make a decision that changes something documented here, update the relevant section so the next assistant/session isn't working from stale information.

## Non-Negotiable Rules

These rules must be respected in all code changes, no exceptions, no shortcuts:

1. **No trade without a stop-loss.** Every row inserted into `trades` must have a non-null `stop_loss`. Enforced at the database level (`not null` constraint) and must also be enforced in application logic.
2. **No live trading without validation.** `risk_settings.allow_live` must never be manually set to `true` without a corresponding `backtest_results` row where `passed_validation = true`.
3. **`passed_validation` has exactly ONE source of truth: the database.** It is a `generated always as (...) stored` column on `backtest_results`. Application code must NEVER attempt to compute or insert this value manually — read it back from the DB response after insert.
   - **Formula was updated this session:** from `win_rate >= 55.0` to **`profit_factor >= 1.5 AND total_trades >= 30`**, because profit_factor properly accounts for risk:reward ratio, whereas win_rate alone does not. Keep the DB formula and any code comments about it in sync — never let them diverge.
4. **Risk management is layered, not optional.** Position sizing must be a percentage of account balance (not fixed lot size), and daily loss limits / max drawdown limits must be checked before any trade is allowed to execute.
5. **Every trade is tagged with a `mode`:** `backtest`, `demo`, or `live`. Never mix these.
6. **The backend uses `SUPABASE_SERVICE_ROLE_KEY`, never the anon key.** Never expose this key to any frontend, mobile app, or commit it to git.
7. **Live/demo strategy parameters come from `strategy_configs`, not hardcoded values.** Any script or service that opens real (even demo) trades must read `sl_atr_mult`, `tp_atr_mult`, `adx_threshold`, `strategy_version` from the `strategy_configs` table (`is_active = true`), never from ad-hoc constants. This is what "freezing" a validated strategy means in this project.
8. **Never re-tune parameters using the same data you validate against.** Any time strategy parameters are chosen via a sweep, confirm them with a proper out-of-sample time-split test (a different, non-overlapping historical window) before trusting the result. A single sweep-selected result should be treated as unconfirmed until this is done.

## Tech Stack

- **API:** FastAPI (Python)
- **Market data / execution:** MetaTrader5 Python package — **Windows-only**, requires a running MT5 terminal. Does NOT work on Linux (this matters for any future hosting/VPS decisions).
- **Database:** Supabase (PostgreSQL), accessed via `supabase-py`, service-role key
- **Analysis:** pandas, numpy

## Project Structure

```
FOREX/                          # repo root
├── forexai/
│   ├── main.py
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── logger.py
│   │   ├── api/routers/
│   │   │   ├── health.py
│   │   │   └── bot.py
│   │   ├── models/
│   │   │   ├── schemas.py
│   │   │   └── db.py            # all Supabase read/write functions
│   │   ├── services/
│   │   │   ├── backtester.py    # backtesting engine + get_latest_signal()
│   │   │   ├── risk_management.py
│   │   │   └── demo_engine.py   # live/demo trading loop logic
│   │   ├── mt5_client.py
│   │   └── supabase_client.py
├── scripts/                     # IMPORTANT: lives at repo root, NOT inside forexai/
│   ├── compare_strategies.py
│   ├── sweep_atr_combos.py
│   ├── sweep_atr_fine.py
│   ├── sweep_adx_threshold.py
│   ├── oos_check.py
│   ├── time_split_validation.py
│   └── run_demo_bot.py          # standalone worker, run this to trade demo
├── tests/
├── requirements.txt
├── README.md
├── CLAUDE.md                    # this file
└── .env                          # NEVER commit this
```

**Path gotcha to remember:** `scripts/` sits at the FOREX root, as a sibling of `forexai/`, not inside it. Scripts insert `forexai/` onto `sys.path` manually (see the `sys.path.insert(...)` line near the top of each script) so that `from app.services... import ...` resolves correctly. Always run scripts from the FOREX root, e.g. `python scripts/run_demo_bot.py` — not from inside `forexai/`, and not as `forexai/scripts/...` (that path doesn't exist).

## Database Schema (Supabase / PostgreSQL)

### `users`
`id (uuid, pk)`, `email`, `full_name`, `created_at`, `updated_at`

### `risk_settings`
`id (uuid, pk)`, `account_id (fk -> users.id)`, `position_size_pct`, `stop_loss_pct`, `take_profit_pct`, `daily_loss_limit_pct`, `max_drawdown_pct`, `max_concurrent_trades_per_symbol`, `allow_live (bool, default false)`, `updated_at`

### `backtest_results`
`id (uuid, pk)`, `account_id (fk)`, `symbol`, `period_start`, `period_end`, `win_rate`, `profit_factor`, `max_drawdown`, `sharpe_ratio`, `total_trades`, `winning_trades`, `losing_trades`, `passed_validation` (generated: **`profit_factor >= 1.5 AND total_trades >= 30`** — updated formula, see Current Status), `report_json`, `created_at`

### `trades`
`id (uuid, pk)`, `account_id (fk)`, `backtest_id (fk, nullable)`, `symbol`, `mode ('backtest'|'demo'|'live')`, `type ('buy'|'sell')`, `entry_time`, `exit_time`, `entry_price`, `exit_price`, `lot_size`, `stop_loss (NOT NULL)`, `take_profit`, `profit_loss`, `status ('open'|'closed'|'cancelled')`, `reason` (for `mode='demo'`/`live` rows, this field is repurposed to store the MT5 position ticket at open time, used later to detect closure — see `demo_engine.py`), `created_at`

### `bot_status`
`id (uuid, pk)`, `account_id (fk)`, `status ('running'|'stopped'|'validation-pending')`, `current_mode`, `last_checked`, `notes`

### `audit_logs`
`id (uuid, pk)`, `account_id (fk)`, `trade_id (fk, nullable)`, `event_type`, `message`, `metadata (jsonb)`, `created_at`

### `strategy_configs`
`id (uuid, pk)`, `account_id (fk)`, `symbol`, `timeframe (default 'M15')`, `strategy_version`, `sl_atr_mult`, `tp_atr_mult`, `adx_threshold`, `is_active (bool, default false)`, `created_at`. Unique on `(account_id, symbol)`. This is the frozen, validated parameter set the live/demo engine reads — see Non-Negotiable Rule 7.

RLS is enabled on all tables. Backend writes use the service-role key, which bypasses RLS by design.

## Current Status (update this section as the project progresses)

**Last updated:** July 2026 (strategy tuning + demo engine session)

- ✅ FastAPI backend running, Supabase + MT5 both connected and confirmed working end-to-end
- ✅ Validation gate formula CHANGED from `win_rate >= 55%` to **`profit_factor >= 1.5 AND total_trades >= 30`** (more sound: accounts for risk:reward, not just win rate). Database column was dropped and recreated with the new generated formula.
- ✅ Backtester was parameterized: `sl_atr_mult`, `tp_atr_mult`, `adx_threshold` are now constructor args (previously hardcoded), plus a `label` field so different parameter sweeps don't overwrite each other's rows in `backtest_results`.
- ✅ `Backtester._fetch_historical_data` and `.run()` now accept an optional `date_to` — needed to fetch a specific historical window (not just "last N days from now"), used for out-of-sample testing.
- ✅ Fixed a real bug in `_calculate_adx`: `pd.Series(plus_dm)` / `pd.Series(minus_dm)` were missing `index=df.index`, causing silent all-NaN columns and empty backtests for any `strategy_version >= 2`. Always pass the original datetime index when wrapping numpy arrays derived from `df` back into a new Series.
- ✅ **Winning parameter combo found and out-of-sample confirmed, for EURUSD M15 only:**
  - `strategy_version=4` (EMA9/21 crossover + RSI + EMA200 trend filter + ADX filter + ATR-based SL/TP + candle confirmation)
  - `sl_atr_mult=1.25`, `tp_atr_mult=2.0`, `adx_threshold=30.0`
  - Tuning window (last 365 days): win_rate 50.0%, profit_factor 1.62, Sharpe 3.23, 56 trades — **PASSED**
  - Out-of-sample window (older, non-overlapping ~240 days before the tuning window): win_rate 51.09%, profit_factor 1.75, Sharpe 3.53, 92 trades — **PASSED**, and actually *better* than the tuning window, which is a good sign the edge is real for this symbol.
  - ⚠️ **This combo does NOT generalize to GBPUSD** (tested: win_rate 36%, profit_factor 0.83 — FAILED). Treat these parameters as EURUSD-specific. Do not assume they transfer to other pairs without their own sweep + OOS validation.
  - These parameters have been inserted into `strategy_configs` for account `00000000-0000-0000-0000-000000000001`, symbol `EURUSD`, `is_active=true`.
- 🚧 **In progress: demo trading engine** (`app/services/demo_engine.py` + `scripts/run_demo_bot.py`). Standalone polling worker, deliberately NOT integrated into the FastAPI app (MT5's Python API is synchronous/blocking and doesn't mix well with uvicorn's reloader/threads). It:
  - Reads the active `strategy_configs` row for the symbol
  - Calls `Backtester.get_latest_signal()` (reuses the exact backtest indicator/signal logic, so live signals can't silently diverge from validated logic)
  - Applies risk management (position sizing from `risk_settings`, daily loss limit check) before opening a trade
  - Sends real orders to MT5 (demo account only — `allow_live` is still `false`) tagged with a fixed `MAGIC_NUMBER`
  - Tracks open trades in `trades` (`mode='demo'`) and detects closure by checking whether the MT5 position still exists, then reads the closing deal for exit price/profit
  - **Known limitations (documented in the file's docstring):** assumes one open position per symbol at a time; pip size (0.0001) and pip value ($10/lot) are hardcoded and only correct for EURUSD-like pairs, not JPY pairs; uses polling (default every 60s) rather than exact candle-close events; order filling mode is IOC and may need adjusting per broker.
  - ❌ **Not yet verified end-to-end.** Last session ended while debugging a path/terminal issue running `scripts/run_demo_bot.py` (see "Known Issues" below). Next session should start by getting this to run cleanly and watching at least one full poll cycle of logs before trusting it further.
- ❌ No live trading enabled anywhere (`allow_live=false` everywhere) — correct, do not change this without a deliberate, documented decision.
- ❌ No mobile app integration endpoints yet (balance, live trades, history) — planned for after the demo phase produces some track record.
- ❌ No CI/automated pipeline yet.
- 🖥️ A small ($4/mo) DigitalOcean droplet (Ubuntu/Linux) was created but is currently unused — it CANNOT run the demo/live engine since MT5 requires Windows. It may still be useful later for hosting the FastAPI web API itself (separated from the MT5-dependent parts), but that split hasn't been designed yet.

## Known Issues / Things to Check First in the Next Session

- `scripts/run_demo_bot.py` was throwing `FileNotFoundError` when run with a path like `forexai\scripts\run_demo_bot.py`. Fix: always `cd` to the FOREX root first and run `scripts\run_demo_bot.py` — `scripts/` is a sibling of `forexai/`, not nested inside it.
- Confirm the venv activates correctly in PowerShell (look for the `PS` prefix in the terminal prompt) before running any Python commands. `Activate.ps1` must be *executed* inside an already-open PowerShell window (e.g. `.venv\Scripts\Activate.ps1`) — it must never be double-clicked from File Explorer, and it will not run inside Command Prompt (`cmd.exe`), only PowerShell.
- Before trusting the demo engine, watch its logs for at least one full poll cycle without errors, and manually verify in the MT5 terminal / Supabase `trades` table that a demo order (if any signal fires) was placed correctly with a valid stop_loss.

## What NOT to do

- Do not enable `allow_live = true` for any account without a passing `backtest_results` row using the current (profit_factor-based) formula.
- Do not hardcode credentials anywhere in source files — everything sensitive goes in `.env` (gitignored).
- Do not remove the `stop_loss NOT NULL` constraint or bypass it in application code.
- Do not reintroduce `response.error` checks on Supabase responses — the installed postgrest-py version raises `APIError` exceptions directly instead.
- Do not assume deposit/withdrawal can be automated through the MT5 API — those are broker account-management operations, not trading-terminal operations.
- Do not assume a parameter combo validated on one symbol/timeframe applies to another without its own sweep + out-of-sample check (see the GBPUSD failure above).
- Do not run MetaTrader5-dependent code on a Linux host (e.g. a DigitalOcean droplet) — it will not work. MT5 requires Windows with the terminal installed and running.

## Typical Next Steps

When picking this project back up, in priority order:
1. Check `git log` and this file's "Current Status" / "Known Issues" sections to see what's done and what's unresolved.
2. Get `scripts/run_demo_bot.py` running cleanly from the FOREX root in an activated PowerShell venv, and watch real log output before trusting it.
3. Once the demo engine is confirmed stable for a few cycles, let it run during market hours for a meaningful stretch (days/weeks) before considering any live trading discussion.
4. If pursuing more symbols: repeat the full sweep + OOS validation process independently per symbol — do not reuse EURUSD's parameters elsewhere.
5. Always run existing tests (`tests/` folder) before and after changes to confirm nothing regresses.