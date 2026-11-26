(() => {
  const $ = (id) => document.getElementById(id);
  const pageSize = 100;
  const state = {
    base: sessionStorage.getItem('neudb-api-url') || 'http://127.0.0.1:8000',
    key: sessionStorage.getItem('neudb-api-key') || '',
    table: '',
    records: [],
    total: 0,
    offset: 0,
    editing: null,
  };
  const connectionDialog = $('connection-dialog');
  const recordDialog = $('record-dialog');

  function showNotice(message, error = false) {
    const element = $('notice');
    element.textContent = message;
    element.className = `notice${error ? ' error' : ''}`;
    element.hidden = false;
  }

  function clearNotice() {
    $('notice').hidden = true;
  }

  function localApiOrigin(value) {
    const url = new URL(value);
    const hostname = url.hostname.toLowerCase();
    const loopback = hostname === 'localhost' || hostname === '[::1]' || hostname === '::1' ||
      /^127(?:\.\d{1,3}){3}$/.test(hostname);
    if (url.protocol !== 'http:' || !loopback) {
      throw new Error('Use an http:// localhost, 127.0.0.1, or [::1] API URL.');
    }
    return url.origin;
  }

  async function request(path, options = {}) {
    const headers = { 'X-API-Key': state.key, ...(options.headers || {}) };
    if (options.body) headers['Content-Type'] = 'application/json';
    const response = await fetch(`${state.base}${path}`, {
      ...options,
      headers,
      credentials: 'omit',
      redirect: 'error',
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail || body);
      throw new Error(detail || `Request failed (${response.status})`);
    }
    return body;
  }

  function setConnected(connected) {
    $('connection-dot').classList.toggle('online', connected);
    $('connection-label').textContent = connected ? 'Connected' : 'Not connected';
  }

  function openDialog(dialog) {
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
  }

  function closeDialog(dialog) {
    if (typeof dialog.close === 'function') dialog.close();
    else dialog.removeAttribute('open');
  }

  async function connect() {
    try {
      state.base = localApiOrigin($('api-url').value.trim());
      state.key = $('api-key').value.trim();
      await request('/health');
      const data = await request('/tables');
      sessionStorage.setItem('neudb-api-url', state.base);
      sessionStorage.setItem('neudb-api-key', state.key);
      setConnected(true);
      $('welcome').hidden = true;
      $('workspace').hidden = false;
      renderTables(data.tables);
      $('add-record').disabled = data.tables.length === 0;
      clearNotice();
      if (data.tables[0]) await selectTable(data.tables[0]);
    } catch (error) {
      setConnected(false);
      showNotice(error.message || 'Could not connect to neuDB.', true);
    }
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    }[character]));
  }

  function renderTables(tables) {
    $('table-list').innerHTML = tables.length
      ? tables.map((name) => `<button type="button" class="table-item${name === state.table ? ' active' : ''}" data-table="${escapeHtml(name)}">▦ ${escapeHtml(name)}</button>`).join('')
      : '<p class="muted">No tables yet.</p>';
    document.querySelectorAll('[data-table]').forEach((button) => {
      button.onclick = () => selectTable(button.dataset.table);
    });
  }

  async function selectTable(name) {
    state.table = name;
    state.offset = 0;
    $('table-title').textContent = name;
    $('records-caption').textContent = `Records in ${name}`;
    $('record-search').value = '';
    $('add-record').disabled = false;
    document.querySelectorAll('[data-table]').forEach((button) => {
      button.classList.toggle('active', button.dataset.table === name);
    });
    await loadRecords();
  }

  async function loadRecords() {
    try {
      clearNotice();
      const data = await request(`/tables/${encodeURIComponent(state.table)}/records?limit=${pageSize}&offset=${state.offset}`);
      state.total = data.total;
      const maxOffset = Math.max(0, (Math.floor((state.total - 1) / pageSize)) * pageSize);
      if (state.offset > maxOffset) {
        state.offset = maxOffset;
        return loadRecords();
      }
      state.records = data.records;
      renderRecords();
    } catch (error) {
      showNotice(error.message, true);
    }
  }

  function renderRecords() {
    const query = $('record-search').value.trim().toLowerCase();
    const records = state.records.filter((record) => !query || JSON.stringify(record).toLowerCase().includes(query));
    const page = Math.floor(state.offset / pageSize) + 1;
    $('record-count').textContent = `${state.total} record${state.total === 1 ? '' : 's'} · page ${page}`;
    const start = state.total === 0 ? 0 : state.offset + 1;
    const end = Math.min(state.offset + state.records.length, state.total);
    $('pagination-status').textContent = state.total === 0 ? 'No records' : `Showing ${start}–${end} of ${state.total}`;
    $('previous-page').disabled = state.offset === 0;
    $('next-page').disabled = state.offset + pageSize >= state.total;
    $('empty-state').hidden = records.length > 0;
    $('empty-state').textContent = query ? 'No matching records on this page.' : 'No records on this page.';
    if (!records.length) {
      $('records-head').innerHTML = '';
      $('records-body').innerHTML = '';
      return;
    }
    const keys = [...new Set(records.flatMap((record) => Object.keys(record)))];
    $('records-head').innerHTML = `<tr>${keys.map((key) => `<th scope="col">${escapeHtml(key)}</th>`).join('')}<th scope="col">Actions</th></tr>`;
    $('records-body').innerHTML = records.map((record) => `<tr>${keys.map((key) => `<td>${escapeHtml(formatValue(record[key]))}</td>`).join('')}<td class="row-actions"><button type="button" data-edit="${escapeHtml(record.id)}" aria-label="Edit record ${escapeHtml(record.id)}">Edit</button><button type="button" class="delete" data-delete="${escapeHtml(record.id)}" aria-label="Delete record ${escapeHtml(record.id)}">Delete</button></td></tr>`).join('');
    document.querySelectorAll('[data-edit]').forEach((button) => button.onclick = () => editRecord(button.dataset.edit));
    document.querySelectorAll('[data-delete]').forEach((button) => button.onclick = () => deleteRecord(button.dataset.delete));
  }

  function formatValue(value) {
    return typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value ?? '');
  }

  function editRecord(id) {
    const record = state.records.find((item) => item.id === id);
    if (!record) return;
    state.editing = id;
    $('record-mode').textContent = 'EDIT RECORD';
    $('record-dialog-title').textContent = 'Edit record';
    $('record-json').value = JSON.stringify(record, null, 2);
    openDialog(recordDialog);
  }

  async function saveRecord(event) {
    event.preventDefault();
    try {
      const record = JSON.parse($('record-json').value);
      if (!record || Array.isArray(record) || typeof record !== 'object') throw new Error('Enter a JSON object.');
      if (state.editing) {
        delete record.id;
        await request(`/tables/${encodeURIComponent(state.table)}/records/${encodeURIComponent(state.editing)}`, {
          method: 'PATCH',
          body: JSON.stringify(record),
        });
      } else {
        await request(`/tables/${encodeURIComponent(state.table)}/records`, {
          method: 'POST',
          body: JSON.stringify(record),
        });
      }
      closeDialog(recordDialog);
      state.editing = null;
      await loadRecords();
      showNotice('Record saved.');
    } catch (error) {
      showNotice(error.message || 'Invalid JSON.', true);
    }
  }

  async function deleteRecord(id) {
    if (!confirm('Delete this record permanently?')) return;
    try {
      await request(`/tables/${encodeURIComponent(state.table)}/records/${encodeURIComponent(id)}`, { method: 'DELETE' });
      await loadRecords();
      showNotice('Record deleted.');
    } catch (error) {
      showNotice(error.message, true);
    }
  }

  async function createTable() {
    const name = prompt('New table name (letters, numbers, underscores):');
    if (!name) return;
    try {
      await request('/tables', { method: 'POST', body: JSON.stringify({ name }) });
      const data = await request('/tables');
      renderTables(data.tables);
      await selectTable(name);
      showNotice('Table created.');
    } catch (error) {
      showNotice(error.message, true);
    }
  }

  $('connection-form').addEventListener('submit', (event) => {
    event.preventDefault();
    closeDialog(connectionDialog);
    connect();
  });
  $('open-connection').onclick = () => openDialog(connectionDialog);
  $('new-table').onclick = createTable;
  $('refresh').onclick = loadRecords;
  $('previous-page').onclick = () => {
    state.offset = Math.max(0, state.offset - pageSize);
    loadRecords();
  };
  $('next-page').onclick = () => {
    state.offset += pageSize;
    loadRecords();
  };
  $('add-record').onclick = () => {
    state.editing = null;
    $('record-mode').textContent = 'NEW RECORD';
    $('record-dialog-title').textContent = 'Add record';
    $('record-json').value = '{\n  "content": ""\n}';
    openDialog(recordDialog);
  };
  $('record-form').addEventListener('submit', saveRecord);
  $('record-search').addEventListener('input', renderRecords);
  document.querySelectorAll('[data-close]').forEach((button) => button.onclick = () => closeDialog(button.closest('dialog')));
  $('api-url').value = state.base;
  $('api-key').value = state.key;
  if (state.key) connect();
})();
