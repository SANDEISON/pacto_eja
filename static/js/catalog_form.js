document.addEventListener("DOMContentLoaded", () => {
  "use strict";

  function normalize(value) {
    return value
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("pt-BR")
      .trim();
  }

  document.querySelectorAll("select[data-searchable-user-select]").forEach((select, index) => {
    const options = [...select.options];
    const wrapper = document.createElement("div");
    wrapper.className = "searchable-user-select";

    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "form-select searchable-user-select-trigger";
    trigger.setAttribute("role", "combobox");
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");

    const menu = document.createElement("div");
    menu.className = "searchable-user-select-menu";
    menu.hidden = true;

    const search = document.createElement("input");
    search.type = "search";
    search.className = "form-control searchable-user-select-search";
    search.placeholder = select.dataset.searchPlaceholder || "Buscar usuário";
    search.autocomplete = "off";
    search.setAttribute("aria-label", search.placeholder);

    const list = document.createElement("div");
    const listId = `searchable-user-options-${index}`;
    list.id = listId;
    list.className = "searchable-user-select-options";
    list.setAttribute("role", "listbox");
    trigger.setAttribute("aria-controls", listId);

    const feedback = document.createElement("div");
    feedback.className = "searchable-user-select-feedback";
    feedback.setAttribute("aria-live", "polite");

    function updateTrigger() {
      const selected = options.find((option) => option.value === select.value) || options[0];
      trigger.textContent = selected?.textContent.trim() || "Selecione um usuário";
      trigger.classList.toggle("has-selection", Boolean(select.value));
    }

    function closeMenu() {
      menu.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
    }

    function choose(option) {
      select.value = option.value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      updateTrigger();
      closeMenu();
      trigger.focus();
    }

    function renderOptions() {
      const query = normalize(search.value);
      const matches = options.filter((option) => (
        !query || normalize(option.textContent).includes(query)
      ));
      list.replaceChildren();
      matches.forEach((option) => {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "searchable-user-select-option";
        item.textContent = option.textContent.trim();
        item.dataset.value = option.value;
        item.setAttribute("role", "option");
        item.setAttribute("aria-selected", String(option.value === select.value));
        if (option.value === select.value) item.classList.add("selected");
        item.addEventListener("click", () => choose(option));
        list.append(item);
      });
      const userCount = matches.filter((option) => option.value).length;
      feedback.textContent = query
        ? `${userCount} usuário${userCount === 1 ? " encontrado" : "s encontrados"}`
        : "";
      feedback.hidden = Boolean(matches.length);
      if (!matches.length) feedback.textContent = "Nenhum usuário encontrado.";
    }

    trigger.addEventListener("click", () => {
      const willOpen = menu.hidden;
      menu.hidden = !willOpen;
      trigger.setAttribute("aria-expanded", String(willOpen));
      if (willOpen) {
        search.value = "";
        renderOptions();
        search.focus();
      }
    });
    search.addEventListener("input", renderOptions);
    wrapper.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeMenu();
        trigger.focus();
      }
    });
    document.addEventListener("click", (event) => {
      if (!wrapper.contains(event.target)) closeMenu();
    });

    select.before(wrapper);
    select.hidden = true;
    menu.append(search, list, feedback);
    wrapper.append(trigger, menu);
    updateTrigger();
  });
});
