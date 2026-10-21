let performanceChart, optimizationPieChart;
async function loadDashboard() {
  const response = await apiCall('/api/dashboard/stats');
  const status = document.getElementById('connectionStatus');
  if (!response.success) {
    status.className = 'alert alert-danger'; status.textContent = response.error; return;
  }
  const s = response.stats;
  status.className = 'alert alert-' + (s.total_erp_records ? 'success' : 'warning');
  status.textContent = s.status + ' · ' + s.postgresql_version + ' · Refreshed ' + new Date(s.refreshed_at).toLocaleString();
  const values = {statCustomers:s.row_counts.customers, statProducts:s.row_counts.products, statOrders:s.row_counts.orders,
    statInventory:s.row_counts.inventory, statRecords:s.total_erp_records, statTables:s.total_tables, statIndexes:s.total_indexes,
    statSlow:s.slow_queries, statPending:s.recommendations.Pending, statApplied:s.recommendations.Applied};
  for (const [id,value] of Object.entries(values)) document.getElementById(id).textContent = value.toLocaleString();
  document.getElementById('lastMeasurement').textContent = s.last_measurement ? 'Last recorded measurement (UTC): ' + s.last_measurement : 'No measurements yet. Analyse a query or run an approved benchmark.';
  const logs = s.recent_logs.filter(r => r.execution_time_after !== null).slice(0,6).reverse();
  document.getElementById('benchmarkEmpty').hidden = logs.length > 0;
  if (typeof Chart !== 'undefined') {
    performanceChart?.destroy(); optimizationPieChart?.destroy();
    performanceChart = new Chart(document.getElementById('performanceChart'), {type:'bar', data:{labels:logs.map(r=>r.query_name || 'Log '+r.id), datasets:[{label:'Baseline (ms)', data:logs.map(r=>r.execution_time_before), backgroundColor:'#e74a3b'},{label:'After (ms)', data:logs.map(r=>r.execution_time_after), backgroundColor:'#1cc88a'}]}, options:{maintainAspectRatio:false, scales:{y:{beginAtZero:true}}}});
    optimizationPieChart = new Chart(document.getElementById('optimizationPieChart'), {type:'doughnut', data:{labels:Object.keys(s.recommendations), datasets:[{data:Object.values(s.recommendations), backgroundColor:['#4e73df','#1cc88a','#858796','#e74a3b']}]}, options:{maintainAspectRatio:false}});
  }
  const body = document.getElementById('recentQueries'); body.replaceChildren();
  for (const r of s.recent_logs) {
    const tr = document.createElement('tr');
    for (const value of [r.created_at, r.query_text, r.execution_time_before, r.execution_time_after, r.status]) {
      const td = document.createElement('td'); td.textContent = value ?? '—'; tr.append(td);
    }
    body.append(tr);
  }
}
loadDashboard();
document.getElementById('refreshDashboard').onclick = loadDashboard;
setInterval(()=>{if(document.getElementById('autoRefresh').checked)loadDashboard();},30000);
