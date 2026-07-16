(function () {
  const form = document.getElementById("managed-educator-form");
  if (!form) return;

  const stateSelect = document.getElementById("id_estado");
  const citySelect = document.getElementById("id_cidade");
  const schoolInput = document.getElementById("id_escola");
  const schoolSearch = document.getElementById("managed-escola-busca");
  const schoolResults = document.getElementById("managed-escola-resultados");
  let searchTimer;

  function resetSchool(message) {
    schoolInput.value = "";
    schoolInput.dataset.selectedLabel = "";
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
      const response = await fetch(url, {headers: {"X-Requested-With": "XMLHttpRequest"}});
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
      const response = await fetch(`${form.dataset.cidadesUrl}?estado=${encodeURIComponent(stateSelect.value)}`, {headers: {"X-Requested-With": "XMLHttpRequest"}});
      const data = await response.json();
      citySelect.innerHTML = '<option value="">Selecione a cidade</option>';
      data.results.forEach(item => citySelect.add(new Option(item.nome_cidade, item.id)));
    } finally {
      citySelect.disabled = false;
    }
  }

  stateSelect.addEventListener("change", loadCities);
  citySelect.addEventListener("change", function () { resetSchool("Buscando escolas..."); loadSchools(); });
  schoolSearch.addEventListener("input", function () { clearTimeout(searchTimer); searchTimer = setTimeout(loadSchools, 300); });
  schoolResults.addEventListener("change", function () {
    schoolInput.value = schoolResults.value;
    schoolInput.dataset.selectedLabel = schoolResults.selectedOptions[0]?.text || "";
  });

  if (citySelect.value) {
    schoolSearch.disabled = false;
    schoolResults.disabled = false;
    loadSchools();
  }
})();
