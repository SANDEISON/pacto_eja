function configurarCamposProgramacao(container) {
  const modalidade = container.querySelector('[name="modalidade"], [name$="-modalidade"]');
  if (!modalidade || modalidade.dataset.camposProgramacaoConfigurados) return;

  const link = container.querySelector('[name$="-link"]');
  const campoLink = link?.closest(".col-12");
  const publica = container.querySelector('[name="publica"], [name$="-publica"]');
  const campoPublica = publica?.closest(".col-12, .form-row");

  function atualizarCampos() {
    const online = modalidade.value === "online";
    if (campoLink) {
      campoLink.hidden = !online;
      link.disabled = !online;
      if (!online) link.value = "";
    }
    if (campoPublica) {
      campoPublica.hidden = !online;
      publica.disabled = !online;
      if (!online) publica.checked = false;
    }
  }

  modalidade.dataset.camposProgramacaoConfigurados = "true";
  modalidade.addEventListener("change", atualizarCampos);
  atualizarCampos();
}

document.addEventListener("DOMContentLoaded", () => {
  const formAdmin = document.getElementById("programacaosala_form");
  if (formAdmin) configurarCamposProgramacao(formAdmin);
});
