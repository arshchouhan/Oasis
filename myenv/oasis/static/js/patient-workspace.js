(() => {
  const selectedLists = new Map();
  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const icon = name => element('span', 'material-symbols-outlined', name);
  const button = (label, className, handler) => {
    const node = element('button', className, label);
    node.type = 'button'; node.onclick = handler;
    return node;
  };
  window.openPatientWorkspace = async (container, url, mode) => {
    const root = element('div', 'personal-workspace');
    container.replaceChildren(root);
    root.setAttribute('aria-busy', 'true');
    for (let i = 0; i < 3; i++) root.append(element('div', 'pw-loading'));
    let data;
    let selected = selectedLists.get(url);
    async function api(body) {
      const response = await fetch(url, body ? {
        method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': document.querySelector('#personalWorkspaceToken input')?.value || ''},
        body: JSON.stringify(body)
      } : {cache: 'no-store'});
      if (response.redirected) throw new Error('Please sign in again.');
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Could not save. Please try again.');
      data = payload;
    }
    function error(message, host = root) {
      host.querySelector('.pw-error')?.remove();
      const alert = element('div', 'pw-error', message);
      alert.setAttribute('role', 'alert'); host.prepend(alert);
    }
    async function mutate(body, source) {
      source.disabled = true;
      try { await api(body); if (root.isConnected) render(); }
      catch (e) { if (root.isConnected) {source.disabled = false; error(e.message);} }
    }
    function editor(kind, item = {}) {
      root.querySelector('.pw-editor')?.remove();
      const form = element('form', 'pw-editor');
      form.append(element('h4', '', kind === 'list' ? 'Create new list' : (item.id ? 'Edit ' : 'New ') + kind));
      function field(name, title, value, multiline = false, required = false, maxLength = 200) {
        const label = element('label', '', title);
        const input = element(multiline ? 'textarea' : 'input');
        input.name = name; input.value = value || ''; input.required = required; input.maxLength = maxLength;
        if (name === 'due_date') input.type = 'date';
        label.append(input); form.append(label); return input;
      }
      const title = kind === 'list' ? field('name', 'List name', '', false, true, 80) : field('title', 'Title', item.title, false, true);
      if (kind !== 'list') field(kind === 'task' ? 'notes' : 'body', 'Notes (optional)', item.notes || item.body, true, false, 5000);
      if (kind === 'task') field('due_date', 'Due date (optional)', item.due_date);
      const actions = element('div', 'pw-editor-actions');
      actions.append(button('Cancel', '', () => {form.remove(); root.querySelector('.pw-add,.pw-new-list')?.focus();}));
      const save = element('button', '', kind === 'list' ? 'Done' : 'Save'); save.type = 'submit'; save.disabled = !title.value.trim();
      title.addEventListener('input', () => { save.disabled = !title.value.trim(); });
      actions.append(save); form.append(actions); root.prepend(form); title.focus();
      form.onsubmit = async event => {
        event.preventDefault(); save.disabled = true; save.textContent = 'Saving…';
        const values = Object.fromEntries(new FormData(form));
        const body = {...values, action: kind === 'list' ? 'create_list' : 'save_' + kind};
        if (item.id) body.id = item.id;
        if (kind === 'task') body.list_id = selected;
        try {
          await api(body);
          if (kind === 'list') { selected = data.lists[data.lists.length - 1].id; selectedLists.set(url, selected); }
          if (root.isConnected) {render(); root.querySelector('.pw-add')?.focus();}
        } catch (e) { if (root.isConnected) {save.disabled = false; save.textContent = 'Save'; error(e.message, form);} }
      };
    }
    function card(item, kind) {
      const row = element('article', 'pw-row' + (item.completed ? ' pw-done' : ''));
      if (kind === 'task') {
        const check = element('input'); check.type = 'checkbox'; check.checked = item.completed;
        check.setAttribute('aria-label', 'Mark ' + item.title + (item.completed ? ' incomplete' : ' complete'));
        check.onchange = async () => {
          check.disabled = true;
          try { await api({action: 'complete_task', id: item.id, completed: check.checked}); if (root.isConnected) render(); }
          catch (e) { check.checked = item.completed; check.disabled = false; if (root.isConnected) error(e.message); }
        };
        row.append(check);
      }
      const body = element('div', 'pw-item-body');
      body.append(button(item.title, 'pw-edit', () => editor(kind, item)));
      if (item.notes || item.body) body.append(element('p', 'pw-description', item.notes || item.body));
      if (item.due_date) {
        const due = element('span', 'pw-due');
        due.append(icon('schedule'), document.createTextNode(new Date(item.due_date + 'T12:00:00').toLocaleDateString(undefined, {day:'numeric', month:'short', year:'numeric'})));
        body.append(due);
      }
      const remove = button('', 'pw-delete', () => {
        if (window.confirm('Delete this ' + kind + '?')) mutate({action: 'delete_' + kind, id: item.id}, remove);
      });
      remove.append(icon('delete_outline')); remove.setAttribute('aria-label', 'Delete ' + item.title);
      row.append(body, remove); return row;
    }
    function render() {
      root.replaceChildren(); root.removeAttribute('aria-busy');
      if (mode === 'tasks') {
        if (!data.lists.some(list => list.id === selected)) selected = data.lists[0]?.id;
        selectedLists.set(url, selected);
        const toolbar = element('div', 'pw-toolbar');
        const select = element('select'); select.setAttribute('aria-label', 'Task list');
        if (!data.lists.length) { const option = element('option', '', 'My Tasks'); select.append(option); select.disabled = true; }
        data.lists.forEach(list => { const option = element('option', '', list.name); option.value = list.id; option.selected = list.id === selected; select.append(option); });
        select.onchange = () => {selected = Number(select.value); selectedLists.set(url, selected); render();};
        toolbar.append(select, button('New list', 'pw-new-list', () => editor('list'))); root.append(toolbar);
      }
      const add = button('', 'pw-add', () => editor(mode === 'notes' ? 'note' : 'task'));
      add.append(icon(mode === 'notes' ? 'edit_note' : 'add_task'), document.createTextNode(mode === 'notes' ? 'Take a note' : 'Add a task'));
      add.disabled = mode === 'tasks' && !selected; root.append(add);
      const items = mode === 'notes' ? data.notes : data.tasks.filter(task => task.task_list_id === selected);
      if (!items.length) root.append(element('p', 'pw-empty', mode === 'notes' ? 'Keep your observations and reminders here. Your notes are private to your account.' : selected ? 'Nothing on your list yet. Add a task and any notes you need.' : 'Create your first list to start adding tasks.'));
      const entries = element('div', 'pw-items');
      let completed = false;
      items.forEach(item => {
        if (item.completed && !completed) {entries.append(element('h4', 'pw-section-label', 'Completed')); completed = true;}
        entries.append(card(item, mode === 'notes' ? 'note' : 'task'));
      }); root.append(entries);
    }
    try {await api(); if (root.isConnected) render();}
    catch (e) {
      if (!root.isConnected) return;
      root.replaceChildren(); root.removeAttribute('aria-busy'); error(e.message);
      root.append(button('Try again', 'pw-new-list', () => window.openPatientWorkspace(container, url, mode)));
    }
  };
})();
