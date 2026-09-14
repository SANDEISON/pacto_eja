document.addEventListener("DOMContentLoaded", () => {
  // Controla somente a experiência de inclusão e remoção. Datas duplicadas e
  // período da atividade são validados novamente pelos formulários Django.
  const list = document.querySelector("[data-meal-list]");
  const template = document.querySelector("[data-meal-template]");
  const totalForms = document.getElementById("id_refeicoes-TOTAL_FORMS");
  const addButton = document.querySelector("[data-add-meal]");
  if (!list || !template || !totalForms || !addButton) return;

  function bindRow(row) {
    // Formsets removem registros existentes marcando o campo DELETE.
    row.querySelector("[data-remove-meal]")?.addEventListener("click", () => {
      const deleteField = row.querySelector('[name$="-DELETE"]');
      if (deleteField) deleteField.checked = true;
      row.querySelectorAll("select, input").forEach((field) => {
        if (field !== deleteField) field.required = false;
      });
      row.hidden = true;
    });
  }

  list.querySelectorAll("[data-meal-row]").forEach(bindRow);
  addButton.addEventListener("click", () => {
    // Substitui o prefixo do template pelo próximo índice esperado no POST.
    const index = Number(totalForms.value);
    const wrapper = document.createElement("div");
    wrapper.innerHTML = template.innerHTML.replaceAll("__prefix__", String(index)).trim();
    const row = wrapper.firstElementChild;
    list.appendChild(row);
    totalForms.value = String(index + 1);
    bindRow(row);
    row.querySelector("select, input")?.focus();
  });
});
