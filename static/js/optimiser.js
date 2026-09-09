const optimiserQueryInput = document.getElementById('optimiserQueryInput');
const optimiseBtn = document.getElementById('optimiseBtn');
const optimiseSpinner = document.getElementById('optimiseSpinner');

let lastReport = null;

function renderList(elId, items) {
  const el = document.getElementById(elId);
  el.innerHTML = '';
  if (!items || items.length === 0) {
    el.innerHTML = '<li class="list-group-item text-muted">None</li>';
    return;
  }
  items.forEach(item => {
    const li = document.createElement('li');
    li.className = 'list-group-item';
    li.textContent = item;
    el.appendChild(li);
  });
}

function renderOptimiserExplainTable(rows) {
  const tbody = document.querySelector('#optimiserExplainTable tbody');
  tbody.innerHTML = '';
  if (!rows || rows.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No rows returned.</td></tr>';
    return;
  }
  rows.forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${r.table ?? '-'}</td><td>${r.type ?? '-'}</td>
      <td>${r.possible_keys ?? '-'}</td><td>${r.key ?? '-'}</td>
      <td>${r.rows ?? '-'}</td><td>${r.Extra ?? '-'}</td>`;
    tbody.appendChild(tr);
  });
}

optimiseBtn.addEventListener('click', async () => {
  const query = optimiserQueryInput.value.trim();
  if (!query) { showToast('Enter a SQL query.', 'error'); return; }

  optimiseSpinner.classList.remove('d-none');
  optimiseBtn.disabled = true;

  const body = await apiCall('/api/optimise-query', {
    method: 'POST',
    body: JSON.stringify({ query })
  });

  optimiseSpinner.classList.add('d-none');
  optimiseBtn.disabled = false;

  if (!body.success) {
    showToast(body.message || 'Optimisation failed.', 'error');
    return;
  }

  lastReport = body.data;
  document.getElementById('optimiserEmptyState').classList.add('d-none');
  document.getElementById('optimiserResults').classList.remove('d-none');

  renderList('problemsList', lastReport.detected_problems);
  renderList('suggestionsList', lastReport.optimization_suggestions);
  document.getElementById('execBefore').textContent = lastReport.execution_time_before_ms;
  document.getElementById('execAfter').textContent = '-';
  document.getElementById('improvementPct').textContent = '-';
  renderOptimiserExplainTable(lastReport.explain_result);

  const indexCard = document.getElementById('indexSuggestionCard');
  if (lastReport.index_suggestion_sql) {
    indexCard.style.display = 'block';
    document.getElementById('indexSuggestionSql').textContent = lastReport.index_suggestion_sql;
  } else {
    indexCard.style.display = 'none';
  }

  const optQueryCard = document.getElementById('optimizedQueryCard');
  if (lastReport.optimized_query) {
    optQueryCard.style.display = 'block';
    document.getElementById('optimizedQuerySql').textContent = lastReport.optimized_query;
  } else {
    optQueryCard.style.display = 'none';
  }

  showToast('Optimisation suggestions generated.');
});

document.getElementById('createIndexBtn').addEventListener('click', () => {
  document.getElementById('modalIndexSql').textContent = lastReport.index_suggestion_sql;
});

document.getElementById('confirmCreateIndexBtn').addEventListener('click', async () => {
  if (!lastReport || !lastReport.index_suggestion_sql) return;

  const body = await apiCall('/api/create-index', {
    method: 'POST',
    body: JSON.stringify({
      index_sql: lastReport.index_suggestion_sql,
      original_query: lastReport.original_query,
      execution_time_before_ms: lastReport.execution_time_before_ms
    })
  });

  const modalEl = document.getElementById('confirmIndexModal');
  bootstrap.Modal.getInstance(modalEl)?.hide();

  if (!body.success) {
    showToast(body.message || 'Failed to create index.', 'error');
    return;
  }

  showToast('Index created successfully.');
  if (body.data && body.data.execution_time_after_ms !== undefined) {
    document.getElementById('execAfter').textContent = body.data.execution_time_after_ms;
    document.getElementById('improvementPct').textContent = body.data.improvement_percentage + '%';
  }
});
