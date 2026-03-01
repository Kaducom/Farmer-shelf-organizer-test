const checkbox = document.getElementById('pre-vencido-checkbox');
const camposPre = document.getElementById('pre-vencido-campos');

if (checkbox && camposPre) {
  checkbox.addEventListener('change', () => {
    camposPre.classList.toggle('escondido', !checkbox.checked);
  });
}

async function atualizarAlertas() {
  const total = document.getElementById('total');
  if (!total) return;

  const resposta = await fetch('/api/alertas');
  const dados = await resposta.json();

  document.getElementById('total').textContent = dados.total;
  document.getElementById('vencidos').textContent = dados.vencidos;
  document.getElementById('pre-vencidos').textContent = dados.pre_vencidos;

  const lista = document.getElementById('itens-criticos');
  lista.innerHTML = '';
  dados.itens_criticos.forEach((item) => {
    const li = document.createElement('li');
    li.textContent = `${item.nome} - ${item.status} (${item.validade}) [${item.secao}]`;
    lista.appendChild(li);
  });
}

atualizarAlertas();
setInterval(atualizarAlertas, 10000);
