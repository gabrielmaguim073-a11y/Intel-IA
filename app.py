import os, time
import pandas as pd
import numpy as np
import requests
from flask import Flask, render_template, request, jsonify
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator

# --- Config ---
ALPHA_KEY = os.getenv("ALPHA_VANTAGE_KEY")  # defina no Render (Environment)
ALPHA_BASE = "https://www.alphavantage.co/query"

app = Flask(__name__)

def fetch_intraday(symbol: str, interval: str = "1min", output_size: str = "compact") -> pd.DataFrame:
    """
    Busca candles intraday (1min/5min/15min) do Alpha Vantage.
    Retorna DataFrame com colunas: open, high, low, close, volume, index datetime asc.
    """
    if not ALPHA_KEY:
        raise RuntimeError("Defina a variável de ambiente ALPHA_VANTAGE_KEY no Render.")

    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": symbol.upper(),
        "interval": interval,
        "outputsize": output_size,
        "datatype": "json",
        "apikey": ALPHA_KEY,
    }
    r = requests.get(ALPHA_BASE, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    # Tratativas de erro comuns do Alpha
    if "Note" in data:
        raise RuntimeError("Limite de rate do Alpha Vantage atingido. Aguarde um pouco e tente de novo.")
    if "Time Series" not in str(list(data.keys())):
        raise RuntimeError(data.get("Error Message", "Resposta inesperada da API."))

    # Descobre a chave do time series
    ts_key = next(k for k in data.keys() if "Time Series" in k)
    ts = pd.DataFrame(data[ts_key]).T
    ts.index = pd.to_datetime(ts.index)
    ts = ts.sort_index()
    ts = ts.rename(columns={
        '1. open': 'open', '2. high': 'high', '3. low': 'low',
        '4. close': 'close', '5. volume': 'volume'
    }).astype(float)
    return ts

def make_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona EMA9, EMA21, RSI14, MACD e SIGNAL ao DataFrame."""
    df = df.copy()
    df["ema9"]  = EMAIndicator(close=df["close"], window=9).ema_indicator()
    df["ema21"] = EMAIndicator(close=df["close"], window=21).ema_indicator()
    macd        = MACD(close=df["close"], window_slow=26, window_fast=12, window_sign=9)
    df["macd"]  = macd.macd()
    df["macdsig"] = macd.macd_signal()
    df["rsi"] = RSIIndicator(close=df["close"], window=14).rsi()
    return df

def make_signal(df: pd.DataFrame) -> dict:
    """
    Regras simples e transparentes:
      - Tendência: ema9 > ema21 => +1 ; ema9 < ema21 => -1
      - Momentum: RSI < 30 => +1 (sobrevendido), RSI > 70 => -1 (sobrecomprado)
      - MACD: macd > signal => +1 ; macd < signal => -1
      Score final em [-3, +3]. Mapeia para BUY/SELL/HOLD.
    """
    last = df.iloc[-1]
    score = 0
    reasons = []

    # Tendência EMAs
    if last.ema9 > last.ema21:
        score += 1; reasons.append("EMA9 acima de EMA21 (tendência altista).")
    elif last.ema9 < last.ema21:
        score -= 1; reasons.append("EMA9 abaixo de EMA21 (tendência baixista).")
    else:
        reasons.append("EMAs neutras.")

    # RSI
    if last.rsi < 30:
        score += 1; reasons.append("RSI < 30 (sobrevendido).")
    elif last.rsi > 70:
        score -= 1; reasons.append("RSI > 70 (sobrecomprado).")
    else:
        reasons.append("RSI neutro.")

    # MACD
    if last.macd > last.macdsig:
        score += 1; reasons.append("MACD acima da linha de sinal (momentum positivo).")
    elif last.macd < last.macdsig:
        score -= 1; reasons.append("MACD abaixo da linha de sinal (momentum negativo).")
    else:
        reasons.append("MACD neutro.")

    if score >= 2:
        label = "BUY"
    elif score <= -2:
        label = "SELL"
    else:
        label = "HOLD"

    return {
        "label": label,
        "score": int(score),
        "close": round(float(last.close), 4),
        "rsi": round(float(last.rsi), 2),
        "ema9": round(float(last.ema9), 4),
        "ema21": round(float(last.ema21), 4),
        "macd": round(float(last.macd), 4),
        "macd_signal": round(float(last.macdsig), 4),
        "time": last.name.isoformat(),
        "reasons": reasons,
    }

@app.route("/")
def home():
    return render_template("index.html")

@app.get("/analyze")
def analyze():
    symbol = request.args.get("symbol", "AAPL").upper()
    interval = request.args.get("interval", "1min")
    try:
        df = fetch_intraday(symbol, interval=interval)
        df = make_indicators(df)
        sig = make_signal(df)
        sig["symbol"] = symbol
        sig["interval"] = interval
        return jsonify(sig)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    # Para rodar local; no Render usamos gunicorn.
    app.run(host="0.0.0.0", port=5000)
