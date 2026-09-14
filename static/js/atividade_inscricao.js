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
  const municipalityList = form.querySelector("[data-municipality-list]");
  const municipalityTemplate = form.querySelector("[data-municipality-template]");
  const municipalityTotalForms = document.getElementById("id_municipio-TOTAL_FORMS");
  const draftScript = document.getElementById("registration-draft-data");
  const draftData = draftScript ? JSON.parse(draftScript.textContent) : {};
  let searchTimer;

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
    const field = modalityStep?.querySelector("select, input");
    if (!field || field.checkValidity()) return true;
    field.reportValidity();
    field.focus();
    return false;
  }

  function updateMealAvailability() {
    if (!mealsSection) return;
    const isInPerson = modalitySelect?.value === "presencial";
    mealsSection.hidden = !isInPerson;
    mealsSection.querySelectorAll('[name="dados-refeicoes"]').forEach((field) => {
      if (!isInPerson) field.checked = false;
    });
  }

  function updateProgramAvailability() {
    if (!programsSection) return;
    const modality = modalitySelect?.value;
    const theme = programThemeFilter?.value || "";
    const date = programDateFilter?.value || "";
    let availablePrograms = 0;
    let modalityPrograms = 0;
    programsSection.querySelectorAll('[name="dados-programacoes"]').forEach((field) => {
      const matchesModality = field.dataset.modalidade === modality;
      const matchesTheme = !theme || field.dataset.tematica === theme;
      const matchesDate = !date || field.dataset.data === date;
      const isAvailable = matchesModality && matchesTheme && matchesDate;
      const option = field.closest("li") || field.closest("div");
      if (option) option.hidden = !isAvailable;
      field.disabled = !matchesModality;
      if (!matchesModality) field.checked = false;
      if (matchesModality) modalityPrograms += 1;
      if (isAvailable) availablePrograms += 1;
    });
    const emptyMessage = programsSection.querySelector("[data-registration-programs-empty]");
    if (emptyMessage) emptyMessage.hidden = availablePrograms > 0;
    const emptyText = programsSection.querySelector("[data-registration-programs-empty-text]");
    if (emptyText) {
      emptyText.textContent = modalityPrograms > 0
        ? "Nenhuma programação corresponde aos filtros selecionados."
        : "Não há programações disponíveis para esta modalidade.";
    }
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
      searchResults.textContent = "Este coautor já foi adicionado.";
      return;
    }

    const row = getAvailableCoauthorRow();
    row.querySelector('input[name$="-usuario"]').value = option.dataset.id;
    row.querySelector('input[name$="-nome"]').value = option.dataset.name;
    row.querySelector('input[name$="-email"]').value = option.dataset.email;
    row.hidden = false;
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
  modalitySelect?.addEventListener("change", updateProgramAvailability);
  programThemeFilter?.addEventListener("change", updateProgramAvailability);
  programDateFilter?.addEventListener("change", updateProgramAvailability);
  programsSection?.addEventListener("change", updateProgramSelectionCount);
  workStateSelect?.addEventListener("change", () => {
    municipalityList?.querySelectorAll("[data-municipality-row]:not([hidden])").forEach(
      (row) => loadMunicipalityOptions(row),
    );
  });
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
    updateMealAvailability();
    updateProgramAvailability();
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
