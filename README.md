# ForexAI Backend

A FastAPI-based forex trading bot backend with MetaTrader5 integration, backtesting, and Supabase persistence.

## Project Status

### ✅ Completed
- **MT5 Connection**: Successfully connects to MetaTrader5 (Demo account), retrieves account info and market data
- **Backtest Engine**: Full backtesting pipeline with EMA/RSI strategy, trade simulation, and performance metrics
- **Validation Gate**: Automated validation that flags backtests with win_rate < 55% as failed (safety mechanism)
- **Supabase Persistence**: Backtests and trades are stored in Supabase with proper:
  - Service role key authentication (backend writes bypass RLS)
  - Foreign key constraints (backtests → trades linkage)
  - Database-generated `passed_validation` field (computed from win_rate)
- **Error Handling**: Fixed postgrest-py compatibility (response.error → APIError exceptions)
- **Scripts**: Utility scripts for testing MT5 connection and running backtests without PYTHONPATH

### 🔄 In Progress / Not Started
- Live trading execution
- Frontend/mobile client
- Additional risk management rules
- Portfolio-level backtest aggregation

## Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Data**: MetaTrader5 Python (MT5 bridge)
- **Database**: Supabase (PostgreSQL)
- **Python Version**: 3.10+
- **Testing**: pytest

## Setup

1. **Clone and environment**:
   ```bash
   git clone <repo>
   cd FOREX
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. **Environment variables** (copy from `.env.sample`):
   ```bash
   cp .env.sample .env
   ```
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_SERVICE_ROLE_KEY`: Service role key from Supabase Project Settings > API
   - `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`, `MT5_PATH`: MetaTrader5 credentials

3. **Run backtest**:
   ```bash
   python scripts/run_eurusd_backtest.py
   ```

## Recent Fixes (2026-07-07)

- Fixed RLS (Row-Level Security) by using service role key for backend writes
- Replaced deprecated `response.error` checks with `try/except APIError` for postgrest compatibility
- Added sys.path bootstrap to scripts (no PYTHONPATH required)
- Verified full flow: MT5 data → Backtester → Supabase storage

## Key Endpoints

- `POST /api/bot/start` - Start backtest validation
- `GET /api/bot/status` - Check bot status
- `GET /api/bot/backtests` - List historical backtests
- `GET /api/bot/risk-settings` - Get risk configuration
- `PUT /api/bot/risk-settings` - Update risk configuration
- `GET /api/health` - Service health check
- `GET /api/health/supabase` - Supabase connectivity check

## Example Backtest Result

```
symbol: EUR/USD
timeframe: M15
period: 2025-08-13 to 2026-01-08 (180 days)
total_trades: 23
win_rate: 34.78%
passed_validation: False (< 55% threshold)
max_drawdown: 0.03
sharpe_ratio: 0.12
profit_factor: 1.02
```

## Next Steps

1. Implement live trading execution against demo/real accounts
2. Add more trading strategies (RSI, MACD, Bollinger Bands, etc.)
3. Build frontend dashboard (React/Vue)
4. Add mobile app support with proper RLS per user
5. Implement paper trading mode
6. Add risk management rules (daily loss limit, max drawdown, position sizing)
