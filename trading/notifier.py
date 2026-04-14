"""
ReflexStrike — Telegram Notifier
──────────────────────────────────
Sends trade alerts and status updates to your Telegram account.

Setup:
  1. Open Telegram and search for @BotFather
  2. Send /newbot, follow the steps, copy the BOT TOKEN
  3. Start a chat with your new bot (press Start)
  4. Visit https://api.telegram.org/bot<TOKEN>/getUpdates in your browser
  5. Find "chat": {"id": 123456789} — that number is your CHAT_ID
  6. Paste both into trading/config.py
"""

import logging
from datetime import datetime, timezone

import aiohttp

logger = logging.getLogger(__name__)

_TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"


class Notifier:
    """Async Telegram notifier. All send_* methods are fire-and-forget safe."""

    def __init__(self, token: str, chat_id: str, enabled: bool = True):
        self.token    = token
        self.chat_id  = str(chat_id)
        self.enabled  = enabled

    # ── Core sender ───────────────────────────────────────────────────────────

    async def send(self, text: str) -> None:
        """Send a raw HTML-formatted message. Silently logs on failure."""
        if not self.enabled or not self.token or not self.chat_id:
            return
        url     = _TELEGRAM_URL.format(token=self.token)
        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.warning(f"Telegram error {resp.status}: {body[:200]}")
        except Exception as e:
            logger.warning(f"Telegram notification failed (non-critical): {e}")

    # ── Formatted messages ────────────────────────────────────────────────────

    async def bot_started(self, symbol: str, timeframe: str,
                          balance: float, currency: str) -> None:
        await self.send(
            f"🤖 <b>ReflexStrike Bot Online</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Symbol  : {symbol} | {timeframe}\n"
            f"Balance : {balance:,.2f} {currency}\n"
            f"Started : {_utc_now()}"
        )

    async def bot_stopped(self) -> None:
        await self.send(
            f"🔴 <b>ReflexStrike Bot Offline</b>\n"
            f"Stopped at {_utc_now()}"
        )

    async def trade_opened(
        self,
        direction: str,        # "BUY" or "SELL"
        symbol: str,
        entry: float,
        sl: float,
        tp: float,
        lot: float,
        risk_pct: float,
        details: dict,
    ) -> None:
        emoji   = "🟢" if direction == "BUY" else "🔴"
        sl_dist = abs(entry - sl)
        tp_dist = abs(entry - tp)

        score    = details["score"]
        score_bar = "●" * score + "○" * (3 - score)

        rsi_line  = "✅" if details["rsi_ok"] else "❌"

        if details["at_zone"] and details["zone"]:
            z = details["zone"]
            zone_line = f"✅ {z['type'].title()}  (strength {z['strength']}×)"
        else:
            zone_line = "❌ No zone"

        if details["near_fvg"] and details["fvg"]:
            f_ = details["fvg"]
            fvg_line = f"✅ {f_['type'].title()} FVG  (mid {f_['gap_mid']:.2f})"
        else:
            fvg_line = "❌ No FVG"

        if details["pa_confirmed"]:
            pa_line = f"✅ {details['candle_pattern'].replace('_', ' ').title()}"
        else:
            pa_line = "❌ No pattern"

        await self.send(
            f"{emoji} <b>{direction} {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Entry  : <b>{entry:.2f}</b>\n"
            f"SL     : {sl:.2f}  (−{sl_dist:.2f})\n"
            f"TP     : {tp:.2f}  (+{tp_dist:.2f})\n"
            f"Lot    : {lot}  |  Risk: {risk_pct}%\n"
            f"\n"
            f"<b>Confluence  {score_bar}  ({score}/3)</b>\n"
            f"RSI   : {rsi_line}\n"
            f"Zone  : {zone_line}\n"
            f"FVG   : {fvg_line}\n"
            f"PA    : {pa_line}\n"
            f"\n"
            f"🕐 {_utc_now()}"
        )

    async def trade_closed(self, direction: str, symbol: str,
                           reason: str = "Opposite signal") -> None:
        emoji = "🔵"
        await self.send(
            f"{emoji} <b>CLOSED {direction} {symbol}</b>\n"
            f"Reason : {reason}\n"
            f"🕐 {_utc_now()}"
        )

    async def ftmo_halt(self, reason: str) -> None:
        await self.send(
            f"🚨 <b>FTMO LIMIT — Trading Halted</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{reason}\n"
            f"No new trades will open today.\n"
            f"🕐 {_utc_now()}"
        )

    async def error(self, message: str) -> None:
        await self.send(
            f"⚠️ <b>Bot Error</b>\n"
            f"{message[:300]}"
        )


# ── Helper ────────────────────────────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
