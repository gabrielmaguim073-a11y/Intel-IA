import os
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory
from openai import OpenAI

app = Flask(__name__)

# -------- Config --------
# Defina essas variáveis no Render:
# OPENAI_API_KEY  -> sua chave da OpenAI
# OPENAI_MODEL    -> ex: gpt-4o-mini (opcional; tem padrão)
# OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS (opcionais)
# APP_TOKEN       -> uma "senha" simples para restringir acesso
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE = float(os.environ.get("OPENAI_TEMPERATURE", "0.7"))
OPENAI_MAX_TOKENS = int(os.environ.get("OPENAI_MAX_TOKENS", "400"))
APP_TOKEN = os.environ.get("APP_TOKEN")  # se não definir, não valida token

client = OpenAI(api_key=OPENAI_API_KEY)

# -------- Rotas --------
@app.route("/")
def home():
    # Página de chat
    return render_template("index.html")

@app.route("/perguntar", methods=["POST"])
def perguntar():
    # Proteção simples por token (opcional, mas recomendado)
    if APP_TOKEN:
        token = request.headers.get("X-Token") or request.headers.get("Authorization", "").replace("Bearer ", "")
        if token != APP_TOKEN:
            return jsonify({"erro": "Não autorizado"}), 401

    data = request.get_json(silent=True) or {}
    pergunta = (data.get("pergunta") or "").strip()
    if not pergunta:
        return jsonify({"erro": "Envie 'pergunta' no JSON."}), 400

    try:
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Você é a IA pessoal do Gabriel. Responda em PT-BR, de forma clara e objetiva."},
                {"role": "user", "content": pergunta},
            ],
            temperature=OPENAI_TEMPERATURE,
            max_tokens=OPENAI_MAX_TOKENS,
        )
        texto = completion.choices[0].message.content
        return jsonify({"resposta": texto})
    except Exception as e:
        logging.exception("Erro consultando a IA")
        return jsonify({"erro": "Falha ao consultar o modelo", "detalhe": str(e)}), 500

# Arquivos estáticos (se precisar no futuro)
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
