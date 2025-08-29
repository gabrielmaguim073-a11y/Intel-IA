// Arquivo: static/js/app.js

document.addEventListener("DOMContentLoaded", () => {
    console.log("🚀 App carregado com sucesso!");

    const titulo = document.querySelector("h1");
    if (titulo) {
        titulo.addEventListener("click", () => {
            alert("Você clicou no título!");
        });
    }
});
