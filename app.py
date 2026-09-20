# ============================================================
# USD FX QUANT SIGNAL ENGINE V2
# ============================================================

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf

st.set_page_config(
    page_title="USD FX Quant Signal Engine V2",
    page_icon="📈",
    layout="wide"
)

st.title("📈 USD FX Quant Signal Engine V2")
st.caption("Multi-pair technical scanner with trend, momentum, volatility and breakout confirmation.")

PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "USD/CHF": "CHF=X",
    "AUD/USD": "AUDUSD=X",
    "NZD/USD": "NZDUSD=X",
    "USD/CAD": "CAD=X",
}

@st.cache_data(ttl=300)
def download_data(symbol, period="1y", interval="1h"):
    try:
        df = yf.download(symbol, period=period, interval=interval,
                          auto_adjust=False, progress=False)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        required = ["Open", "High", "Low", "Close"]
        if not all(c in df.columns for c in required):
            return pd.DataFrame()
        cols = required + (["Volume"] if "Volume" in df.columns else [])
        df = df[cols].copy().dropna()
        return df
    except Exception:
        return pd.DataFrame()

def calculate_indicators(df):
    df = df.copy()

    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()

    prev = df["Close"].shift(1)
    tr1 = df["High"] - df["Low"]
    tr2 = (df["High"] - prev).abs()
    tr3 = (df["Low"] - prev).abs()
    df["TR"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["ATR"] = df["TR"].rolling(14).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_HIST"] = df["MACD"] - df["MACD_SIGNAL"]

    high_diff = df["High"].diff()
    low_diff = -df["Low"].diff()
    plus_dm = pd.Series(np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0), index=df.index)
    minus_dm = pd.Series(np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0), index=df.index)
    plus_di = 100 * plus_dm.rolling(14).mean() / (df["ATR"] + 1e-10)
    minus_di = 100 * minus_dm.rolling(14).mean() / (df["ATR"] + 1e-10)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
    df["ADX"] = dx.rolling(14).mean()
    df["+DI"] = plus_di
    df["-DI"] = minus_di

    df["Previous_High"] = df["High"].rolling(20).max().shift(1)
    df["Previous_Low"] = df["Low"].rolling(20).min().shift(1)
    df["ATR_Percent"] = (df["ATR"] / df["Close"]) * 100

    if "Volume" in df.columns:
        df["Volume_MA"] = df["Volume"].rolling(20).mean()
        df["Volume_Ratio"] = df["Volume"] / (df["Volume_MA"] + 1e-10)
    else:
        df["Volume_Ratio"] = np.nan

    return df

def get_higher_timeframe_trend(symbol):
    higher = download_data(symbol, period="1y", interval="4h")
    if higher.empty:
        return "UNKNOWN"
    higher = calculate_indicators(higher)
    last = higher.iloc[-1]
    if last["EMA20"] > last["EMA50"] > last["EMA200"]:
        return "BULLISH"
    if last["EMA20"] < last["EMA50"] < last["EMA200"]:
        return "BEARISH"
    return "NEUTRAL"

