import os
import json
import time
import threading
import math
import logging
from collections import deque
from urllib.request import urlopen

from flask import Flask, jsonify, render_template, request

# --- OpenAI (opcional, mas recomendado) ---
try:
    from openai import OpenAI
    OPENAI_OK = True
except Exception:
    OPENAI_OK = False

app = Flask(__name__)

# =========================
# CONFIGURAÇÕES
# =========================
# Ativo e timeframe monitorados (padrão BTCUSDT 1m)
SYMBOL = os.environ.get("SYMBOL", "BTCUSDT").upper()
INTERVAL = os.environ.get("INTERVAL", "1m")  # 1m, 5m, 15m...

# Quantidade de candles mantidos em memória
MAX_CANDLES = int(os.environ.get("MAX_CANDLES", "300"))

# OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# Porta (útil em Render/Heroku)
PORT = int(os.environ.get("PORT", "10000"))

# Buffer em memória para candles
# cada item: {"t": ts_ms, "o": float, "h": float, "l": float, "c": float, "v": float}
CANDLES = deque(maxlen=MAX_CANDLES)

# =========================
# FUNÇÕES DE INDICADOR
# =========================
def ema(values, period):
    """EMA simples, sem dependências externas."""
    if not values or len(values) < period:
        return [None] * len(values)
    k = 2 / (period + 1.0)
    out = []
    ema_prev = sum(values[:period]) / period
    # preencher até period-1 com None para alinhar
    out.extend([None] * (period - 1))
    out.append(ema_prev)
    for i in range(period, len(values)):
        ema_prev = values[i] * k + ema_prev * (1 - k)
        out.append(ema_prev)
    return out

def rsi(values, period=14):
    """RSI 14 clássico."""
    if not values or len(values) < period + 1:
        return [None] * len(values)
    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(values)):
        ch = values[i] - values[i-1]
        gains.append(max(ch, 0))
        losses.append(-min(ch, 0))

    rsi_list = [None]*(period)
    avg_gain = sum(gains[1:period+1]) / period
    avg_loss = sum(losses[1:period+1]) / period
    if avg_loss == 0:
        rsi_list.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi_list.append(100.0 - (100.0 / (1.0 + rs)))

    for i in range(period+1, len(values)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi_list.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_list.append(100.0 - (100.0 / (1.0 + rs)))
    return rsi_list

# =========================
# COLETA DE DADOS (BINANCE)
# =========================
BINANCE_URL = "https://api.binance.com/api/v3/klines"

def fetch_klines(symbol, interval, limit=200):
    """Busca candles via REST (sem chave)."""
    url = f"{BINANCE_URL}?symbol={symbol}&interval={interval}&limit={limit}"
    with urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    # Formato Binance por candle:
    # [ open_time, open, high, low, close, volume, close_time, ... ]
    candles = []
    for item in data:
        candles.append({
            "t": int(item[0]),
            "o": float(item[1]),
            "h": float(item[2]),
            "l": float(item[3]),
            "c": float(item[4]),
            "v": float(item[5]),
        })
    return candles

def candles_worker():
    """Thread que atualiza o deque CANDLES a cada ~5s."""
    global CANDLES
    while True:
        try:
            latest = fetch_klines(SYMBOL, INTERVAL, limit=200)
            # substitui mantendo maxlen
            CANDLES.clear()
            for c in latest:
                CANDLES.append(c)
        except Exception as e:
            logging.exception("Falha ao buscar candles: %s", e)
        time.sleep(5)

# Inicia thread de coleta ao subir o app
threading.Thread(target=candles_worker, daemon=True).start()

# =========================
# ROTAS FLASK
# =========================
@app.route("/")
def index():
    return render_template("index.html", symbol=SYMBOL, interval=INTERVAL)

@app.route("/api/snapshot")
def snapshot():
    """Retorna os candles + indicadores (EMA9, EMA21, RSI14)."""
    data = list(CANDLES)
    closes = [c["c"] for c in data]
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    rsi14 = rsi(closes, 14)

    # compacta últimos 120 candles p/ front
    view = data[-120:]

    return jsonify({
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "candles": view,
        "ema9": ema9[-120:],
        "ema21": ema21[-120:],
        "rsi14": rsi14[-120:],
        "last": data[-1] if data else None
    })

@app.route("/perguntar", methods=["POST"])
def perguntar():
    """Gera análise com IA usando o snapshot atual."""
    try:
        payload = request.get_json(silent=True) or {}
        user_note = (payload.get("pergunta") or "").strip()

        data = list(CANDLES)[-120:]
        if not data:
            return jsonify({"erro": "Sem dados ainda, tente novamente em instantes."}), 503

        closes = [c["c"] for c in data]
        ema9_list = ema(closes, 9)
        ema21_list = ema(closes, 21)
        rsi14_list = rsi(closes, 14)

        last = data[-1]
        last_close = last["c"]
        last_ema9 = ema9_list[-1]
        last_ema21 = ema21_list[-1]
        last_rsi = rsi14_list[-1]

        # Monta um resumo compacto p/ IA (não envie todos os 120 candles para economizar tokens)
        def tail(lst, n=20):
            return [x for x in lst[-n:] if x is not None]

        resumo = {
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "ultimos_precos": tail(closes, 30),
            "ema9_tail": tail(ema9_list, 30),
            "ema21_tail": tail(ema21_list, 30),
            "rsi14_tail": tail(rsi14_list, 30),
            "ultimo_close": last_close,
            "ultimo_ema9": last_ema9,
            "ultimo_ema21": last_ema21,
            "ultimo_rsi14": last_rsi,
            "observacao_usuario": user_note,
        }

        # Se não houver OpenAI, retorna um texto local simples
        if not OPENAI_OK or not OPENAI_API_KEY:
            txt = (
                f"[MODO DEMO SEM OPENAI]\n"
                f"Ativo: {SYMBOL} ({INTERVAL})\n"
                f"Último preço: {last_close:.2f}\n"
                f"EMA9: {last_ema9:.2f} | EMA21: {last_ema21:.2f}\n"
                f"RSI14: {last_rsi:.1f}\n"
                f"Interpretação rápida: {'tendência de alta' if last_ema9 and last_ema21 and last_ema9>last_ema21 else 'tendência de baixa/indefinida'}\n"
                f"Observação: {user_note or '(sem)'}"
            )
            return jsonify({"resposta": txt})

        client = OpenAI(api_key=OPENAI_API_KEY)

        system_msg = (
            "Você é um analista técnico profissional. "
            "Explique de forma objetiva, em PT-BR, usando apenas dados técnicos. "
            "Não faça recomendações de compra/venda; foque em leitura de tendência, força e riscos."
        )

        user_msg = (
            "Analise os dados abaixo e descreva tendência (alta/baixa/lateral), "
            "possíveis suportes/resistências com base no comportamento recente, "
            "o que o cruzamento das EMAs sugere e o que o RSI indica. "
            "Se houver divergências, cite. "
            f"Dados: ```json\n{json.dumps(resumo, ensure_ascii=False)}\n```"
        )

        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.2,
            max_tokens=400
        )

        ans = completion.choices[0].message.content.strip()
        return jsonify({"resposta": ans})

    except Exception as e:
        logging.exception("Erro na rota /perguntar")
        return jsonify({"erro": "Falha ao gerar análise", "detalhe": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
