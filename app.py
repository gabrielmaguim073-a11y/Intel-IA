from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return "🚀 Sua IA está rodando com Flask!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
