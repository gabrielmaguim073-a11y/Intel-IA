import os
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Olá, Mundo! 🚀 Sua IA já está rodando no Render!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render define a porta em PORT
    app.run(host="0.0.0.0", port=port)
