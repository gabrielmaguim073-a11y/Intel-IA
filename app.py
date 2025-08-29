import os
from flask import Flask

# pega a chave salva no Render
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY não está definida no ambiente")

app = Flask(__name__)

@app.route("/")
def home():
    return f"Sua API_KEY está carregada e o servidor Flask está rodando! Chave: {API_KEY[:5]}***"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
