(function () {
  "use strict";

  // Coordena as etapas da inscrição e o formset de coautores. Todas as regras
  // de autorização e integridade continuam sendo validadas novamente no backend.
  const form = document.getElementById("registration-form");
  if (!form) return;

  const coauthorList = document.getElementById("coauthors-list");
  const totalFormsInput = document.getElementById("id_coautor-TOTAL_FORMS");
  const coauthorTemplate = document.getElementById("coauthor-template");
  const coauthorSearch = document.getElementById("coauthor-search");
  const searchResults = document.getElementById("coauthor-results");
  const steps = [...form.querySelectorAll("[data-registration-step]")];
  const personalDataStep = form.querySelector('[data-registration-step="pessoal"]');
  const modalityStep = form.querySelector('[data-registration-step="modalidade"]');
  const modalitySelect = document.getElementById("id_dados-modalidade_inscricao");
  const mealsSection = form.querySelector("[data-registration-meals]");
  const programsSection = form.querySelector("[data-registration-programs]");
  const programRequiredModal = document.getElementById("registration-program-required-modal");
  const programDetailsModal = document.getElementById("registration-program-details-modal");
  const programThemeFilter = form.querySelector("[data-registration-program-theme-filter]");
  const programDateFilter = form.querySelector("[data-registration-program-date-filter]");
  const workChoiceStep = form.querySelector('[data-registration-step="decisao"]');
  const continueButton = form.querySelector("[data-registration-continue]");
  const modalityContinueButton = form.querySelector("[data-registration-modality-continue]");
  const backButton = form.querySelector("[data-registration-back]");
  const finishButton = form.querySelector("[data-registration-finish]");
  const updateButton = form.querySelector("[data-registration-update]");
  const submitWorkButton = form.querySelector("[data-registration-submit]");
  const canSubmitWork = form.dataset.canSubmitWork === "true";
  const alreadyRegistered = form.dataset.alreadyRegistered === "true";
  const addressStateSelect = document.getElementById("id_endereco-estado");
  const addressCitySelect = document.getElementById("id_endereco-cidade");
  const formationList = form.querySelector("[data-formation-list]");
  const formationTemplate = form.querySelector("[data-formation-template]");
  const formationTotalForms = document.getElementById("id_formacao-TOTAL_FORMS");
  const formationsEmpty = form.querySelector("[data-formations-empty]");
  const formationsRequiredError = form.querySelector("[data-formations-required]");
  const currentStepInput = form.querySelector("[data-current-registration-step]");
  const workStateSelect = document.getElementById("id_trabalho-estado");
  const workPresentationSelect = document.getElementById("id_trabalho-modalidade_apresentacao");
  const proposalAxisContainer = form.querySelector("[data-proposal-axis-container]");
  const proposalAxisSelect = document.getElementById("id_trabalho-eixo_proposta");
  const municipalityList = form.querySelector("[data-municipality-list]");
  const municipalityTemplate = form.querySelector("[data-municipality-template]");
  const municipalityTotalForms = document.getElementById("id_municipio-TOTAL_FORMS");
  const draftScript = document.getElementById("registration-draft-data");
  const draftData = draftScript ? JSON.parse(draftScript.textContent) : {};
  let searchTimer;

  function updateProposalAxisAvailability() {
    if (!proposalAxisContainer || !proposalAxisSelect) return;
    const isOnline = workPresentationSelect?.value === "online";
    proposalAxisContainer.hidden = !isOnline;
    proposalAxisSelect.disabled = !isOnline;
    if (!isOnline) proposalAxisSelect.value = "";
  }

  function showStep(stepName) {
    steps.forEach((step) => {
      step.hidden = step.dataset.registrationStep !== stepName;
    });
    if (continueButton) continueButton.hidden = stepName !== "pessoal";
    if (modalityContinueButton) {
      modalityContinueButton.hidden = stepName !== "modalidade" || !canSubmitWork;
    }
    if (backButton) backButton.hidden = stepName === "pessoal";
    if (finishButton) finishButton.hidden = true;
    if (updateButton) updateButton.hidden = true;
    if (submitWorkButton) submitWorkButton.hidden = stepName !== "trabalho";
    if (stepName === "modalidade" && !canSubmitWork) {
      if (alreadyRegistered && updateButton) updateButton.hidden = false;
      if (!alreadyRegistered && finishButton) finishButton.hidden = false;
    }
    if (stepName === "decisao") workChoiceStep?.focus({ preventScroll: true });
    if (currentStepInput) currentStepInput.value = stepName;
  }

  function personalDataIsValid() {
    const visibleFormationRows = formationList?.querySelectorAll("[data-formation-row]:not([hidden])") || [];
    if (!visibleFormationRows.length) {
      formationsRequiredError?.classList.add("d-block");
      form.querySelector("[data-add-formation]")?.focus();
      return false;
    }
    formationsRequiredError?.classList.remove("d-block");
    const fields = [...personalDataStep.querySelectorAll("input, select, textarea")].filter(
      (field) => !field.closest("[data-formation-row]")?.hidden,
    );
    const invalidField = fields.find((field) => !field.checkValidity());
    if (!invalidField) return true;
    invalidField.reportValidity();
    invalidField.focus();
    return false;
  }

  function modalityIsValid() {
    if (modalitySelect && !modalitySelect.checkValidity()) {
      modalitySelect.reportValidity();
      modalitySelect.focus();
      return false;
    }
    return programSelectionIsValid();
  }

  function updateMealAvailability() {
    if (!mealsSection) return;
    const hasInPersonProgram = Boolean(
      programsSection?.querySelector('[name="dados-programacoes"]:checked[data-modalidade="presencial"]'),
    );
    const isInPerson = modalitySelect?.value === "presencial" || hasInPersonProgram;
    mealsSection.hidden = !isInPerson;
    mealsSection.querySelectorAll('[name="dados-refeicoes"]').forEach((field) => {
      if (!isInPerson) field.checked = false;
    });
  }

  function programOptionWrapper(field) {
    return field.closest("li") || field.parentElement?.parentElement;
  }

  function groupProgramOptions() {
    if (!programsSection) return;
    const fields = [...programsSection.querySelectorAll('[name="dados-programacoes"]')];
    // O mixin de formulários também aplica `certificate-options` a cada
    // checkbox. Restringir a busca a uma div evita confundir o input com a
    // raiz das opções.
    const optionsRoot = fields[0]?.closest("div.certificate-options");
    if (!optionsRoot || optionsRoot.dataset.grouped === "true") return;

    const days = new Map();
    fields.forEach((field) => {
      const option = programOptionWrapper(field);
      if (!option || option === optionsRoot) return;
      option.classList.add("program-option-wrapper");
      if (field.dataset.descricao?.trim()) {
        option.classList.add("has-program-details");
        const detailsButton = document.createElement("button");
        detailsButton.type = "button";
        detailsButton.className = "btn btn-sm btn-outline-primary program-details-button";
        detailsButton.dataset.programDetails = "";
        detailsButton.dataset.programInputId = field.id;
        detailsButton.textContent = "Ver detalhes";
        const roomName = option.querySelector(".program-card-heading strong")?.textContent?.trim();
        detailsButton.setAttribute("aria-label", `Ver detalhes de ${roomName || "sala"}`);
        option.append(detailsButton);
      }
      const dayKey = field.dataset.data;
      const periodKey = `${dayKey}-${field.dataset.turno}`;
      if (!days.has(dayKey)) {
        const day = document.createElement("section");
        day.className = "registration-program-day";
        day.dataset.programDay = dayKey;
        const heading = document.createElement("h5");
        heading.innerHTML = '<i class="bi bi-calendar3" aria-hidden="true"></i>';
        heading.append(document.createTextNode(` ${field.dataset.dataLabel}`));
        day.append(heading);
        days.set(dayKey, { element: day, periods: new Map() });
      }
      const day = days.get(dayKey);
      if (!day.periods.has(periodKey)) {
        const period = document.createElement("div");
        period.className = "registration-program-period";
        period.dataset.programPeriod = periodKey;
        const heading = document.createElement("h6");
        heading.innerHTML = '<i class="bi bi-clock" aria-hidden="true"></i>';
        heading.append(document.createTextNode(` ${field.dataset.turnoLabel}`));
        const options = document.createElement("div");
        options.className = "registration-program-period-options";
        period.append(heading, options);
        day.element.append(period);
        day.periods.set(periodKey, options);
      }
      day.periods.get(periodKey).append(option);
    });
    optionsRoot.replaceChildren(...[...days.values()].map((day) => day.element));
    optionsRoot.dataset.grouped = "true";
  }

  programsSection?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-program-details]");
    if (!button || !programDetailsModal) return;
    const field = document.getElementById(button.dataset.programInputId);
    if (!field) return;
    const title = programDetailsModal.querySelector("[data-program-details-title]");
    const description = programDetailsModal.querySelector("[data-program-details-description]");
    const roomName = programOptionWrapper(field)?.querySelector(".program-card-heading strong")?.textContent;
    if (title) title.textContent = roomName || "Detalhes da sala";
    if (description) description.textContent = field.dataset.descricao?.trim() || "Descrição não informada.";
    if (window.bootstrap?.Modal) window.bootstrap.Modal.getOrCreateInstance(programDetailsModal).show();
  });

  function updateProgramGroupVisibility() {
    programsSection?.querySelectorAll("[data-program-period]").forEach((period) => {
      period.hidden = !period.querySelector(".program-option-wrapper:not([hidden])");
    });
    programsSection?.querySelectorAll("[data-program-day]").forEach((day) => {
      day.hidden = !day.querySelector("[data-program-period]:not([hidden])");
    });
  }

  function selectedProgramConflicts() {
    const occupied = new Set();
    let hasConflict = false;
    programsSection?.querySelectorAll('[name="dados-programacoes"]:checked').forEach((field) => {
      const slot = `${field.dataset.data}-${field.dataset.turno}`;
      if (occupied.has(slot)) hasConflict = true;
      occupied.add(slot);
    });
    return { occupied, hasConflict };
  }

  function updateProgramConflicts() {
    if (!programsSection) return true;
    const { occupied, hasConflict } = selectedProgramConflicts();
    programsSection.querySelectorAll('[name="dados-programacoes"]').forEach((field) => {
      const slot = `${field.dataset.data}-${field.dataset.turno}`;
      const blocked = !field.checked && occupied.has(slot);
      field.disabled = blocked;
      const option = programOptionWrapper(field);
      option?.classList.toggle("program-option-conflict", blocked);
      if (blocked) {
        field.title = "Já existe uma sala selecionada nesta data e turno.";
      } else {
        field.removeAttribute("title");
      }
    });
    const message = programsSection.querySelector("[data-registration-program-conflict]");
    if (message) message.hidden = !hasConflict;
    return !hasConflict;
  }

  function programSelectionIsValid() {
    const programFields = programsSection?.querySelectorAll('[name="dados-programacoes"]') || [];
    const selectedPrograms = [
      ...(programsSection?.querySelectorAll('[name="dados-programacoes"]:checked') || []),
    ];
    const requiredMessage = programsSection?.querySelector("[data-registration-programs-required]");
    const modalMessage = programRequiredModal?.querySelector("#registration-program-required-message");
    const showSelectionError = (message) => {
      if (requiredMessage) {
        requiredMessage.textContent = message;
        requiredMessage.classList.add("d-block");
      }
      if (modalMessage) modalMessage.textContent = message;
      if (programRequiredModal && window.bootstrap?.Modal) {
        window.bootstrap.Modal.getOrCreateInstance(programRequiredModal).show();
      } else {
        programFields[0]?.focus();
      }
    };
    if (programFields.length && !selectedPrograms.length) {
      showSelectionError("Selecione pelo menos uma sala disponível.");
      return false;
    }
    if (!updateProgramConflicts()) {
      const firstConflict = programsSection?.querySelector('[name="dados-programacoes"]:checked');
      firstConflict?.focus();
      return false;
    }
    const selectedShifts = new Set(selectedPrograms.map((field) => field.dataset.turno));
    if (programFields.length && (!selectedShifts.has("manha") || !selectedShifts.has("tarde"))) {
      showSelectionError(
        "Selecione pelo menos uma programação pela manhã e uma à tarde, independentemente do dia.",
      );
      return false;
    }
    requiredMessage?.classList.remove("d-block");
    return true;
  }

  function updateProgramAvailability() {
    if (!programsSection) return;
    const modality = modalitySelect?.value || "";
    programsSection.hidden = !modality;
    if (!modality) {
      programsSection.querySelectorAll('[name="dados-programacoes"]:checked').forEach((field) => {
        field.checked = false;
      });
      updateProgramSelectionCount();
      return;
    }
    const theme = programThemeFilter?.value || "";
    const date = programDateFilter?.value || "";
    let availablePrograms = 0;
    programsSection.querySelectorAll('[name="dados-programacoes"]').forEach((field) => {
      const matchesModality = !modality || field.dataset.modalidade === modality;
      const matchesTheme = !theme || field.dataset.tematica === theme;
      const matchesDate = !date || field.dataset.data === date;
      const isAvailable = matchesModality && matchesTheme && matchesDate;
      const option = programOptionWrapper(field);
      if (option) option.hidden = !isAvailable;
      if (isAvailable) availablePrograms += 1;
    });
    updateProgramGroupVisibility();
    const emptyMessage = programsSection.querySelector("[data-registration-programs-empty]");
    if (emptyMessage) emptyMessage.hidden = availablePrograms > 0;
    const emptyText = programsSection.querySelector("[data-registration-programs-empty-text]");
    if (emptyText) {
      emptyText.textContent = modality
        ? "Não há programações disponíveis para esta modalidade e os filtros selecionados."
        : "Nenhuma programação corresponde aos filtros selecionados.";
    }
    updateProgramConflicts();
    updateProgramSelectionCount();
  }

  function updateProgramSelectionCount() {
    if (!programsSection) return;
    const selectedPrograms = programsSection.querySelectorAll(
      '[name="dados-programacoes"]:checked:not(:disabled)',
    ).length;
    const counter = programsSection.querySelector("[data-registration-programs-count]");
    if (counter) {
      counter.textContent = selectedPrograms === 1
        ? "1 selecionada"
        : `${selectedPrograms} selecionadas`;
    }
  }

  async function loadAddressCities(selectedCity = "") {
    if (!addressStateSelect || !addressCitySelect) return;
    addressCitySelect.value = "";
    addressCitySelect.disabled = true;
    addressCitySelect.innerHTML = '<option value="">Buscando municípios...</option>';
    if (!addressStateSelect.value) {
      addressCitySelect.innerHTML = '<option value="">Selecione primeiro a UF</option>';
      addressCitySelect.disabled = false;
      return;
    }
    try {
      const response = await fetch(`${form.dataset.cidadesUrl}?estado=${encodeURIComponent(addressStateSelect.value)}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!response.ok) throw new Error("Não foi possível carregar os municípios.");
      const data = await response.json();
      addressCitySelect.innerHTML = '<option value="">Selecione o município</option>';
      data.results.forEach((item) => addressCitySelect.add(new Option(item.nome_cidade, item.id)));
      if (!data.results.length) {
        addressCitySelect.innerHTML = '<option value="">Nenhum município encontrado</option>';
      }
      addressCitySelect.value = String(selectedCity || "");
    } catch (error) {
      addressCitySelect.innerHTML = '<option value="">Não foi possível carregar os municípios</option>';
    } finally {
      addressCitySelect.disabled = false;
    }
  }

  function updateFormationsEmptyState() {
    const visibleRows = formationList?.querySelectorAll("[data-formation-row]:not([hidden])").length || 0;
    formationsEmpty?.classList.toggle("d-none", visibleRows > 0);
    if (visibleRows > 0) formationsRequiredError?.classList.remove("d-block");
  }

  function requireFormationFields(row, required) {
    ["nivel", "nome_curso", "instituicao", "situacao"].forEach((fieldName) => {
      const field = row.querySelector(`[name$="-${fieldName}"]`);
      if (field) field.required = required;
    });
  }

  function addFormation(shouldFocus = true) {
    if (!formationList || !formationTemplate || !formationTotalForms) return;
    const index = Number(formationTotalForms.value);
    const wrapper = document.createElement("div");
    wrapper.innerHTML = formationTemplate.innerHTML.replaceAll("__prefix__", String(index));
    requireFormationFields(wrapper.firstElementChild, true);
    formationList.append(wrapper.firstElementChild);
    formationTotalForms.value = String(index + 1);
    updateFormationsEmptyState();
    if (shouldFocus) formationList.lastElementChild?.querySelector("select, input")?.focus();
  }

  function removeFormation(row) {
    const deleteInput = row.querySelector('input[name$="-DELETE"]');
    if (deleteInput) deleteInput.checked = true;
    requireFormationFields(row, false);
    row.hidden = true;
    updateFormationsEmptyState();
  }

  // Reaproveita uma linha vazia renderizada pelo Django ou cria uma nova a
  // partir do empty_form, mantendo TOTAL_FORMS sincronizado.
  function getAvailableCoauthorRow() {
    let row = [...coauthorList.querySelectorAll(".coauthor-row")].find((item) => {
      const userInput = item.querySelector('input[name$="-usuario"]');
      const deleteInput = item.querySelector('input[name$="-DELETE"]');
      return !userInput.value && !deleteInput?.checked;
    });
    if (row) return row;

    return appendCoauthorRow();
  }

  function appendCoauthorRow() {
    const formIndex = Number(totalFormsInput.value);
    const wrapper = document.createElement("div");
    wrapper.innerHTML = coauthorTemplate.innerHTML.replaceAll("__prefix__", formIndex);
    const row = wrapper.firstElementChild;
    coauthorList.append(row);
    totalFormsInput.value = String(formIndex + 1);
    return row;
  }

  function activeAuthorshipRows() {
    return [...(coauthorList?.querySelectorAll(".coauthor-row") || [])].filter((row) => {
      const user = row.querySelector('input[name$="-usuario"]');
      const deleted = row.querySelector('input[name$="-DELETE"]')?.checked;
      return user?.value && !deleted && !row.hidden;
    });
  }

  function normalizeAuthorship(preferredAuthor = null) {
    const rows = activeAuthorshipRows();
    if (!rows.length) return;
    const author = preferredAuthor
      || rows.find((row) => row.querySelector('select[name$="-papel"]')?.value === "autor")
      || rows[0];
    const others = rows
      .filter((row) => row !== author)
      .sort((left, right) => (
        Number(left.querySelector('input[name$="-ordem"]')?.value || 999)
        - Number(right.querySelector('input[name$="-ordem"]')?.value || 999)
      ));
    [author, ...others].forEach((row, index) => {
      const role = row.querySelector('select[name$="-papel"]');
      const order = row.querySelector('input[name$="-ordem"]');
      if (role) role.value = index === 0 ? "autor" : "coautor";
      if (order) order.value = String(index + 1);
    });
  }

  function moveAuthorshipRow(row) {
    const rows = activeAuthorshipRows();
    const author = rows.find(
      (item) => item.querySelector('select[name$="-papel"]')?.value === "autor",
    );
    if (!author || row === author) {
      normalizeAuthorship(author || row);
      return;
    }
    const coauthors = rows
      .filter((item) => item !== author && item !== row)
      .sort((left, right) => (
        Number(left.querySelector('input[name$="-ordem"]')?.value || 999)
        - Number(right.querySelector('input[name$="-ordem"]')?.value || 999)
      ));
    const desiredPosition = Math.max(
      0,
      Math.min(coauthors.length, Number(row.querySelector('input[name$="-ordem"]')?.value || 2) - 2),
    );
    coauthors.splice(desiredPosition, 0, row);
    [author, ...coauthors].forEach((item, index) => {
      item.querySelector('input[name$="-ordem"]').value = String(index + 1);
    });
  }

  async function loadMunicipalityOptions(row, selectedCity = "") {
    const citySelect = row?.querySelector('select[name$="-cidade"]');
    if (!citySelect) return;
    citySelect.disabled = true;
    citySelect.innerHTML = '<option value="">Buscando municípios...</option>';
    if (!workStateSelect?.value) {
      citySelect.innerHTML = '<option value="">Selecione primeiro o estado</option>';
      citySelect.disabled = false;
      return;
    }
    try {
      const response = await fetch(`${form.dataset.cidadesUrl}?estado=${encodeURIComponent(workStateSelect.value)}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!response.ok) throw new Error();
      const data = await response.json();
      citySelect.innerHTML = '<option value="">Selecione o município</option>';
      data.results.forEach((item) => citySelect.add(new Option(item.nome_cidade, item.id)));
      citySelect.value = String(selectedCity || "");
    } catch (error) {
      citySelect.innerHTML = '<option value="">Não foi possível carregar os municípios</option>';
    } finally {
      citySelect.disabled = false;
    }
  }

  function appendMunicipalityRow(shouldFocus = true) {
    if (!municipalityList || !municipalityTemplate || !municipalityTotalForms) return null;
    const index = Number(municipalityTotalForms.value);
    const wrapper = document.createElement("div");
    wrapper.innerHTML = municipalityTemplate.innerHTML.replaceAll("__prefix__", String(index));
    const row = wrapper.firstElementChild;
    municipalityList.append(row);
    municipalityTotalForms.value = String(index + 1);
    loadMunicipalityOptions(row);
    if (shouldFocus) row.querySelector("select")?.focus();
    return row;
  }

  function removeMunicipality(row) {
    const deleteInput = row.querySelector('input[name$="-DELETE"]');
    if (deleteInput) deleteInput.checked = true;
    row.querySelectorAll("select, input").forEach((field) => {
      if (field !== deleteInput) field.required = false;
    });
    row.hidden = true;
  }

  async function restoreDraft() {
    if (!Object.keys(draftData).length) return;

    const desiredFormations = Number(draftData["formacao-TOTAL_FORMS"]?.[0] || 0);
    while (formationTotalForms && Number(formationTotalForms.value) < desiredFormations) {
      addFormation(false);
    }
    const desiredCoauthors = Number(draftData["coautor-TOTAL_FORMS"]?.[0] || 0);
    while (totalFormsInput && coauthorTemplate && Number(totalFormsInput.value) < desiredCoauthors) {
      appendCoauthorRow();
    }
    const desiredMunicipalities = Number(draftData["municipio-TOTAL_FORMS"]?.[0] || 0);
    while (
      municipalityTotalForms
      && Number(municipalityTotalForms.value) < desiredMunicipalities
    ) {
      appendMunicipalityRow(false);
    }

    Object.entries(draftData).forEach(([name, values]) => {
      if (name === "endereco-cidade" || /^municipio-\d+-cidade$/.test(name)) return;
      const fields = [...form.elements].filter((field) => field.name === name);
      fields.forEach((field) => {
        if (field.type === "file") return;
        if (field.type === "checkbox" || field.type === "radio") {
          field.checked = values.includes(field.value);
        } else {
          field.value = values[values.length - 1] || "";
        }
      });
    });

    const city = draftData["endereco-cidade"]?.[0];
    if (addressStateSelect?.value) await loadAddressCities(city);
    if (workStateSelect?.value && municipalityList) {
      await Promise.all([...municipalityList.querySelectorAll("[data-municipality-row]")].map(
        (row, index) => loadMunicipalityOptions(
          row,
          draftData[`municipio-${index}-cidade`]?.[0]
            || row.querySelector('select[name$="-cidade"]')?.value,
        ),
      ));
    }
    form.querySelectorAll('[name$="-DELETE"]:checked').forEach((field) => {
      const row = field.closest("[data-formation-row], .coauthor-row, [data-municipality-row]");
      if (row) row.hidden = true;
    });
    coauthorList?.querySelectorAll(".coauthor-row").forEach((row) => {
      const user = row.querySelector('input[name$="-usuario"]');
      const deleted = row.querySelector('input[name$="-DELETE"]')?.checked;
      if (user?.value && !deleted) row.hidden = false;
    });
  }

  function renderSearchResults(people, emptyMessage) {
    searchResults.replaceChildren();
    if (!people.length) {
      searchResults.textContent = emptyMessage || "Nenhum usuário cadastrado encontrado.";
      return;
    }
    people.forEach((person) => {
      const option = document.createElement("button");
      option.type = "button";
      option.className = "coauthor-result";
      option.dataset.id = person.id;
      option.dataset.name = person.name;
      option.dataset.email = person.email;

      const name = document.createElement("strong");
      const email = document.createElement("small");
      name.textContent = person.name;
      email.textContent = person.email || "E-mail não informado";
      option.append(name, email);
      searchResults.append(option);
    });
  }

  async function searchCoauthors(query) {
    searchResults.textContent = "Buscando...";
    try {
      const url = `${form.dataset.coauthorsUrl}?q=${encodeURIComponent(query)}`;
      const response = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const data = await response.json();
      renderSearchResults(data.results || [], data.message);
    } catch (error) {
      searchResults.textContent = "Não foi possível realizar a busca. Tente novamente.";
    }
  }

  function addCoauthor(option) {
    const isDuplicate = [...coauthorList.querySelectorAll('input[name$="-usuario"]')].some(
      (input) => input.value === option.dataset.id
        && !input.closest(".coauthor-row").querySelector('input[name$="-DELETE"]')?.checked,
    );
    if (isDuplicate) {
      searchResults.textContent = "Esta pessoa já foi adicionada à autoria.";
      return;
    }

    const row = getAvailableCoauthorRow();
    row.querySelector('input[name$="-usuario"]').value = option.dataset.id;
    row.querySelector('input[name$="-nome"]').value = option.dataset.name;
    row.querySelector('input[name$="-email"]').value = option.dataset.email;
    row.hidden = false;
    normalizeAuthorship();
    coauthorSearch.value = "";
    searchResults.replaceChildren();
  }

  continueButton?.addEventListener("click", () => {
    if (!personalDataIsValid()) return;
    showStep("modalidade");
  });
  modalityContinueButton?.addEventListener("click", () => {
    if (!modalityIsValid()) return;
    showStep("decisao");
  });
  form.addEventListener("submit", (event) => {
    const action = event.submitter?.value;
    if (!["inscrever", "atualizar"].includes(action)) return;
    if (modalityIsValid()) return;
    event.preventDefault();
    showStep("modalidade");
  });
  form.querySelector('[data-work-choice="yes"]')?.addEventListener("click", () => showStep("trabalho"));
  form.querySelector('[data-work-choice="no"]')?.addEventListener("click", () => {
    if (alreadyRegistered && updateButton) updateButton.hidden = false;
    if (!alreadyRegistered && finishButton) finishButton.hidden = false;
  });
  backButton?.addEventListener("click", () => {
    const currentStep = steps.find((step) => !step.hidden)?.dataset.registrationStep;
    if (currentStep === "trabalho") showStep("decisao");
    else if (currentStep === "decisao") showStep("modalidade");
    else showStep("pessoal");
  });
  addressStateSelect?.addEventListener("change", loadAddressCities);
  modalitySelect?.addEventListener("change", updateMealAvailability);
  modalitySelect?.addEventListener("change", () => {
    programsSection?.querySelectorAll('[name="dados-programacoes"]:checked').forEach((field) => {
      if (field.dataset.modalidade !== modalitySelect.value) field.checked = false;
    });
    programsSection?.querySelector("[data-registration-programs-required]")?.classList.remove("d-block");
    updateProgramAvailability();
    updateProgramSelectionCount();
    updateMealAvailability();
  });
  programThemeFilter?.addEventListener("change", updateProgramAvailability);
  programDateFilter?.addEventListener("change", updateProgramAvailability);
  programsSection?.addEventListener("change", (event) => {
    if (!event.target.matches('[name="dados-programacoes"]')) return;
    programsSection.querySelector("[data-registration-programs-required]")?.classList.remove("d-block");
    updateProgramConflicts();
    updateProgramSelectionCount();
    updateMealAvailability();
  });
  workStateSelect?.addEventListener("change", () => {
    municipalityList?.querySelectorAll("[data-municipality-row]:not([hidden])").forEach(
      (row) => loadMunicipalityOptions(row),
    );
  });
  workPresentationSelect?.addEventListener("change", updateProposalAxisAvailability);
  form.querySelector("[data-add-municipality]")?.addEventListener(
    "click", () => appendMunicipalityRow(),
  );
  municipalityList?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-municipality]");
    if (button) removeMunicipality(button.closest("[data-municipality-row]"));
  });
  form.querySelector("[data-add-formation]")?.addEventListener("click", () => addFormation());
  formationList?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-formation]");
    if (button) removeFormation(button.closest("[data-formation-row]"));
  });
  coauthorList?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-coauthor]");
    if (!button) return;
    const row = button.closest(".coauthor-row");
    const deleteInput = row.querySelector('input[name$="-DELETE"]');
    if (deleteInput) deleteInput.checked = true;
    row.hidden = true;
    normalizeAuthorship();
  });
  coauthorList?.addEventListener("change", (event) => {
    const row = event.target.closest(".coauthor-row");
    if (!row) return;
    if (event.target.matches('select[name$="-papel"]')) {
      if (event.target.value === "autor") {
        normalizeAuthorship(row);
      } else {
        const replacement = activeAuthorshipRows().find(
          (item) => item !== row
            && item.querySelector('select[name$="-papel"]')?.value === "autor",
        ) || activeAuthorshipRows().find((item) => item !== row) || row;
        normalizeAuthorship(replacement);
      }
    }
    if (event.target.matches('input[name$="-ordem"]')) moveAuthorshipRow(row);
  });
  coauthorSearch?.addEventListener("input", () => {
    searchResults.replaceChildren();
    clearTimeout(searchTimer);
    const query = coauthorSearch.value.trim();
    if (query.length < 3) return;
    searchTimer = setTimeout(() => searchCoauthors(query), 300);
  });
  searchResults?.addEventListener("click", (event) => {
    const option = event.target.closest(".coauthor-result");
    if (option) addCoauthor(option);
  });

  async function initialize() {
    await restoreDraft();
    groupProgramOptions();
    updateMealAvailability();
    updateProgramAvailability();
    updateProposalAxisAvailability();
    const initialStep = location.hash === "#trabalho-pane"
      ? "trabalho"
      : (form.dataset.initialStep || "pessoal");
    showStep(initialStep);
    formationList?.querySelectorAll("[data-formation-row]:not([hidden])").forEach(
      (row) => requireFormationFields(row, true),
    );
    updateFormationsEmptyState();
    form.querySelectorAll("[data-character-limit]").forEach((field) => {
      const limit = Number(field.dataset.characterLimit);
      const counter = document.createElement("small");
      counter.className = "field-character-counter form-text";
      const update = () => {
        counter.textContent = `${field.value.length} / ${limit} caracteres`;
        counter.classList.toggle("text-danger", field.value.length >= limit);
      };
      field.insertAdjacentElement("afterend", counter);
      field.addEventListener("input", update);
      update();
    });
  }

  initialize();
})();
