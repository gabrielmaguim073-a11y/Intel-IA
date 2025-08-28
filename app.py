from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "🚀 IA Online e funcionando!"

@app.route("/analise", methods=["POST"])
def analise():
    data = request.get_json()
    # Exemplo simples de resposta — depois você pode melhorar com lógica de IA
    return jsonify({"status": "ok", "mensagem": "Análise recebida", "dados": data})

if __name__ == "__main__":
    app.run(debug=True)
