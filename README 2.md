# Green Bull Signal App — Netlify V2

This is a signal-analysis app, not an automated trading robot.

## Critical deployment requirement
Deploy the **entire project**, not only `index.html`. The folder `netlify/functions/signal.js` is required.

The frontend calls the function directly at:
`/.netlify/functions/signal`

A `_redirects` fallback is also included for `/api/signal`.

## Included markets
BTC/USD, Gold (XAU/USD), EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD, USD/CHF and NZD/USD.

## Data source
The Netlify Function retrieves candle data server-side from Yahoo Finance chart endpoints, avoiding browser CORS restrictions. No API key is required for this route.

## Signal engine
Seven confirmations are evaluated: EMA trend, MACD, ADX, breakout/breakdown, RSI/momentum, news-neutral filter, and Bollinger Band confirmation. Default threshold is 5/7.

The app may still return HOLD when the conditions are mixed. It does not guarantee profitable trades.
