(function () {
  // Controla o cadastro público como um formulário progressivo: consulta CPF,
  // restringe opções geográficas e reúne múltiplas atuações antes do envio.
  const form = document.getElementById("cadastro-educador-form");
  if (!form) return;

  const cpfInput = document.getElementById("id_cpf");
  const nameInput = document.getElementById("id_nome_completo");
  const emailInput = document.getElementById("id_email");
  const birthDateInput = document.getElementById("id_data_nascimento");
  const corRacaSelect = document.getElementById("id_cor_raca");
  const genderSelect = document.getElementById("id_genero");
  const addressCepInput = document.getElementById("id_endereco_cep");
  const addressStreetInput = document.getElementById("id_endereco_logradouro");
  const addressNumberInput = document.getElementById("id_endereco_numero");
  const addressComplementInput = document.getElementById("id_endereco_complemento");
  const addressDistrictInput = document.getElementById("id_endereco_bairro");
  const addressStateSelect = document.getElementById("id_endereco_estado");
  const addressCitySelect = document.getElementById("id_endereco_cidade");
  const cpfStatus = document.getElementById("cpf-status");
  const cpfEditHelp = document.getElementById("cpf-edit-help");
  const editRegistrationButton = document.getElementById("edit-registration");
  const editCpfInput = document.getElementById("id_editar_cpf");
  const submitLabel = document.getElementById("submit-label");
  let lockedControls = [];
  const stateSelect = document.getElementById("id_estado");
  const citySelect = document.getElementById("id_cidade");
  const schoolInput = document.getElementById("id_escola");
  const schoolSearch = document.getElementById("escola-busca");
  const schoolResults = document.getElementById("escola-resultados");
  const schoolToggle = document.querySelector(".school-combobox-toggle");
  const functionSelect = document.getElementById("id_funcao");
  const assignmentTypeSelect = document.getElementById("id_funcao_caracterizacao_turmas");
  const experienceTimeSelect = document.getElementById("id_tempo_atuacao");
  const assignmentsInput = document.getElementById("id_atuacoes_json");
  const certificateInputs = Array.from(document.querySelectorAll('input[name="curso_certificado"]'));
  const assignmentsList = document.getElementById("assignment-list");
  const assignmentsCount = document.getElementById("assignment-count");
  const editorTitle = document.getElementById("assignment-editor-title");
  const editorError = document.getElementById("assignment-editor-error");
  const addAssignmentButton = document.getElementById("add-assignment");
  const cancelAssignmentButton = document.getElementById("cancel-assignment");
  const submitButton = form.querySelector('button[type="submit"]');
  let cpfTimer;
  let cpfRequestId = 0;
  let addressRequestId = 0;
  let loadedCpf = form.dataset.bound === "true" ? digits(cpfInput.value) : "";
  let schoolTimer;
  let schoolOptions = [];
  let activeSchoolIndex = -1;
  let schoolRequestId = 0;
  let editingIndex = null;
  let assignments = parseAssignments();

  function parseAssignments() {
    // O campo oculto é a fonte de dados enviada ao servidor; a lista visual é só uma representação.
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
  function maskCep(value) {
    const number = value.replace(/\D/g, "").slice(0, 8);
    return number.replace(/^(\d{5})(\d)/, "$1-$2");
  }
  function clearAddress() {
    addressRequestId += 1;
    addressCepInput.value = "";
    addressStreetInput.value = "";
    addressNumberInput.value = "";
    addressComplementInput.value = "";
    addressDistrictInput.value = "";
    addressStateSelect.value = "";
    addressCitySelect.innerHTML = '<option value="">Selecione primeiro a UF</option>';
    addressCitySelect.disabled = false;
  }
  function setCpfStatus(kind, icon, message) {
    cpfEditHelp.hidden = true;
    cpfStatus.className = "lookup-status" + (kind ? ` is-${kind}` : "");
    cpfStatus.innerHTML = `<i class="bi ${icon}"></i><span>${message}</span>`;
  }
  function unlockForm() {
    lockedControls.forEach(([control, disabled]) => { control.disabled = disabled; });
    lockedControls = [];
  }
  function lockForm() {
    unlockForm();
    lockedControls = Array.from(form.querySelectorAll("input:not([type='hidden']), select, button"))
      .filter(control => control !== cpfInput && control !== editRegistrationButton && control !== submitButton)
      .map(control => [control, control.disabled]);
    lockedControls.forEach(([control]) => { control.disabled = true; });
  }
  async function lookupCpf(edit = false) {
    // Cadastros concluídos exigem a escolha de edição antes de liberar o envio.
    const cpf = digits(cpfInput.value);
    const editing = edit || editCpfInput.value === cpf;
    const requestId = ++cpfRequestId;
    if (cpf.length !== 11) {
      form.dataset.registered = "false";
      submitButton.disabled = true;
      setCpfStatus("", "bi-search", "Digite o CPF completo para consultar.");
      return;
    }
    setCpfStatus("", "bi-arrow-repeat", "Consultando o cadastro...");
    submitButton.disabled = true;
    try {
      const response = await fetch(`${form.dataset.cpfUrl}?cpf=${cpf}${editing ? "&editar=1" : ""}`, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      const data = await response.json();
      if (requestId !== cpfRequestId || cpf !== digits(cpfInput.value)) return;
      if (!response.ok || !data.valid) throw new Error(data.message || "CPF inválido.");
      form.dataset.registered = String(data.registered);
      if (data.registered && !editing) {
        nameInput.readOnly = false;
        emailInput.readOnly = false;
        submitButton.disabled = true;
        setCpfStatus("error", "bi-exclamation-circle-fill", "Este CPF já realizou o preenchimento deste formulário. Clique abaixo para realizar alteração nos seus dados.");
        cpfEditHelp.hidden = false;
        lockForm();
      } else {
        unlockForm();
        if (data.dados && (loadedCpf !== cpf || edit)) {
          const fields = {
            nome_completo: nameInput, email: emailInput, data_nascimento: birthDateInput,
            cor_raca: corRacaSelect, genero: genderSelect, endereco_cep: addressCepInput,
            endereco_logradouro: addressStreetInput, endereco_numero: addressNumberInput,
            endereco_complemento: addressComplementInput, endereco_bairro: addressDistrictInput,
            endereco_estado: addressStateSelect,
          };
          Object.entries(fields).forEach(([key, input]) => { input.value = data.dados[key] ?? ""; });
          addressCepInput.value = maskCep(addressCepInput.value);
          certificateInputs.forEach(input => {
            input.checked = (data.dados.curso_certificado || []).map(String).includes(input.value);
          });
          if (editing) {
            document.getElementById("id_email_confirmacao").value = data.dados.email || "";
            assignments = data.dados.atuacoes || [];
            clearEditor();
            renderAssignments();
          }
          loadedCpf = cpf;
          await loadAddressCities(data.dados.endereco_cidade);
          if (requestId !== cpfRequestId || cpf !== digits(cpfInput.value)) return;
        }
        editCpfInput.value = data.registered && editing ? cpf : "";
        submitLabel.textContent = editCpfInput.value ? "Salvar Alterações" : "Salvar cadastro";
        nameInput.readOnly = !editing && Boolean(data.dados?.nome_completo);
        emailInput.readOnly = !editing && Boolean(data.dados?.email);
        submitButton.disabled = false;
        setCpfStatus("new", "bi-person-plus-fill", editCpfInput.value
          ? "Cadastro localizado. Altere os dados e clique em Salvar Alterações."
          : data.exists
          ? "Cadastro localizado. Confira os dados e complete o formulário."
          : "Complete os dados para criar a conta.");
      }
    } catch (error) {
      if (requestId !== cpfRequestId || cpf !== digits(cpfInput.value)) return;
      nameInput.readOnly = false;
      emailInput.readOnly = false;
      form.dataset.registered = "false";
      submitButton.disabled = true;
      setCpfStatus("error", "bi-exclamation-circle-fill", error.message);
      if (edit) cpfEditHelp.hidden = false;
    }
  }

  function resetSchool(message) {
    // Invalida respostas antigas para que uma busca lenta não sobrescreva a seleção atual.
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
    // O identificador incremental evita condições de corrida durante a digitação.
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

  async function loadAddressCities(selectedCity = "") {
    const requestId = ++addressRequestId;
    addressCitySelect.value = "";
    addressCitySelect.disabled = true;
    addressCitySelect.innerHTML = '<option value="">Buscando municípios...</option>';
    if (!addressStateSelect.value) {
      addressCitySelect.innerHTML = '<option value="">Selecione primeiro a UF</option>';
      addressCitySelect.disabled = false;
      return;
    }
    try {
      const response = await fetch(`${form.dataset.cidadesUrl}?estado=${encodeURIComponent(addressStateSelect.value)}`, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      const data = await response.json();
      if (requestId !== addressRequestId) return;
      addressCitySelect.innerHTML = '<option value="">Selecione o município</option>';
      data.results.forEach(item => addressCitySelect.add(new Option(item.nome_cidade, item.id)));
      addressCitySelect.value = selectedCity ? String(selectedCity) : "";
    } finally {
      if (requestId === addressRequestId) addressCitySelect.disabled = false;
    }
  }

  function setEditorError(message) {
    editorError.textContent = message || "";
    editorError.classList.toggle("d-none", !message);
  }

  function assignmentKey(item) {
    return `${item.cidade_id}:${item.escola_id}:${item.funcao}:${item.funcao_caracterizacao_turmas}`;
  }

  function currentAssignment() {
    // Converte a seleção atual no formato validado novamente pelo backend.
    const selectedState = stateSelect.selectedOptions[0];
    const selectedCity = citySelect.selectedOptions[0];
    const selectedFunction = functionSelect.selectedOptions[0];
    const selectedAssignmentType = assignmentTypeSelect.selectedOptions[0];
    const selectedExperienceTime = experienceTimeSelect.selectedOptions[0];
    if (!stateSelect.value || !citySelect.value || !schoolInput.value || !functionSelect.value || !assignmentTypeSelect.value || !experienceTimeSelect.value) return null;
    return {
      estado_id: stateSelect.value,
      estado_nome: selectedState?.text || "",
      cidade_id: citySelect.value,
      cidade_nome: selectedCity?.text || "",
      escola_id: schoolInput.value,
      escola_nome: schoolInput.dataset.selectedLabel || "",
      funcao: functionSelect.value,
      funcao_nome: selectedFunction?.text || "",
      funcao_caracterizacao_turmas: assignmentTypeSelect.value,
      funcao_caracterizacao_turmas_nome: selectedAssignmentType?.text || "",
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
    // Reconstrói a lista com textContent nos dados do usuário para evitar injeção de HTML.
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
      role.textContent = `${item.funcao_nome} · ${item.funcao_caracterizacao_turmas_nome} · ${item.tempo_atuacao_nome}`;
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
    assignmentTypeSelect.value = "";
    experienceTimeSelect.value = "";
    editorTitle.textContent = "Adicionar atuação";
    addAssignmentButton.innerHTML = '<i class="bi bi-plus-lg"></i> Adicionar atuação';
    cancelAssignmentButton.classList.add("d-none");
    setEditorError("");
  }

  function addOrUpdateAssignment() {
    // Uma mesma chave de cidade, escola, função e atuação pode aparecer somente uma vez.
    const item = currentAssignment();
    if (!item) {
      setEditorError("Selecione função, atuação, tempo de atuação, estado, cidade e escola antes de adicionar.");
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
    assignmentTypeSelect.value = item.funcao_caracterizacao_turmas;
    experienceTimeSelect.value = item.tempo_atuacao;
    editorTitle.textContent = "Editar atuação";
    addAssignmentButton.innerHTML = '<i class="bi bi-check-lg"></i> Atualizar atuação';
    cancelAssignmentButton.classList.remove("d-none");
    stateSelect.focus();
  }

  cpfInput.addEventListener("input", function () {
    unlockForm();
    editCpfInput.value = "";
    submitLabel.textContent = "Salvar cadastro";
    cpfEditHelp.hidden = true;
    cpfInput.value = maskCpf(cpfInput.value);
    cpfRequestId += 1;
    submitButton.disabled = true;
    if (loadedCpf && loadedCpf !== digits(cpfInput.value)) {
      loadedCpf = "";
      nameInput.value = "";
      emailInput.value = "";
      nameInput.readOnly = false;
      emailInput.readOnly = false;
      document.getElementById("id_email_confirmacao").value = "";
      birthDateInput.value = "";
      corRacaSelect.value = "";
      genderSelect.value = "";
      certificateInputs.forEach(input => { input.checked = false; });
      clearAddress();
      assignments = [];
      clearEditor();
      renderAssignments();
    }
    clearTimeout(cpfTimer);
    cpfTimer = setTimeout(lookupCpf, 350);
  });
  editRegistrationButton.addEventListener("click", async function () {
    clearTimeout(cpfTimer);
    editRegistrationButton.disabled = true;
    try {
      await lookupCpf(true);
      if (editCpfInput.value) nameInput.focus();
    } finally {
      editRegistrationButton.disabled = false;
    }
  });
  addressCepInput.addEventListener("input", function () { addressCepInput.value = maskCep(addressCepInput.value); });
  addressStateSelect.addEventListener("change", function () { loadAddressCities(); });
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
    if ((form.dataset.registered === "true" && editCpfInput.value !== digits(cpfInput.value)) || submitButton.disabled) {
      event.preventDefault();
      cpfInput.focus();
      return;
    }
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
  addressCepInput.value = maskCep(addressCepInput.value);
  if (digits(cpfInput.value).length === 11) lookupCpf();
  if (citySelect.value) {
    schoolSearch.disabled = false;
    schoolToggle.disabled = false;
    loadSchools();
  }
  renderAssignments();
})();
