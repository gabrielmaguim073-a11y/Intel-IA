from flask import Flask, request, jsonify, render_template
import openai
import os

app = Flask(__name__)

# Configuração da API Key do OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Página inicial
@app.route("/")
def index():
    return render_template("index.html")

# Rota da IA (para conversas)
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message")

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Você é uma IA que ajuda em análises financeiras."},
            {"role": "user", "content": user_message},
        ]
    )

    return jsonify({"reply": response["choices"][0]["message"]["content"]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
