# FX Signals — Cloudflare Worker

Signal-only M15 scanner for BTC/USD, XAU/USD, EUR/USD, GBP/USD, USD/JPY, USD/CAD and AUD/USD.

BUY requires all: price > EMA50 > EMA200; RSI 50–70; break above previous completed UTC-day high; bullish completed M15 candle.

SELL requires all: price < EMA50 < EMA200; RSI 30–50; break below previous completed UTC-day low; bearish completed M15 candle.

Otherwise: NO TRADE.

## Secret
In Cloudflare Worker → Settings → Variables and Secrets → Add → Secret:
`TWELVE_DATA_API_KEY`

Never put the API key in this repository.
