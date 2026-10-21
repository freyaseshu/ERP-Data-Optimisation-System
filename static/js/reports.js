const reportRangeSelect = document.getElementById('reportRangeSelect');
const customRangeInputs = document.getElementById('customRangeInputs');

reportRangeSelect.addEventListener('change', () => {
  customRangeInputs.classList.toggle('d-none', reportRangeSelect.value !== 'custom');
});

function renderQueryTable(elId, rows) {
  const tbody = document.querySelector(`#${elId} tbody`);
  tbody.innerHTML = '';
  if (!rows || rows.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No data yet.</td></tr>';
    return;
  }
  rows.forEach(r => {
    const tr = document.createElement('tr');
    const shortQuery = (r.query_text || '').length > 60 ? r.query_text.slice(0, 60) + '...' : r.query_text;
    tr.innerHTML = `
      <td><code class="small">${escapeHtml(shortQuery)}</code></td>
      <td>${r.execution_time_before ?? '-'}</td>
      <td>${r.execution_time_after ?? '-'}</td>
      <td>${r.improvement_percentage ?? '-'}%</td>`;
    tbody.appendChild(tr);
  });
}

async function loadReport() {
  const range = reportRangeSelect.value;
  let url = `/api/reports/performance?range=${range}`;
  if (range === 'custom') {
    const start = document.getElementById('reportStartDate').value;
    const end = document.getElementById('reportEndDate').value;
    if (start) url += `&start=${start}`;
    if (end) url += `&end=${end}`;
  }

  const body = await apiCall(url);
  if (!body.success) {
    showToast(body.error || body.message || 'Failed to load report.', 'error');
    return;
  }
  const d = body.data;
  document.getElementById('repAvgTime').textContent = d.average_execution_time_ms ?? '—';
  document.getElementById('repOptimized').textContent = d.queries_optimized;
  document.getElementById('repImprovement').textContent = (d.average_improvement_percentage ?? '—') + '%';
  document.getElementById('repIndexes').textContent = d.indexes_suggested;
  document.getElementById('repDuplicates').textContent = d.duplicate_records_found;
  document.getElementById('repArchived').textContent = d.records_archived;

  renderQueryTable('slowestTable', d.slowest_queries);
  renderQueryTable('fastestTable', d.fastest_queries);
  renderTrend(d.all_logs);
}

document.getElementById('loadReportBtn').addEventListener('click', loadReport);
document.getElementById('exportCsvBtn').addEventListener('click', () => {
  const range = reportRangeSelect.value;
  const params=new URLSearchParams({range,start:document.getElementById('reportStartDate').value,end:document.getElementById('reportEndDate').value});
  window.location.href = '/api/reports/export?'+params;
});

let trendChart;
loadReport();
function renderTrend(logs){
  if(typeof Chart==='undefined')return;
  const rows=logs.filter(r=>r.execution_time_before!==null).slice(0,100).reverse();
  trendChart?.destroy();
  trendChart=new Chart(document.getElementById('queryTrend'),{type:'line',data:{labels:rows.map(r=>r.created_at+' UTC'),datasets:[{label:'Recorded baseline execution (ms)',data:rows.map(r=>r.execution_time_before),borderColor:'#4e73df',tension:.1},{label:'Recorded after execution (ms)',data:rows.map(r=>r.execution_time_after),borderColor:'#1cc88a',tension:.1}]},options:{maintainAspectRatio:false,scales:{y:{beginAtZero:true}}}});
}
