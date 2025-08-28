from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "🚀 Sua IA está rodando no Heroku com sucesso!"

if __name__ == "__main__":
    app.run()
