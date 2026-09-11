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
  const workChoiceStep = form.querySelector('[data-registration-step="decisao"]');
  const continueButton = form.querySelector("[data-registration-continue]");
  const backButton = form.querySelector("[data-registration-back]");
  const finishButton = form.querySelector("[data-registration-finish]");
  const submitWorkButton = form.querySelector("[data-registration-submit]");
  const canSubmitWork = form.dataset.canSubmitWork === "true";
  const alreadyRegistered = form.dataset.alreadyRegistered === "true";
  let searchTimer;

  function showStep(stepName) {
    steps.forEach((step) => {
      step.hidden = step.dataset.registrationStep !== stepName;
    });
    if (continueButton) continueButton.hidden = stepName !== "pessoal";
    if (backButton) backButton.hidden = alreadyRegistered || stepName === "pessoal";
    if (finishButton) finishButton.hidden = true;
    if (submitWorkButton) submitWorkButton.hidden = stepName !== "trabalho";
    if (stepName === "decisao") workChoiceStep?.focus({ preventScroll: true });
  }

  function personalDataIsValid() {
    const fields = [...personalDataStep.querySelectorAll("input, select, textarea")];
    const invalidField = fields.find((field) => !field.checkValidity());
    if (!invalidField) return true;
    invalidField.reportValidity();
    invalidField.focus();
    return false;
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

    const formIndex = Number(totalFormsInput.value);
    const wrapper = document.createElement("div");
    wrapper.innerHTML = coauthorTemplate.innerHTML.replaceAll("__prefix__", formIndex);
    row = wrapper.firstElementChild;
    coauthorList.append(row);
    totalFormsInput.value = String(formIndex + 1);
    return row;
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
    if (canSubmitWork && workChoiceStep) showStep("decisao");
    else finishButton.hidden = false;
  });
  form.querySelector('[data-work-choice="yes"]')?.addEventListener("click", () => showStep("trabalho"));
  form.querySelector('[data-work-choice="no"]')?.addEventListener("click", () => {
    finishButton.hidden = false;
  });
  backButton?.addEventListener("click", () => {
    const currentStep = steps.find((step) => !step.hidden)?.dataset.registrationStep;
    showStep(currentStep === "trabalho" && canSubmitWork ? "decisao" : "pessoal");
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

  const shouldOpenWork = (alreadyRegistered && canSubmitWork)
    || form.dataset.initialStep === "trabalho"
    || location.hash === "#trabalho-pane";
  showStep(shouldOpenWork ? "trabalho" : "pessoal");
})();
