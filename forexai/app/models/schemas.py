from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class BacktestResultCreate(BaseModel):
    account_id: str
    symbol: str
    period_start: datetime
    period_end: datetime
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    passed_validation: bool
    report_json: dict


class BacktestResult(BaseModel):
    id: str
    account_id: str
    symbol: str
    period_start: datetime
    period_end: datetime
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    passed_validation: bool
    report_json: dict
    created_at: datetime

    class Config:
        orm_mode = True
