(function () {
  const form = document.getElementById("cadastro-educador-form");
  if (!form) return;

  const cpfInput = document.getElementById("id_cpf");
  const nameInput = document.getElementById("id_nome_completo");
  const emailInput = document.getElementById("id_email");
  const birthDateInput = document.getElementById("id_data_nascimento");
  const corRacaSelect = document.getElementById("id_cor_raca");
  const genderSelect = document.getElementById("id_genero");
  const cpfStatus = document.getElementById("cpf-status");
  const stateSelect = document.getElementById("id_estado");
  const citySelect = document.getElementById("id_cidade");
  const schoolInput = document.getElementById("id_escola");
  const schoolSearch = document.getElementById("escola-busca");
  const schoolResults = document.getElementById("escola-resultados");
  const schoolToggle = document.querySelector(".school-combobox-toggle");
  const functionSelect = document.getElementById("id_funcao_caracterizacao_turmas");
  const experienceTimeSelect = document.getElementById("id_tempo_atuacao");
  const assignmentsInput = document.getElementById("id_atuacoes_json");
  const assignmentsList = document.getElementById("assignment-list");
  const assignmentsCount = document.getElementById("assignment-count");
  const editorTitle = document.getElementById("assignment-editor-title");
  const editorError = document.getElementById("assignment-editor-error");
  const addAssignmentButton = document.getElementById("add-assignment");
  const cancelAssignmentButton = document.getElementById("cancel-assignment");
  const submitButton = form.querySelector('button[type="submit"]');
  let cpfTimer;
  let schoolTimer;
  let schoolOptions = [];
  let activeSchoolIndex = -1;
  let schoolRequestId = 0;
  let editingIndex = null;
  let assignments = parseAssignments();

  function parseAssignments() {
    try {
      const parsed = JSON.parse(assignmentsInput.value || "[]");
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

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
        birthDateInput.value = data.data_nascimento || "";
        corRacaSelect.value = data.cor_raca_id ? String(data.cor_raca_id) : "";
        genderSelect.value = data.genero || "";
        nameInput.readOnly = true;
        emailInput.readOnly = true;
        form.dataset.existingPerson = "true";
        submitButton.disabled = false;
        const message = data.registered
          ? "Pessoa localizada. Você pode adicionar outro vínculo com escola."
          : "Pessoa localizada. Os dados foram preenchidos.";
        setCpfStatus("success", "bi-check-circle-fill", message);
      } else {
        if (wasExisting) { nameInput.value = ""; emailInput.value = ""; birthDateInput.value = ""; corRacaSelect.value = ""; genderSelect.value = ""; }
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
    schoolRequestId += 1;
    schoolInput.value = "";
    schoolInput.dataset.selectedLabel = "";
    schoolSearch.value = "";
    schoolSearch.disabled = !citySelect.value;
    schoolSearch.placeholder = message;
    schoolToggle.disabled = !citySelect.value;
    schoolOptions = [];
    activeSchoolIndex = -1;
    renderSchoolMessage(message);
    closeSchoolOptions();
  }

  function openSchoolOptions() {
    if (schoolSearch.disabled) return;
    schoolResults.hidden = false;
    schoolSearch.setAttribute("aria-expanded", "true");
  }

  function closeSchoolOptions() {
    schoolResults.hidden = true;
    schoolSearch.setAttribute("aria-expanded", "false");
    activeSchoolIndex = -1;
  }

  function renderSchoolMessage(message) {
    schoolResults.replaceChildren();
    const status = document.createElement("div");
    status.className = "school-option-status";
    status.textContent = message;
    schoolResults.appendChild(status);
  }

  function selectSchool(option) {
    schoolInput.value = String(option.id_escola);
    schoolInput.dataset.selectedLabel = option.nome;
    schoolSearch.value = option.nome;
    schoolSearch.removeAttribute("aria-activedescendant");
    closeSchoolOptions();
  }

  function setActiveSchool(index) {
    const options = Array.from(schoolResults.querySelectorAll("[role='option']"));
    if (!options.length) return;
    activeSchoolIndex = (index + options.length) % options.length;
    options.forEach((option, optionIndex) => option.classList.toggle("is-active", optionIndex === activeSchoolIndex));
    const activeOption = options[activeSchoolIndex];
    schoolSearch.setAttribute("aria-activedescendant", activeOption.id);
    activeOption.scrollIntoView({ block: "nearest" });
  }

  function populateSchools(results) {
    const selected = schoolInput.value;
    const selectedLabel = schoolInput.dataset.selectedLabel;
    schoolOptions = results.slice();
    if (selected && selectedLabel && !schoolOptions.some(item => String(item.id_escola) === selected)) {
      schoolOptions.unshift({ id_escola: selected, nome: selectedLabel });
    }
    if (selected && selectedLabel) schoolSearch.value = selectedLabel;
    schoolResults.replaceChildren();
    if (!schoolOptions.length) {
      renderSchoolMessage("Nenhuma escola encontrada");
      openSchoolOptions();
      return;
    }
    schoolOptions.forEach((item, index) => {
      const option = document.createElement("button");
      option.type = "button";
      option.className = "school-option";
      option.id = `escola-opcao-${index}`;
      option.setAttribute("role", "option");
      option.setAttribute("aria-selected", String(String(item.id_escola) === selected));
      option.textContent = item.nome;
      option.addEventListener("mousedown", event => event.preventDefault());
      option.addEventListener("click", () => selectSchool(item));
      schoolResults.appendChild(option);
    });
    openSchoolOptions();
  }
  async function loadSchools() {
    if (!citySelect.value) return;
    const requestId = ++schoolRequestId;
    schoolSearch.placeholder = "Digite para buscar uma escola";
    schoolToggle.disabled = true;
    renderSchoolMessage("Buscando escolas...");
    openSchoolOptions();
    try {
      const url = `${form.dataset.escolasUrl}?cidade=${encodeURIComponent(citySelect.value)}&q=${encodeURIComponent(schoolSearch.value)}`;
      const response = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      const data = await response.json();
      if (requestId !== schoolRequestId) return;
      populateSchools(data.results || []);
    } finally {
      if (requestId === schoolRequestId) schoolToggle.disabled = false;
    }
  }
  async function loadCities() {
    citySelect.value = "";
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

  function setEditorError(message) {
    editorError.textContent = message || "";
    editorError.classList.toggle("d-none", !message);
  }

  function assignmentKey(item) {
    return `${item.cidade_id}:${item.escola_id}:${item.funcao}`;
  }

  function currentAssignment() {
    const selectedState = stateSelect.selectedOptions[0];
    const selectedCity = citySelect.selectedOptions[0];
    const selectedFunction = functionSelect.selectedOptions[0];
    const selectedExperienceTime = experienceTimeSelect.selectedOptions[0];
    if (!stateSelect.value || !citySelect.value || !schoolInput.value || !functionSelect.value || !experienceTimeSelect.value) return null;
    return {
      estado_id: stateSelect.value,
      estado_nome: selectedState?.text || "",
      cidade_id: citySelect.value,
      cidade_nome: selectedCity?.text || "",
      escola_id: schoolInput.value,
      escola_nome: schoolInput.dataset.selectedLabel || "",
      funcao: functionSelect.value,
      funcao_nome: selectedFunction?.text || "",
      tempo_atuacao: experienceTimeSelect.value,
      tempo_atuacao_nome: selectedExperienceTime?.text || "",
    };
  }

  function syncAssignments() {
    assignmentsInput.value = JSON.stringify(assignments);
    assignmentsCount.textContent = String(assignments.length);
  }

  function createActionButton(action, index, label, icon, className) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.dataset.action = action;
    button.dataset.index = String(index);
    button.innerHTML = `<i class="bi ${icon}"></i><span>${label}</span>`;
    return button;
  }

  function renderAssignments() {
    assignmentsList.replaceChildren();
    if (!assignments.length) {
      const empty = document.createElement("div");
      empty.className = "assignment-empty";
      empty.innerHTML = '<i class="bi bi-inbox"></i><span>Nenhuma atuação adicionada.</span>';
      assignmentsList.appendChild(empty);
      syncAssignments();
      return;
    }

    assignments.forEach((item, index) => {
      const card = document.createElement("article");
      card.className = "assignment-item";
      const content = document.createElement("div");
      content.className = "assignment-item-content";
      const title = document.createElement("strong");
      title.textContent = item.escola_nome;
      const location = document.createElement("span");
      location.textContent = `${item.cidade_nome} — ${item.estado_nome}`;
      const role = document.createElement("span");
      role.className = "assignment-role";
      role.textContent = `${item.funcao_nome} · ${item.tempo_atuacao_nome}`;
      content.append(title, location, role);

      const actions = document.createElement("div");
      actions.className = "assignment-item-actions";
      actions.append(
        createActionButton("edit", index, "Editar", "bi-pencil", "btn btn-sm btn-outline-primary"),
        createActionButton("delete", index, "Excluir", "bi-trash", "btn btn-sm btn-outline-danger"),
      );
      card.append(content, actions);
      assignmentsList.appendChild(card);
    });
    syncAssignments();
  }

  function clearEditor() {
    editingIndex = null;
    stateSelect.value = "";
    citySelect.innerHTML = '<option value="">Selecione primeiro o estado</option>';
    citySelect.disabled = false;
    resetSchool("Selecione primeiro a cidade");
    functionSelect.value = "";
    experienceTimeSelect.value = "";
    editorTitle.textContent = "Adicionar atuação";
    addAssignmentButton.innerHTML = '<i class="bi bi-plus-lg"></i> Adicionar atuação';
    cancelAssignmentButton.classList.add("d-none");
    setEditorError("");
  }

  function addOrUpdateAssignment() {
    const item = currentAssignment();
    if (!item) {
      setEditorError("Selecione atuação, tempo de atuação, estado, cidade e escola antes de adicionar.");
      return;
    }
    if (editingIndex === null && assignments.length >= 20) {
      setEditorError("É permitido adicionar no máximo 20 atuações por cadastro.");
      return;
    }
    const duplicateIndex = assignments.findIndex((assignment, index) => assignmentKey(assignment) === assignmentKey(item) && index !== editingIndex);
    if (duplicateIndex !== -1) {
      setEditorError("Esta atuação já foi adicionada à lista.");
      return;
    }
    if (editingIndex === null) assignments.push(item);
    else assignments[editingIndex] = item;
    renderAssignments();
    clearEditor();
  }

  async function editAssignment(index) {
    const item = assignments[index];
    if (!item) return;
    editingIndex = index;
    setEditorError("");
    stateSelect.value = String(item.estado_id);
    await loadCities();
    citySelect.value = String(item.cidade_id);
    schoolInput.value = String(item.escola_id);
    schoolInput.dataset.selectedLabel = item.escola_nome;
    schoolSearch.disabled = false;
    schoolSearch.value = "";
    schoolToggle.disabled = false;
    await loadSchools();
    schoolSearch.value = item.escola_nome;
    closeSchoolOptions();
    functionSelect.value = item.funcao;
    experienceTimeSelect.value = item.tempo_atuacao;
    editorTitle.textContent = "Editar atuação";
    addAssignmentButton.innerHTML = '<i class="bi bi-check-lg"></i> Atualizar atuação';
    cancelAssignmentButton.classList.remove("d-none");
    stateSelect.focus();
  }

  cpfInput.addEventListener("input", function () {
    cpfInput.value = maskCpf(cpfInput.value);
    clearTimeout(cpfTimer);
    cpfTimer = setTimeout(lookupCpf, 350);
  });
  stateSelect.addEventListener("change", loadCities);
  citySelect.addEventListener("change", function () { resetSchool("Buscando escolas..."); loadSchools(); });
  schoolSearch.addEventListener("focus", function () {
    if (schoolResults.childElementCount) openSchoolOptions();
  });
  schoolSearch.addEventListener("input", function () {
    if (schoolSearch.value !== schoolInput.dataset.selectedLabel) {
      schoolInput.value = "";
      schoolInput.dataset.selectedLabel = "";
    }
    clearTimeout(schoolTimer);
    schoolTimer = setTimeout(loadSchools, 300);
  });
  schoolSearch.addEventListener("keydown", function (event) {
    const optionCount = schoolResults.querySelectorAll("[role='option']").length;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      openSchoolOptions();
      setActiveSchool(activeSchoolIndex + (event.key === "ArrowDown" ? 1 : -1));
    } else if (event.key === "Enter" && activeSchoolIndex >= 0) {
      event.preventDefault();
      selectSchool(schoolOptions[activeSchoolIndex]);
    } else if (event.key === "Escape") {
      closeSchoolOptions();
    } else if (!optionCount) {
      activeSchoolIndex = -1;
    }
  });
  schoolToggle.addEventListener("click", function () {
    if (schoolResults.hidden) {
      schoolSearch.focus();
      loadSchools();
    } else closeSchoolOptions();
  });
  document.addEventListener("click", function (event) {
    if (!event.target.closest(".school-combobox")) closeSchoolOptions();
  });
  addAssignmentButton.addEventListener("click", addOrUpdateAssignment);
  cancelAssignmentButton.addEventListener("click", clearEditor);
  assignmentsList.addEventListener("click", function (event) {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const index = Number(button.dataset.index);
    if (button.dataset.action === "edit") editAssignment(index);
    if (button.dataset.action === "delete") {
      assignments.splice(index, 1);
      if (editingIndex === index) clearEditor();
      else if (editingIndex !== null && editingIndex > index) editingIndex -= 1;
      renderAssignments();
    }
  });
  form.addEventListener("submit", function (event) {
    if (!assignments.length) {
      event.preventDefault();
      setEditorError("Adicione pelo menos uma atuação antes de salvar o cadastro.");
      addAssignmentButton.focus();
      return;
    }
    if (currentAssignment()) {
      event.preventDefault();
      setEditorError("Clique em “Adicionar atuação” ou “Atualizar atuação” antes de salvar.");
      addAssignmentButton.focus();
    }
  });

  cpfInput.value = maskCpf(cpfInput.value);
  if (digits(cpfInput.value).length === 11) lookupCpf();
  if (citySelect.value) {
    schoolSearch.disabled = false;
    schoolToggle.disabled = false;
    loadSchools();
  }
  renderAssignments();
})();
