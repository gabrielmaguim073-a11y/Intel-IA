import os

# lê a chave salva no Render
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY não está definida no ambiente")
