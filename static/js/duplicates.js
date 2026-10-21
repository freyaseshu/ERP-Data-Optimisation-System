const tableSelect = document.getElementById('tableSelect');
const checkDuplicatesBtn = document.getElementById('checkDuplicatesBtn');
const dupSpinner = document.getElementById('dupSpinner');
let pendingDelete = null;

function renderDuplicates(data) {
  document.getElementById('dupEmptyState').classList.add('d-none');
  document.getElementById('dupResults').classList.remove('d-none');
  document.getElementById('dupGroupsBadge').textContent = `${data.total_groups} duplicate groups`;
  document.getElementById('dupRecordsBadge').textContent = `${data.total_duplicate_records} duplicate records`;

  const tbody = document.querySelector('#dupTable tbody');
  tbody.innerHTML = '';

  if (data.duplicate_groups.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No duplicates found.</td></tr>';
    return;
  }

  data.duplicate_groups.forEach((g, idx) => {
    const valueStr = Object.entries(g.group_values).map(([k, v]) => `${k}: ${v}`).join(', ');
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(valueStr)}</td>
      <td><span class="badge bg-danger">${g.duplicate_count}</span></td>
      <td><small>${g.record_ids.join(', ')}</small></td>
      <td><small>${escapeHtml(g.suggested_action)}</small></td>
      <td>
        <button class="btn btn-sm btn-outline-secondary view-btn" data-idx="${idx}">
          <i class="bi bi-eye"></i> View
        </button>
        <button ${document.body.dataset.role !== 'Admin' ? 'disabled' : ''} class="btn btn-sm btn-outline-danger delete-btn" data-idx="${idx}">
          <i class="bi bi-trash"></i> Delete
        </button>
      </td>`;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll('.view-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const g = data.duplicate_groups[btn.dataset.idx];
      showToast(`Record IDs: ${g.record_ids.join(', ')}`, 'warning');
    });
  });

  tbody.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const g = data.duplicate_groups[btn.dataset.idx];
      const keepId = Math.min(...g.record_ids);
      const deleteIds = g.record_ids.filter(id => id !== keepId);
      pendingDelete = { table: tableSelect.value, keepId, deleteIds };
      document.getElementById('deleteCountText').textContent = deleteIds.length;
      document.getElementById('keepIdText').textContent = keepId;
      new bootstrap.Modal(document.getElementById('confirmDeleteModal')).show();
    });
  });
}

checkDuplicatesBtn.addEventListener('click', async () => {
  const table = tableSelect.value;
  dupSpinner.classList.remove('d-none');
  checkDuplicatesBtn.disabled = true;

  const body = await apiCall(`/api/duplicates/${table}`);

  dupSpinner.classList.add('d-none');
  checkDuplicatesBtn.disabled = false;

  if (!body.success) {
    showToast(body.error || body.message || 'Failed to check duplicates.', 'error');
    return;
  }
  renderDuplicates(body.data);
});

document.getElementById('confirmDeleteBtn').addEventListener('click', async () => {
  if (!pendingDelete) return;

  const body = await apiCall('/api/duplicates/delete', {
    method: 'POST',
    body: JSON.stringify({
      table: pendingDelete.table,
      keep_id: pendingDelete.keepId,
      delete_ids: pendingDelete.deleteIds,
      confirm: true
    })
  });

  bootstrap.Modal.getInstance(document.getElementById('confirmDeleteModal'))?.hide();

  if (!body.success) {
    showToast(body.error || body.message || 'Failed to delete duplicates.', 'error');
    return;
  }
  showToast(body.error || body.message || 'Duplicates deleted.');
  checkDuplicatesBtn.click();
});
