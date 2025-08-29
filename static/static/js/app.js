// Arquivo: static/js/app.js

async function getSnapshot() {
  try {
    const r = await fetch("/api/snapshot");
    const data = await r.json();
    const last = data.last;

    const snapshotDiv = document.getElementById("snapshot");
    if (!last) {
      snapshotDiv.textContent = "Aguardando primeiros candles...";
      return;
    }

    // Mostra alguns números-chave
    const ema9 = data.ema9.filter(x => x != null);
    const ema21 = data.ema21.filter(x => x != null);
    const rsi14 = data.rsi14.filter(x => x != null);

    snapshotDiv.innerHTML = `
      <b>Ativo:</b> ${data.symbol} &nbsp;
      <b>Período:</b> ${data.interval}<br>
      <b>Último preço:</b> ${last.c.toFixed(2)}<br>
      <b>EMA9:</b> ${ema9.length ? ema9[ema9.length-1].toFixed(2) : "-"} &nbsp;
      <b>EMA21:</b> ${ema21.length ? ema21[ema21.length-1].toFixed(2) : "-"} &nbsp;
      <b>RSI14:</b> ${rsi14.length ? rsi14[rsi14.length-1].toFixed(1) : "-"}
    `;
  } catch (e) {
    document.getElementById("snapshot").textContent = "Erro ao carregar snapshot.";
    console.error(e);
  }
}

async function analisar() {
  const nota = document.getElementById("nota").value.trim();
  const btn = document.getElementById("analisar");
  const out = document.getElementById("resultado");

  btn.disabled = true;
  out.textContent = "Gerando análise da IA...";

  try {
    const r = await fetch("/perguntar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pergunta: nota })
    });
    const data = await r.json();
    if (data.resposta) {
      out.textContent = data.resposta;
    } else {
      out.textContent = data.erro || "Falha ao obter resposta.";
    }
  } catch (e) {
    out.textContent = "Erro na solicitação.";
    console.error(e);
  } finally {
    btn.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  getSnapshot();
  // atualiza o snapshot periodicamente
  setInterval(getSnapshot, 7000);

  const btn = document.getElementById("analisar");
  if (btn) btn.addEventListener("click", analisar);
});
