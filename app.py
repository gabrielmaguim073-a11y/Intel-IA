from flask import Flask, request, jsonify

app = Flask(__name__)

@app.get("/")
def home():
    return "IA Online!"

@app.post("/analisar")
def analisar():
    data = request.get_json(silent=True) or {}
    ativo = (data.get("ativo") or "").strip().upper()
    if not ativo:
        return jsonify(erro="Informe o campo 'ativo' no JSON (ex: {'ativo':'AAPL'})."), 400

    # Lógica simples só para demo (sem dependências extras)
    import random
    preco = round(random.uniform(10, 500), 2)
    decisao = "Comprar" if int(preco) % 2 else "Aguardar"

    return jsonify(ativo=ativo, preco=preco, decisao=decisao)
