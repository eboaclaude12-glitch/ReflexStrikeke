"""
ReflexStrike Risk Manager
──────────────────────────
Handles:
  1. Position sizing — risk a fixed % of account per trade
  2. FTMO safety checks — enforce daily loss and max drawdown limits
"""

import logging

logger = logging.getLogger(__name__)


# ── Position Sizing ─────────────────────────────────────────────────────────

def calculate_lot_size(
    account_balance: float,
    risk_percent: float,
    sl_distance: float,          # distance in price (e.g. 1.50 for gold $1.50 stop)
    tick_value: float,           # value of 1 tick in account currency (from symbol info)
    tick_size: float,            # smallest price change (symbol_info.trade_tick_size)
    volume_min: float = 0.01,
    volume_max: float = 500.0,
    volume_step: float = 0.01,
) -> float:
    """
    Calculate lot size so that if price hits the stop loss, we lose exactly
    risk_percent % of account_balance.

    Formula:
        risk_amount   = balance × (risk_percent / 100)
        loss_per_lot  = (sl_distance / tick_size) × tick_value
        lot           = risk_amount / loss_per_lot

    Clamps result to [volume_min, volume_max] and rounds to volume_step.
    """
    if sl_distance <= 0:
        logger.warning("SL distance is zero or negative — using minimum lot.")
        return volume_min

    risk_amount = account_balance * (risk_percent / 100.0)
    ticks_in_sl = sl_distance / tick_size
    loss_per_lot = ticks_in_sl * tick_value

    if loss_per_lot <= 0:
        logger.warning("Computed loss_per_lot is zero — using minimum lot.")
        return volume_min

    raw_lot = risk_amount / loss_per_lot

    # Round to nearest valid step
    steps = round(raw_lot / volume_step)
    lot = round(steps * volume_step, 8)

    # Clamp
    lot = max(volume_min, min(volume_max, lot))
    lot = round(lot, len(str(volume_step).rstrip("0").split(".")[-1]))

    logger.debug(
        f"Lot calc | balance={account_balance:.2f} risk%={risk_percent} "
        f"sl_dist={sl_distance:.5f} loss_per_lot={loss_per_lot:.4f} → lot={lot}"
    )
    return lot


# ── FTMO Safety Guard ────────────────────────────────────────────────────────

class FTMOGuard:
    """
    Tracks daily P&L and total drawdown against FTMO limits.

    FTMO rules (standard challenge):
      • Daily loss limit : 5 % of initial balance  (hard stop)
      • Max drawdown     : 10 % of initial balance (hard stop)

    If either limit would be breached, is_trading_allowed() returns False
    and the bot must stop opening new trades for the session.
    """

    def __init__(
        self,
        initial_balance: float,
        daily_loss_limit_pct: float = 5.0,
        max_drawdown_pct: float = 10.0,
    ):
        self.initial_balance = initial_balance
        self.daily_loss_limit = initial_balance * (daily_loss_limit_pct / 100.0)
        self.max_drawdown_floor = initial_balance * (1 - max_drawdown_pct / 100.0)

        self._session_open_balance = initial_balance   # reset each day
        self._peak_balance = initial_balance

        logger.info(
            f"FTMO Guard initialised | initial={initial_balance:.2f} "
            f"daily_limit={self.daily_loss_limit:.2f} "
            f"drawdown_floor={self.max_drawdown_floor:.2f}"
        )

    def update(self, current_balance: float):
        """Call this at the start of each bar with the current account balance."""
        self._peak_balance = max(self._peak_balance, current_balance)

    def reset_daily(self, current_balance: float):
        """Call this at the start of each trading day (00:00 broker time)."""
        self._session_open_balance = current_balance
        logger.info(f"FTMO Guard daily reset | session open balance={current_balance:.2f}")

    def is_trading_allowed(self, current_balance: float) -> tuple[bool, str]:
        """
        Returns (allowed: bool, reason: str).
        allowed=False means DO NOT open any new trades.
        """
        # Daily loss check
        daily_loss = self._session_open_balance - current_balance
        if daily_loss >= self.daily_loss_limit:
            reason = (
                f"FTMO daily loss limit hit: lost {daily_loss:.2f} "
                f"(limit {self.daily_loss_limit:.2f})"
            )
            logger.warning(reason)
            return False, reason

        # Max drawdown check (from initial balance)
        if current_balance <= self.max_drawdown_floor:
            reason = (
                f"FTMO max drawdown hit: balance {current_balance:.2f} "
                f"≤ floor {self.max_drawdown_floor:.2f}"
            )
            logger.warning(reason)
            return False, reason

        return True, "OK"
