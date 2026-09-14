document.addEventListener("DOMContentLoaded", () => {
  // Mantém os modais de salas sincronizados com os formsets do Django. O
  // backend repete todas as validações de permissão, modalidade e integridade.
  const roomForm = document.getElementById("activity-add-room-form");
  const scheduleForm = document.getElementById("activity-schedule-form");
  if (!roomForm && !scheduleForm) return;

  const roomModal = document.getElementById("activity-room-modal");
  const roomScheduleList = roomForm?.querySelector("[data-activity-room-schedules]");
  const roomScheduleTemplate = roomForm?.querySelector("[data-activity-room-schedule-template]");
  const totalRoomScheduleForms = roomForm?.querySelector('[name="nova_programacoes-TOTAL_FORMS"]');
  const roomErrors = roomForm?.querySelector("[data-activity-room-errors]");
  const roomSubmit = roomForm?.querySelector("[data-save-activity-room]");
  const successMessage = document.querySelector("[data-activity-room-success]");
  const linkedRooms = document.querySelector("[data-activity-linked-rooms]");
  const linkedEmpty = document.querySelector("[data-activity-linked-empty]");
  const scheduleModal = document.getElementById("activity-schedule-modal");
  const scheduleErrors = scheduleForm?.querySelector("[data-activity-schedule-errors]");
  const scheduleSubmit = scheduleForm?.querySelector("[data-save-activity-schedule]");
  const scheduleTitle = scheduleForm?.querySelector("#activity-schedule-modal-title");
  const scheduleRoom = scheduleForm?.querySelector("[data-activity-schedule-room]");

  function configureLink(container) {
    const modality = container.querySelector('[name$="-modalidade"]');
    const link = container.querySelector('[name$="-link"]');
    const linkContainer = link?.closest(".col-12");
    if (!modality || !link || !linkContainer || modality.dataset.linkConfigured) return;
    const update = () => {
      const online = modality.value === "online";
      link.disabled = !online;
      linkContainer.hidden = !online;
      if (!online) link.value = "";
    };
    modality.dataset.linkConfigured = "true";
    modality.addEventListener("change", update);
    update();
  }

  function showErrors(container, messages, fallback) {
    // Usa textContent para que mensagens retornadas pela API nunca virem HTML.
    const list = document.createElement("ul");
    list.className = "mb-0";
    (messages?.length ? messages : [fallback]).forEach((message) => {
      const item = document.createElement("li");
      item.textContent = message;
      list.append(item);
    });
    container.replaceChildren(list);
    container.hidden = false;
  }

  function addScheduleToRoomForm() {
    const index = Number(totalRoomScheduleForms.value);
    const wrapper = document.createElement("div");
    wrapper.innerHTML = roomScheduleTemplate.innerHTML.replaceAll("__prefix__", String(index)).trim();
    const row = wrapper.firstElementChild;
    roomScheduleList.append(row);
    totalRoomScheduleForms.value = String(index + 1);
    configureLink(row);
    row.querySelector("input:not([type=hidden]), select")?.focus();
  }

  function resetRoomForm() {
    // Todo cadastro de sala começa com ao menos uma programação visível.
    roomForm.reset();
    roomScheduleList.replaceChildren();
    totalRoomScheduleForms.value = "0";
    addScheduleToRoomForm();
    roomErrors.hidden = true;
    roomErrors.replaceChildren();
  }

  function setScheduleCount(roomCard) {
    const count = roomCard.querySelector("[data-activity-linked-schedules]").children.length;
    const label = roomCard.querySelector("[data-linked-schedule-count]")
      || roomCard.querySelector("header small");
    if (label) label.textContent = `${count} programaç${count === 1 ? "ão" : "ões"}`;
  }

  function createActionButton(className, iconClass, label, url) {
    const button = document.createElement("button");
    button.className = className;
    button.type = "button";
    button.dataset.url = url;
    const icon = document.createElement("i");
    icon.className = iconClass;
    button.append(icon, document.createTextNode(` ${label}`));
    return button;
  }

  function renderProgram(schedule, program) {
    // Os data attributes permitem reabrir o formulário sem uma nova consulta.
    schedule.dataset.programId = String(program.id);
    schedule.dataset.date = program.data_iso;
    schedule.dataset.shift = program.turno_value;
    schedule.dataset.modality = program.modalidade_value;
    schedule.dataset.link = program.link || "";
    schedule.dataset.themeId = String(program.tematica_id);
    schedule.dataset.description = program.descricao || "";
    schedule.dataset.capacity = String(program.capacidade);

    const content = document.createElement("div");
    content.className = "activity-linked-schedule-content";
    const theme = document.createElement("strong");
    theme.textContent = program.tematica;
    const meta = document.createElement("div");
    [
      ["bi bi-calendar3", program.data],
      ["bi bi-clock", program.turno],
      ["bi bi-broadcast", program.modalidade],
      ["bi bi-people", `${program.capacidade} vagas`],
    ].forEach(([iconClass, text]) => {
      const item = document.createElement("span");
      const icon = document.createElement("i");
      icon.className = iconClass;
      item.append(icon, document.createTextNode(` ${text}`));
      meta.append(item);
    });
    content.append(theme, meta);

    const actions = document.createElement("div");
    actions.className = "activity-linked-schedule-actions";
    if (linkedRooms.dataset.canEdit === "true") {
      const edit = createActionButton("btn btn-sm btn-outline-primary", "bi bi-pencil", "Editar", program.edit_url);
      edit.dataset.editLinkedSchedule = "";
      actions.append(edit);
    }
    if (linkedRooms.dataset.canDelete === "true") {
      const remove = createActionButton("btn btn-sm btn-outline-danger", "bi bi-trash", "Excluir", program.delete_url);
      remove.dataset.deleteLinkedSchedule = "";
      actions.append(remove);
    }
    schedule.replaceChildren(content, actions);
  }

  function appendLinkedRoom(room, roomPrograms) {
    if (!linkedRooms) return;
    let roomCard = linkedRooms.querySelector(`[data-room-id="${room.id}"]`);
    if (!roomCard) {
      roomCard = document.createElement("article");
      roomCard.className = "activity-linked-room";
      roomCard.dataset.activityLinkedRoom = "";
      roomCard.dataset.roomId = String(room.id);
      const header = document.createElement("header");
      const icon = document.createElement("span");
      icon.innerHTML = '<i class="bi bi-door-open"></i>';
      const title = document.createElement("div");
      const name = document.createElement("strong");
      const count = document.createElement("small");
      name.textContent = room.nome;
      count.dataset.linkedScheduleCount = "";
      title.append(name, count);
      header.append(icon, title);
      if (linkedRooms.dataset.canAdd === "true") {
        const add = createActionButton("btn btn-sm btn-outline-primary ms-auto", "bi bi-plus-lg", "Adicionar programação", room.add_schedule_url);
        add.dataset.addLinkedSchedule = "";
        add.dataset.roomName = room.nome;
        header.append(add);
      }
      const scheduleList = document.createElement("div");
      scheduleList.className = "activity-linked-schedules";
      scheduleList.dataset.activityLinkedSchedules = "";
      roomCard.append(header, scheduleList);
      linkedRooms.insertBefore(roomCard, linkedEmpty);
    }
    const scheduleList = roomCard.querySelector("[data-activity-linked-schedules]");
    roomPrograms.forEach((program) => {
      let schedule = scheduleList.querySelector(`[data-program-id="${program.id}"]`);
      if (!schedule) {
        schedule = document.createElement("div");
        schedule.className = "activity-linked-schedule";
        scheduleList.append(schedule);
      }
      renderProgram(schedule, program);
    });
    setScheduleCount(roomCard);
    if (linkedEmpty) linkedEmpty.hidden = true;
  }

  function scheduleField(name) {
    return scheduleForm.querySelector(`[name="programacao-${name}"]`);
  }

  function openScheduleModal(button, schedule = null) {
    scheduleForm.reset();
    scheduleForm.action = button.dataset.url;
    scheduleErrors.hidden = true;
    scheduleErrors.replaceChildren();
    scheduleTitle.textContent = schedule ? "Editar programação" : "Adicionar programação";
    scheduleRoom.textContent = button.dataset.roomName
      || button.closest("[data-activity-linked-room]").querySelector("header strong").textContent;
    if (schedule) {
      scheduleField("data").value = schedule.dataset.date;
      scheduleField("turno").value = schedule.dataset.shift;
      scheduleField("modalidade").value = schedule.dataset.modality;
      scheduleField("link").value = schedule.dataset.link;
      scheduleField("tematica").value = schedule.dataset.themeId;
      scheduleField("descricao").value = schedule.dataset.description;
      scheduleField("quantidade_max_participantes").value = schedule.dataset.capacity;
    }
    scheduleField("modalidade").dispatchEvent(new Event("change"));
    bootstrap.Modal.getOrCreateInstance(scheduleModal).show();
  }

  roomForm?.querySelectorAll("[data-activity-room-schedule]").forEach(configureLink);
  roomForm?.querySelector("[data-add-activity-room-schedule]")?.addEventListener("click", addScheduleToRoomForm);
  roomScheduleList?.addEventListener("click", (event) => {
    const remove = event.target.closest("[data-remove-activity-room-schedule]");
    if (!remove) return;
    const row = remove.closest("[data-activity-room-schedule]");
    const deleteInput = row.querySelector('[name$="-DELETE"]');
    if (deleteInput) deleteInput.checked = true;
    row.hidden = true;
    if (![...roomScheduleList.children].some((item) => !item.hidden)) addScheduleToRoomForm();
  });

  roomForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    roomErrors.hidden = true;
    roomSubmit.disabled = true;
    try {
      const response = await fetch(roomForm.action, { method: "POST", body: new FormData(roomForm), headers: { "X-Requested-With": "XMLHttpRequest" } });
      const responseData = await response.json();
      if (!response.ok) {
        showErrors(roomErrors, responseData.errors, "Não foi possível adicionar a sala.");
        return;
      }
      appendLinkedRoom(responseData.sala, responseData.programacoes);
      successMessage.textContent = responseData.message;
      successMessage.hidden = false;
      bootstrap.Modal.getOrCreateInstance(roomModal).hide();
      resetRoomForm();
    } catch (error) {
      showErrors(roomErrors, null, "Não foi possível adicionar a sala. Tente novamente.");
    } finally {
      roomSubmit.disabled = false;
    }
  });

  if (scheduleForm) configureLink(scheduleForm);
  linkedRooms?.addEventListener("click", async (event) => {
    // A lista usa delegação porque novos cartões são inseridos após o carregamento.
    const add = event.target.closest("[data-add-linked-schedule]");
    if (add) {
      openScheduleModal(add);
      return;
    }
    const edit = event.target.closest("[data-edit-linked-schedule]");
    if (edit) {
      openScheduleModal(edit, edit.closest("[data-program-id]"));
      return;
    }
    const remove = event.target.closest("[data-delete-linked-schedule]");
    if (!remove || !window.confirm("Deseja excluir esta programação da atividade?")) return;
    remove.disabled = true;
    try {
      const csrf = scheduleForm?.querySelector('[name="csrfmiddlewaretoken"]')?.value
        || roomForm.querySelector('[name="csrfmiddlewaretoken"]').value;
      const body = new FormData();
      body.append("csrfmiddlewaretoken", csrf);
      const response = await fetch(remove.dataset.url, { method: "POST", body });
      const responseData = await response.json();
      if (!response.ok) throw new Error();
      const schedule = remove.closest("[data-program-id]");
      const roomCard = schedule.closest("[data-activity-linked-room]");
      schedule.remove();
      if (responseData.room_empty) roomCard.remove();
      else setScheduleCount(roomCard);
      if (!linkedRooms.querySelector("[data-activity-linked-room]") && linkedEmpty) linkedEmpty.hidden = false;
      successMessage.textContent = responseData.message;
      successMessage.hidden = false;
    } catch (error) {
      window.alert("Não foi possível excluir a programação. Tente novamente.");
      remove.disabled = false;
    }
  });

  scheduleForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    scheduleErrors.hidden = true;
    scheduleSubmit.disabled = true;
    try {
      const response = await fetch(scheduleForm.action, { method: "POST", body: new FormData(scheduleForm), headers: { "X-Requested-With": "XMLHttpRequest" } });
      const responseData = await response.json();
      if (!response.ok) {
        showErrors(scheduleErrors, responseData.errors, "Não foi possível salvar a programação.");
        return;
      }
      appendLinkedRoom(responseData.sala, [responseData.programacao]);
      successMessage.textContent = responseData.message;
      successMessage.hidden = false;
      bootstrap.Modal.getOrCreateInstance(scheduleModal).hide();
    } catch (error) {
      showErrors(scheduleErrors, null, "Não foi possível salvar a programação. Tente novamente.");
    } finally {
      scheduleSubmit.disabled = false;
    }
  });
});
