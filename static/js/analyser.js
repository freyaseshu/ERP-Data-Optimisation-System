const predefinedSelect = document.getElementById('predefinedSelect');
const queryInput = document.getElementById('queryInput');
const analyseBtn = document.getElementById('analyseBtn');
const analyseSpinner = document.getElementById('analyseSpinner');

predefinedSelect.addEventListener('change', () => {
  const key = predefinedSelect.value;
  if (key && PREDEFINED_QUERIES[key]) {
    queryInput.value = PREDEFINED_QUERIES[key];
  }
});

function severityBadge(sev) {
  return `<span class="badge badge-severity-${sev}">${sev.toUpperCase()}</span>`;
}

function renderExplainTable(rows) {
  const tbody = document.querySelector('#explainTable tbody');
  tbody.innerHTML = '';
  if (!rows || rows.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No rows returned.</td></tr>';
    return;
  }
  rows.forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${r.table ?? '-'}</td>
      <td>${r.type ?? '-'}</td>
      <td>${r.possible_keys ?? '-'}</td>
      <td>${r.key ?? '-'}</td>
      <td>${r.rows ?? '-'}</td>
      <td>${r.Extra ?? '-'}</td>`;
    tbody.appendChild(tr);
  });
}

function renderFindings(findings) {
  const container = document.getElementById('findingsList');
  container.innerHTML = '';
  findings.forEach(f => {
    const div = document.createElement('div');
    div.className = `finding-item ${f.severity}`;
    div.innerHTML = `<div class="d-flex justify-content-between">
        <strong>${f.issue}</strong> ${severityBadge(f.severity)}
      </div>
      <div class="small text-muted">${f.detail}</div>`;
    container.appendChild(div);
  });
}

analyseBtn.addEventListener('click', async () => {
  const query = queryInput.value.trim();
  const predefinedKey = predefinedSelect.value;
  if (!query && !predefinedKey) {
    showToast('Enter a SQL query or choose a predefined one.', 'error');
    return;
  }

  analyseSpinner.classList.remove('d-none');
  analyseBtn.disabled = true;

  const body = await apiCall('/api/analyse-query', {
    method: 'POST',
    body: JSON.stringify({ query, predefined_key: predefinedKey })
  });

  analyseSpinner.classList.add('d-none');
  analyseBtn.disabled = false;

  if (!body.success) {
    showToast(body.message || 'Analysis failed.', 'error');
    return;
  }

  document.getElementById('analyserEmptyState').classList.add('d-none');
  document.getElementById('analyserResults').classList.remove('d-none');
  document.getElementById('execTime').textContent = body.data.execution_time_ms;
  document.getElementById('rowsPreview').textContent = body.data.rows_previewed;
  renderExplainTable(body.data.explain_result);
  renderFindings(body.data.findings);
  showToast('Query analysed successfully.');
});
