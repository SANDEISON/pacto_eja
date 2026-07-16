(function () {
  const form = document.getElementById("cadastro-educador-form");
  if (!form) return;

  const cpfInput = document.getElementById("id_cpf");
  const nameInput = document.getElementById("id_nome_completo");
  const emailInput = document.getElementById("id_email");
  const cpfStatus = document.getElementById("cpf-status");
  const stateSelect = document.getElementById("id_estado");
  const citySelect = document.getElementById("id_cidade");
  const schoolInput = document.getElementById("id_escola");
  const schoolSearch = document.getElementById("escola-busca");
  const schoolResults = document.getElementById("escola-resultados");
  const submitButton = form.querySelector('button[type="submit"]');
  let cpfTimer;
  let schoolTimer;

  function digits(value) { return value.replace(/\D/g, "").slice(0, 11); }
  function maskCpf(value) {
    const number = digits(value);
    return number.replace(/^(\d{3})(\d)/, "$1.$2").replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3").replace(/\.(\d{3})(\d)/, ".$1-$2");
  }
  function setCpfStatus(kind, icon, message) {
    cpfStatus.className = "lookup-status" + (kind ? ` is-${kind}` : "");
    cpfStatus.innerHTML = `<i class="bi ${icon}"></i><span>${message}</span>`;
  }
  async function lookupCpf() {
    const cpf = digits(cpfInput.value);
    if (cpf.length !== 11) {
      setCpfStatus("", "bi-search", "Digite o CPF completo para consultar.");
      return;
    }
    setCpfStatus("", "bi-arrow-repeat", "Consultando o cadastro...");
    try {
      const response = await fetch(`${form.dataset.cpfUrl}?cpf=${cpf}`, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      const data = await response.json();
      if (!response.ok || !data.valid) throw new Error(data.message || "CPF inválido.");
      const wasExisting = form.dataset.existingPerson === "true";
      if (data.exists) {
        nameInput.value = data.nome_completo;
        emailInput.value = data.email;
        nameInput.readOnly = true;
        emailInput.readOnly = true;
        form.dataset.existingPerson = "true";
        if (data.registered) {
          submitButton.disabled = true;
          setCpfStatus("error", "bi-exclamation-circle-fill", "Esta pessoa já possui um cadastro de educador.");
        } else {
          submitButton.disabled = false;
          setCpfStatus("success", "bi-check-circle-fill", "Pessoa localizada. Os dados foram preenchidos.");
        }
      } else {
        if (wasExisting) { nameInput.value = ""; emailInput.value = ""; }
        nameInput.readOnly = false;
        emailInput.readOnly = false;
        form.dataset.existingPerson = "false";
        submitButton.disabled = false;
        setCpfStatus("new", "bi-person-plus-fill", "CPF não cadastrado. Complete os dados para criar a conta.");
      }
    } catch (error) {
      nameInput.readOnly = false;
      emailInput.readOnly = false;
      form.dataset.existingPerson = "false";
      submitButton.disabled = false;
      setCpfStatus("error", "bi-exclamation-circle-fill", error.message);
    }
  }

  function resetSchool(message) {
    schoolInput.value = "";
    schoolSearch.value = "";
    schoolSearch.disabled = !citySelect.value;
    schoolResults.disabled = !citySelect.value;
    schoolResults.innerHTML = `<option value="">${message}</option>`;
  }
  function populateSchools(results) {
    const selected = schoolInput.value;
    const selectedLabel = schoolInput.dataset.selectedLabel;
    schoolResults.innerHTML = '<option value="">Selecione a escola</option>';
    if (selected && selectedLabel && !results.some(item => String(item.id_escola) === selected)) {
      schoolResults.add(new Option(selectedLabel, selected, true, true));
    }
    results.forEach(item => schoolResults.add(new Option(item.nome, item.id_escola, false, String(item.id_escola) === selected)));
    if (!results.length && !selected) schoolResults.innerHTML = '<option value="">Nenhuma escola encontrada</option>';
  }
  async function loadSchools() {
    if (!citySelect.value) return;
    schoolResults.disabled = true;
    schoolResults.innerHTML = '<option value="">Buscando escolas...</option>';
    try {
      const url = `${form.dataset.escolasUrl}?cidade=${encodeURIComponent(citySelect.value)}&q=${encodeURIComponent(schoolSearch.value)}`;
      const response = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      const data = await response.json();
      populateSchools(data.results || []);
    } finally {
      schoolResults.disabled = false;
    }
  }
  async function loadCities() {
    resetSchool("Selecione primeiro a cidade");
    citySelect.disabled = true;
    citySelect.innerHTML = '<option value="">Buscando cidades...</option>';
    if (!stateSelect.value) {
      citySelect.innerHTML = '<option value="">Selecione primeiro o estado</option>';
      return;
    }
    try {
      const response = await fetch(`${form.dataset.cidadesUrl}?estado=${encodeURIComponent(stateSelect.value)}`, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      const data = await response.json();
      citySelect.innerHTML = '<option value="">Selecione a cidade</option>';
      data.results.forEach(item => citySelect.add(new Option(item.nome_cidade, item.id)));
    } finally {
      citySelect.disabled = false;
    }
  }

  cpfInput.addEventListener("input", function () {
    cpfInput.value = maskCpf(cpfInput.value);
    clearTimeout(cpfTimer);
    cpfTimer = setTimeout(lookupCpf, 350);
  });
  stateSelect.addEventListener("change", loadCities);
  citySelect.addEventListener("change", function () { resetSchool("Buscando escolas..."); loadSchools(); });
  schoolSearch.addEventListener("input", function () { clearTimeout(schoolTimer); schoolTimer = setTimeout(loadSchools, 300); });
  schoolResults.addEventListener("change", function () {
    schoolInput.value = schoolResults.value;
    schoolInput.dataset.selectedLabel = schoolResults.selectedOptions[0]?.text || "";
  });

  cpfInput.value = maskCpf(cpfInput.value);
  if (digits(cpfInput.value).length === 11) lookupCpf();
  if (citySelect.value) {
    schoolSearch.disabled = false;
    schoolResults.disabled = false;
    loadSchools();
  }
})();
