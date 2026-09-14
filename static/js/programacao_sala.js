document.addEventListener("DOMContentLoaded", () => {
  // O backend continua responsável por validar a modalidade. Aqui apenas
  // ocultamos o campo de link quando a programação é presencial.
  function configurarLink(container) {
    const modalidade = container.querySelector('[name$="modalidade"]');
    const link = container.querySelector('[name$="link"]');
    if (!modalidade || !link || modalidade.dataset.linkConfigured) return;
    const linkContainer = link.closest(".col-12");
    function atualizarLink() {
      const isOnline = modalidade.value === "online";
      link.disabled = !isOnline;
      linkContainer.hidden = !isOnline;
      if (!isOnline) link.value = "";
    }
    modalidade.dataset.linkConfigured = "true";
    modalidade.addEventListener("change", atualizarLink);
    atualizarLink();
  }

  const editors = document.getElementById("room-schedule-editors");
  const summaries = document.getElementById("room-schedules-summary");
  const emptyState = document.getElementById("room-schedules-empty");
  document.querySelectorAll("[data-room-schedule-form]").forEach(configurarLink);
  if (!editors || !summaries) {
    configurarLink(document);
    return;
  }

  const forms = () => [...editors.querySelectorAll("[data-room-schedule-form]")];
  const summaryCards = () => [...summaries.querySelectorAll("[data-room-schedule-summary]")];
  const findEditor = (index) => forms().find((item) => item.dataset.formIndex === index);
  const findSummary = (index) => summaryCards().find((item) => item.dataset.formIndex === index);

  function updateEmptyState() {
    if (emptyState) emptyState.hidden = summaryCards().some((item) => !item.hidden);
  }

  function snapshot(editor) {
    // Mantém uma cópia temporária para que "Cancelar" restaure a edição.
    return [...editor.querySelectorAll("input, select, textarea")].map((field) => ({
      name: field.name,
      value: field.value,
      checked: field.checked,
    }));
  }

  function restore(editor, values) {
    values.forEach((saved) => {
      const field = [...editor.querySelectorAll("input, select, textarea")].find(
        (candidate) => candidate.name === saved.name,
      );
      if (!field) return;
      field.value = saved.value;
      field.checked = saved.checked;
    });
    editor.querySelector('[name$="modalidade"]')?.dispatchEvent(new Event("change"));
  }

  function openEditor(editor) {
    forms().forEach((other) => {
      if (other !== editor && !other.hidden) {
        other.querySelector("[data-cancel-schedule]")?.click();
      }
    });
    editor.dataset.snapshot = JSON.stringify(snapshot(editor));
    editor.hidden = false;
    editor.scrollIntoView({ behavior: "smooth", block: "nearest" });
    editor.querySelector("input:not([type=hidden]), select, textarea")?.focus();
  }

  const value = (editor, suffix) => editor.querySelector(`[name$="-${suffix}"]`)?.value || "";
  function selectedText(editor, suffix) {
    const select = editor.querySelector(`[name$="-${suffix}"]`);
    return select?.selectedOptions[0]?.text || "—";
  }
  function setMeta(element, iconClass, text) {
    const icon = document.createElement("i");
    icon.className = iconClass;
    element.replaceChildren(icon, document.createTextNode(` ${text}`));
  }

  function createSummary(editor) {
    // Novos formsets ainda não têm um cartão renderizado pelo Django.
    const summary = document.createElement("article");
    summary.className = "room-schedule-summary-card";
    summary.dataset.roomScheduleSummary = "";
    summary.dataset.formIndex = editor.dataset.formIndex;
    const icon = document.createElement("div");
    icon.className = "room-schedule-summary-icon";
    icon.innerHTML = '<i class="bi bi-calendar2-event"></i>';
    const content = document.createElement("div");
    content.className = "room-schedule-summary-content";
    content.innerHTML = '<strong data-summary-theme></strong><div class="room-schedule-summary-meta"><span data-summary-date></span><span data-summary-shift></span><span data-summary-modality></span><span data-summary-capacity></span></div>';
    const actions = document.createElement("div");
    actions.className = "room-schedule-summary-actions";
    actions.innerHTML = '<button class="btn btn-sm btn-outline-primary" type="button" data-edit-schedule><i class="bi bi-pencil"></i> Editar</button><button class="btn btn-sm btn-outline-danger" type="button" data-delete-schedule><i class="bi bi-trash"></i> Excluir</button>';
    summary.append(icon, content, actions);
    summaries.insertBefore(summary, emptyState);
    bindSummary(summary);
    return summary;
  }

  function updateSummary(editor) {
    const summary = findSummary(editor.dataset.formIndex) || createSummary(editor);
    const rawDate = value(editor, "data").split("-");
    const date = rawDate.length === 3 ? `${rawDate[2]}/${rawDate[1]}/${rawDate[0]}` : "—";
    summary.querySelector("[data-summary-theme]").textContent = selectedText(editor, "tematica");
    setMeta(summary.querySelector("[data-summary-date]"), "bi bi-calendar3", date);
    setMeta(summary.querySelector("[data-summary-shift]"), "bi bi-clock", selectedText(editor, "turno"));
    setMeta(summary.querySelector("[data-summary-modality]"), "bi bi-broadcast", selectedText(editor, "modalidade"));
    setMeta(summary.querySelector("[data-summary-capacity]"), "bi bi-people", `${value(editor, "quantidade_max_participantes")} vagas`);
    summary.hidden = false;
    updateEmptyState();
  }

  function bindSummary(summary) {
    summary.querySelector("[data-edit-schedule]")?.addEventListener("click", () => {
      const editor = findEditor(summary.dataset.formIndex);
      if (editor) openEditor(editor);
    });
    summary.querySelector("[data-delete-schedule]")?.addEventListener("click", () => {
      const editor = findEditor(summary.dataset.formIndex);
      const deleteField = editor?.querySelector('[name$="-DELETE"]');
      if (deleteField) deleteField.checked = true;
      if (editor) editor.hidden = true;
      summary.hidden = true;
      updateEmptyState();
    });
  }

  function bindEditor(editor) {
    configurarLink(editor);
    editor.querySelectorAll("[data-cancel-schedule]").forEach((button) => {
      button.addEventListener("click", () => {
        if (editor.dataset.newSchedule === "true") {
          const deleteField = editor.querySelector('[name$="-DELETE"]');
          if (deleteField) deleteField.checked = true;
          findSummary(editor.dataset.formIndex)?.remove();
        } else if (editor.dataset.snapshot) {
          restore(editor, JSON.parse(editor.dataset.snapshot));
        }
        editor.hidden = true;
        updateEmptyState();
      });
    });
    editor.querySelector("[data-finish-schedule]")?.addEventListener("click", () => {
      const fields = editor.querySelectorAll("input:not([type=hidden]):not([disabled]), select:not([disabled]), textarea:not([disabled])");
      if (![...fields].every((field) => field.reportValidity())) return;
      const deleteField = editor.querySelector('[name$="-DELETE"]');
      if (deleteField) deleteField.checked = false;
      updateSummary(editor);
      editor.dataset.newSchedule = "false";
      editor.hidden = true;
    });
    if (editor.querySelector(".invalid-feedback, .alert-danger")) editor.hidden = false;
  }

  summaryCards().forEach(bindSummary);
  forms().forEach(bindEditor);
  updateEmptyState();

  const template = document.getElementById("empty-room-schedule-form");
  const addButton = document.getElementById("add-room-schedule");
  const totalForms = document.getElementById("id_programacoes-TOTAL_FORMS");
  if (!template || !addButton || !totalForms) return;
  addButton.addEventListener("click", () => {
    // O índice do management form deve acompanhar cada formulário adicionado.
    const index = Number(totalForms.value);
    const wrapper = document.createElement("div");
    wrapper.innerHTML = template.innerHTML.replaceAll("__prefix__", String(index)).trim();
    const editor = wrapper.firstElementChild;
    editor.dataset.newSchedule = "true";
    editors.appendChild(editor);
    totalForms.value = String(index + 1);
    bindEditor(editor);
    openEditor(editor);
  });
});
