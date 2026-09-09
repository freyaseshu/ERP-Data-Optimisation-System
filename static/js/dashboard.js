async function loadDashboard() {
  const body = await apiCall('/api/dashboard');
  if (!body.success) {
    showToast(body.message || 'Failed to load dashboard.', 'error');
    return;
  }
  const s = body.data;
  document.getElementById('statCustomers').textContent = s.total_customers ?? 0;
  document.getElementById('statProducts').textContent = s.total_products ?? 0;
  document.getElementById('statOrders').textContent = s.total_orders ?? 0;
  document.getElementById('statInventory').textContent = s.total_inventory_items ?? 0;
  document.getElementById('statAvgTime').textContent = s.avg_query_execution_time_ms ?? 0;
  document.getElementById('statSlowQueries').textContent = s.slow_queries_detected ?? 0;
  document.getElementById('statDuplicates').textContent = s.duplicate_records_detected ?? 0;
  document.getElementById('statArchived').textContent = s.archived_records ?? 0;

  renderDashboardCharts(s);
}

loadDashboard();