def analyze_market(df, higher_tf_trend):
    if len(df) < 250:
        return None

    last = df.iloc[-1]
    price = float(last["Close"])
    atr = float(last["ATR"])
    if np.isnan(atr) or atr <= 0:
        return None

    bullish_points = 0
    bearish_points = 0
    bullish_reasons = []
    bearish_reasons = []

    if last["EMA20"] > last["EMA50"] > last["EMA200"]:
        bullish_points += 25
        bullish_reasons.append("EMA20 > EMA50 > EMA200")
    elif last["EMA20"] < last["EMA50"] < last["EMA200"]:
        bearish_points += 25
        bearish_reasons.append("EMA20 < EMA50 < EMA200")

    rsi = float(last["RSI"])
    if 50 < rsi < 68:
        bullish_points += 15
        bullish_reasons.append(f"RSI bullish ({rsi:.1f})")
    elif 32 < rsi < 50:
        bearish_points += 15
        bearish_reasons.append(f"RSI bearish ({rsi:.1f})")
    if rsi >= 75:
        bullish_points -= 10
    if rsi <= 25:
        bearish_points -= 10

    if last["MACD"] > last["MACD_SIGNAL"] and last["MACD_HIST"] > 0:
        bullish_points += 15
        bullish_reasons.append("MACD bullish")
    elif last["MACD"] < last["MACD_SIGNAL"] and last["MACD_HIST"] < 0:
        bearish_points += 15
        bearish_reasons.append("MACD bearish")

    adx = float(last["ADX"])
    if adx >= 25:
        if last["+DI"] > last["-DI"]:
            bullish_points += 15
            bullish_reasons.append(f"Strong bullish trend ADX {adx:.1f}")
        elif last["-DI"] > last["+DI"]:
            bearish_points += 15
            bearish_reasons.append(f"Strong bearish trend ADX {adx:.1f}")

    if price > last["Previous_High"]:
        bullish_points += 15
        bullish_reasons.append("20-period upside breakout")
    elif price < last["Previous_Low"]:
        bearish_points += 15
        bearish_reasons.append("20-period downside breakout")

    if higher_tf_trend == "BULLISH":
        bullish_points += 15
        bullish_reasons.append("4H trend bullish")
    elif higher_tf_trend == "BEARISH":
        bearish_points += 15
        bearish_reasons.append("4H trend bearish")

    bullish_points = max(0, min(100, bullish_points))
    bearish_points = max(0, min(100, bearish_points))

    if bullish_points >= 70 and bullish_points > bearish_points + 15:
        signal = "BUY"
        confidence = bullish_points
        entry = price
        stop_loss = entry - atr * 1.5
        take_profit = entry + atr * 3.0
        reasons = bullish_reasons
    elif bearish_points >= 70 and bearish_points > bullish_points + 15:
        signal = "SELL"
        confidence = bearish_points
        entry = price
        stop_loss = entry + atr * 1.5
        take_profit = entry - atr * 3.0
        reasons = bearish_reasons
    else:
        signal = "NO TRADE"
        confidence = max(bullish_points, bearish_points)
        entry = price
        stop_loss = np.nan
        take_profit = np.nan
        reasons = ["Conditions are not sufficiently aligned"]

    if signal == "BUY":
        risk = entry - stop_loss
        reward = take_profit - entry
    elif signal == "SELL":
        risk = stop_loss - entry
        reward = entry - take_profit
    else:
        risk = np.nan
        reward = np.nan

    rr = reward / risk if not np.isnan(risk) and risk > 0 else np.nan

    return {
        "Signal": signal,
        "Confidence": confidence,
        "Price": price,
        "Entry": entry,
        "Stop Loss": stop_loss,
        "Take Profit": take_profit,
        "Risk Reward": rr,
        "RSI": rsi,
        "ADX": adx,
        "ATR": atr,
        "Higher TF": higher_tf_trend,
        "Bull Score": bullish_points,
        "Bear Score": bearish_points,
        "Reasons": reasons
    }

def backtest_strategy(df):
    if len(df) < 300:
        return None
    trades = []
    for i in range(250, len(df) - 10):
        current = df.iloc[:i + 1]
        result = analyze_market(current, "UNKNOWN")
        if result is None or result["Signal"] == "NO TRADE":
            continue

        entry = result["Entry"]
        stop = result["Stop Loss"]
        target = result["Take Profit"]
        future = df.iloc[i + 1:i + 11]
        outcome = "OPEN"

        if result["Signal"] == "BUY":
            for _, candle in future.iterrows():
                if candle["Low"] <= stop:
                    outcome = "LOSS"
                    break
                if candle["High"] >= target:
                    outcome = "WIN"
                    break
        else:
            for _, candle in future.iterrows():
                if candle["High"] >= stop:
                    outcome = "LOSS"
                    break
                if candle["Low"] <= target:
                    outcome = "WIN"
                    break

        if outcome in ["WIN", "LOSS"]:
            trades.append(outcome)

    if not trades:
        return None

    wins = trades.count("WIN")
    losses = trades.count("LOSS")
    total = wins + losses

    return {
        "Trades": total,
        "Wins": wins,
        "Losses": losses,
        "Win Rate": wins / total * 100
    }

st.sidebar.header("⚙️ Scanner Settings")

selected_pairs = st.sidebar.multiselect(
    "USD Pairs", list(PAIRS.keys()), default=list(PAIRS.keys())
)

timeframe = st.sidebar.selectbox(
    "Trading timeframe", ["1h", "30m", "15m"], index=0
)

period = st.sidebar.selectbox(
    "Historical data", ["6mo", "1y", "2y"], index=1
)

minimum_confidence = st.sidebar.slider(
    "Minimum signal score", 50, 95, 70
)

show_backtest = st.sidebar.checkbox(
    "Run historical backtest", value=True
)

st.subheader("🌎 USD Forex Scanner")

results = []
raw_data = {}
progress = st.progress(0)

