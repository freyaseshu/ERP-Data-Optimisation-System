const archiveTableSelect = document.getElementById('archiveTableSelect');
const archiveDateInput = document.getElementById('archiveDateInput');
let previewData = null;

document.getElementById('previewArchiveBtn').addEventListener('click', async () => {
  const table = archiveTableSelect.value;
  const beforeDate = archiveDateInput.value;
  if (!beforeDate) { showToast('Choose a date first.', 'error'); return; }

  const body = await apiCall('/api/archive/preview', {
    method: 'POST',
    body: JSON.stringify({ table, before_date: beforeDate })
  });

  if (!body.success) {
    showToast(body.message || 'Preview failed.', 'error');
    return;
  }

  previewData = { table, before_date: beforeDate };
  document.getElementById('archivePreviewCard').classList.remove('d-none');
  document.getElementById('previewTable').textContent = body.data.table;
  document.getElementById('previewCondition').textContent = body.data.condition;
  document.getElementById('previewCount').textContent = body.data.records_to_archive;
});

document.getElementById('confirmArchiveBtn').addEventListener('click', async () => {
  if (!previewData) return;

  const body = await apiCall('/api/archive/execute', {
    method: 'POST',
    body: JSON.stringify({
      table: previewData.table,
      before_date: previewData.before_date,
      confirm: true
    })
  });

  bootstrap.Modal.getInstance(document.getElementById('confirmArchiveModal'))?.hide();

  if (!body.success) {
    showToast(body.message || 'Archive failed.', 'error');
    return;
  }
  showToast(body.message || 'Records archived.');
  document.getElementById('archivePreviewCard').classList.add('d-none');
});