for count, pair in enumerate(selected_pairs):
    symbol = PAIRS[pair]
    df = download_data(symbol, period=period, interval=timeframe)

    if df.empty:
        continue

    df = calculate_indicators(df)
    raw_data[pair] = df
    higher_tf = get_higher_timeframe_trend(symbol)
    analysis = analyze_market(df, higher_tf)

    if analysis:
        results.append({
            "Pair": pair,
            "Signal": analysis["Signal"],
            "Score": round(analysis["Confidence"], 1),
            "Price": analysis["Price"],
            "RSI": round(analysis["RSI"], 1),
            "ADX": round(analysis["ADX"], 1),
            "4H Trend": analysis["Higher TF"],
            "RR": round(analysis["Risk Reward"], 2) if not np.isnan(analysis["Risk Reward"]) else "-"
        })

    progress.progress((count + 1) / max(len(selected_pairs), 1))

progress.empty()

if results:
    result_df = pd.DataFrame(results).sort_values("Score", ascending=False)
    st.dataframe(result_df, use_container_width=True, hide_index=True)
else:
    st.warning("No market data or signals available.")

st.subheader("🎯 Signal Details")

pair_names = [
    r["Pair"] for r in results
    if r["Signal"] != "NO TRADE" and r["Score"] >= minimum_confidence
]

if pair_names:
    selected_pair = st.selectbox("Select active signal", pair_names)
    df = raw_data[selected_pair]
    higher_tf = get_higher_timeframe_trend(PAIRS[selected_pair])
    analysis = analyze_market(df, higher_tf)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Signal", analysis["Signal"])
    c2.metric("Confidence", f'{analysis["Confidence"]:.0f}/100')
    c3.metric("RSI", f'{analysis["RSI"]:.1f}')
    c4.metric("ADX", f'{analysis["ADX"]:.1f}')
    c5.metric("4H Trend", analysis["Higher TF"])

    if analysis["Signal"] != "NO TRADE":
        st.markdown("### Trade Levels")
        a, b, c, d = st.columns(4)
        a.metric("Entry", f'{analysis["Entry"]:.5f}')
        b.metric("Stop Loss", f'{analysis["Stop Loss"]:.5f}')
        c.metric("Take Profit", f'{analysis["Take Profit"]:.5f}')
        d.metric("Risk / Reward", f'{analysis["Risk Reward"]:.2f}')

        st.markdown("### Why the engine generated this signal")
        for reason in analysis["Reasons"]:
            st.write(f"✓ {reason}")
    else:
        st.info("No sufficiently aligned trade setup.")

    st.subheader(f"📊 {selected_pair} Analysis")
    chart_df = df.tail(250)

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.04, row_heights=[0.70, 0.30]
    )

    fig.add_trace(go.Candlestick(
        x=chart_df.index, open=chart_df["Open"],
        high=chart_df["High"], low=chart_df["Low"],
        close=chart_df["Close"], name="Price"
    ), row=1, col=1)

    for col, name in [("EMA20", "EMA 20"), ("EMA50", "EMA 50"), ("EMA200", "EMA 200")]:
        fig.add_trace(go.Scatter(
            x=chart_df.index, y=chart_df[col],
            name=name, line=dict(width=1.5)
        ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=chart_df.index, y=chart_df["RSI"],
        name="RSI", line=dict(width=1.5)
    ), row=2, col=1)

    fig.add_hline(y=70, line_dash="dash", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        height=700,
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(fig, use_container_width=True)

if show_backtest:
    st.subheader("🧪 Historical Strategy Test")
    backtest_results = []

    for pair in selected_pairs:
        if pair not in raw_data:
            continue
        test = backtest_strategy(raw_data[pair])
        if test:
            backtest_results.append({
                "Pair": pair,
                "Trades": test["Trades"],
                "Wins": test["Wins"],
                "Losses": test["Losses"],
                "Win Rate": round(test["Win Rate"], 2)
            })

    if backtest_results:
        st.dataframe(
            pd.DataFrame(backtest_results),
            use_container_width=True,
            hide_index=True
        )
        st.caption(
            "Historical results are not a guarantee of future performance. "
            "The simplified backtest does not model spread, slippage, "
            "commissions, news shocks or execution latency."
        )
    else:
        st.info("Not enough historical data for the backtest.")

st.markdown("---")
st.caption(
    "Quant Signal Engine V2 • Technical-analysis research tool • "
    "Signals are probabilistic and should not be treated as guaranteed outcomes."
)
