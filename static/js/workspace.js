const workspaceArea = document.getElementById('workspaceRun');
const workspaceStatus = document.getElementById('workspaceStatus');
const workspaceHistory = document.getElementById('runHistory');
let activeRun = null;
let workspaceBusy = false;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function evidenceDetails(title, value) {
  const details = element('details');
  details.append(element('summary', title), element('pre', JSON.stringify(value, null, 2)));
  return details;
}
function number(value) { return typeof value === 'number' ? value.toFixed(3) : 'Unavailable'; }
function metricTable(headers, rows) {
  const wrapper = element('div', undefined, 'table-responsive');
  const table = element('table', undefined, 'table table-sm workspace-metric');
  const head = element('tr');
  for (const label of headers) head.append(element('th', label));
  const thead = element('thead'); thead.append(head); table.append(thead);
  const body = element('tbody');
  for (const values of rows) { const row = element('tr'); for (const value of values) row.append(element('td', value)); body.append(row); }
  table.append(body); wrapper.append(table); return wrapper;
}
function busy(value, message='') {
  workspaceBusy = value;
  document.querySelectorAll('#workspaceForm button, #workspaceRun button, #runHistory').forEach(button => button.disabled = value);
  workspaceStatus.textContent = message;
  workspaceStatus.className = message ? 'alert alert-info' : '';
}
async function refreshHistory() {
  const data = await apiCall('/api/workspace/runs');
  if (!data.success) { showToast(data.error, 'error'); return; }
  workspaceHistory.replaceChildren(element('option', 'Choose an assessment'));
  workspaceHistory.options[0].value = '';
  for (const run of data.runs) {
    const option = element('option', `#${run.id} · ${run.profile} · ${run.created_at} UTC · ${run.created_by}`);
    option.value = run.id; workspaceHistory.append(option);
  }
  if (activeRun) workspaceHistory.value = activeRun.id;
}
async function loadRun(id) {
  const data = await apiCall(`/api/workspace/runs/${id}`);
  if (!data.success) { showToast(data.error, 'error'); return; }
  activeRun = data.run; renderRun();
}
function renderRun() {
  workspaceArea.replaceChildren();
  const run = activeRun;
  const done = run.actions.filter(a => ['Applied', 'Verified', 'Rejected'].includes(a.status)).length;
  workspaceArea.append(element('h2', `Assessment #${run.id} · ${done} / ${run.actions.length} actions reviewed`, 'h4'));
  workspaceArea.append(element('p', `${run.assessment.profile_description}. Created by ${run.created_by} · ${run.created_at} UTC.`));
  const diagnostics = element('div', undefined, 'workspace-panel mb-4');
  diagnostics.append(element('h3', 'Execution plan evidence', 'h5'));
  diagnostics.append(evidenceDetails('Saved workload controls for this assessment', run.configuration));
  for (const query of run.assessment.queries) {
    const details = element('details'); details.append(element('summary', `${query.name} · ${number(query.execution_time_ms)} ms · ${query.returned_rows} rows`));
    details.append(element('pre', query.sql));
    for (const warning of query.warnings) details.append(element('p', warning, 'text-warning'));
    details.append(metricTable(['Plan node', 'Table / index', 'Estimated rows', 'Actual rows', 'Time (ms)'], query.plan.map(node => [
      '  '.repeat(node.depth) + node.node_type, [node.table, node.index].filter(Boolean).join(' / '), node.estimated_rows ?? '', node.actual_rows ?? '', number(node.actual_time_ms)])));
    details.append(evidenceDetails('Full EXPLAIN ANALYZE and buffer evidence', query.raw_plan)); diagnostics.append(details);
  }
  diagnostics.append(evidenceDetails('Dataset, database activity, existing indexes and environment', run.assessment));
  workspaceArea.append(diagnostics);
  for (const action of run.actions) {
    const panel = element('article', undefined, 'workspace-panel workspace-action mb-3'); panel.dataset.status = action.status;
    const top = element('div', undefined, 'd-flex justify-content-between align-items-center gap-3');
    top.append(element('h3', `${action.kind} / ${action.title}`, 'mb-0'), element('span', action.status, 'badge')); panel.append(top);
    panel.append(element('p', action.scope, 'workspace-scope mt-2'));
    const description = element('dl');
    for (const [label, value] of [['Reason and evidence', action.rationale], ['Trade-offs', action.risks]]) description.append(element('dt', label), element('dd', value));
    panel.append(description, element('pre', action.sql));
    if (action.error) panel.append(element('p', action.error, 'alert alert-danger'));
    if (action.result) {
      const result = action.result;
      if ('baseline_time_ms' in result) {
        panel.append(metricTable(['Before (ms)', 'After (ms)', 'Change (%)', 'Results equivalent'], [[number(result.baseline_time_ms), number(result.optimised_time_ms), number(result.improvement_percentage), String(result.equivalent)]]));
        panel.append(element('p', 'Positive percentages indicate lower read time; negative percentages are regressions. Check samples and variation before drawing conclusions.', 'small text-muted'));
      }
      if (result.baseline?.metrics) {
        const rows = [];
        for (const [kind, before] of Object.entries(result.baseline.metrics)) {
          const after = result.after.metrics[kind];
          rows.push([kind, before.count, number(before.mean_ms), number(after.mean_ms), number(before.p95_ms), number(after.p95_ms)]);
        }
        panel.append(metricTable(['Operation', 'Count / phase', 'Before mean (ms)', 'After mean (ms)', 'Before p95 (ms)', 'After p95 (ms)'], rows));
        panel.append(element('p', `Throughput: ${number(result.baseline.throughput_ops_per_second)} → ${number(result.after.throughput_ops_per_second)} operations/s. Copies unchanged: ${result.equivalent}. Sandbox removed: ${result.sandbox_removed}.`, 'small'));
      }
      if ('records_archived' in result) panel.append(element('p', `${result.records_archived} new order snapshots verified. Live orders unchanged: ${result.live_orders_unchanged}.`));
      if ('partitions' in result) panel.append(element('p', `${result.partitions} partitions; report scans ${result.partitions_scanned.length}. Full copied dataset equivalent: ${result.full_copy_equivalent}.`));
      if (result.note) panel.append(element('p', result.note, 'small text-muted'));
      panel.append(evidenceDetails('Verification evidence, samples and plans', result));
    }
    if (document.body.dataset.role === 'Admin' && ['Pending', 'Failed'].includes(action.status)) {
      for (const [decision, label] of [['approve', 'Review & approve'], ['reject', 'Reject']]) {
        const button = element('button', label, decision === 'approve' ? 'btn btn-primary me-2' : 'btn btn-outline-secondary'); button.type = 'button';
        button.onclick = () => decideAction(action, decision); button.disabled = workspaceBusy; panel.append(button);
      }
    } else if (action.status === 'Pending') panel.append(element('p', 'An administrator must approve this action.', 'small text-muted'));
    if (action.decisions.length) panel.append(evidenceDetails('Administrator decision history (UTC)', action.decisions));
    workspaceArea.append(panel);
  }
  const download = document.getElementById('exportRun'); download.hidden = false; download.href = `/api/workspace/runs/${run.id}/export`;
}
async function decideAction(action, decision) {
  if (workspaceBusy) return;
  if (decision === 'approve' && !await confirmAction(`${action.title}\n\n${action.scope}\n\n${action.sql}\n\n${action.risks}\n\nApprove this operation and record verification evidence?`)) return;
  busy(true, decision === 'approve' ? 'Running the approved action and verifying results. Keep this page open.' : 'Recording rejection…');
  try {
    const result = await apiCall(`/api/workspace/runs/${activeRun.id}/actions/${action.id}`, {method:'POST', body:JSON.stringify({decision, confirm:true})});
    if (!result.success) showToast(result.error, 'error');
    await loadRun(activeRun.id); await refreshHistory();
  } finally { busy(false); }
}
document.getElementById('workspaceForm').onsubmit = async event => {
  event.preventDefault(); if (workspaceBusy) return;
  const config = Object.fromEntries(new FormData(event.target));
  for (const key of ['workers', 'writers', 'operations', 'iterations', 'seed']) config[key] = Number(config[key]);
  busy(true, 'Collecting actual ERP plans, database activity and a reviewable action list…');
  try {
    const result = await apiCall('/api/workspace/runs', {method:'POST', body:JSON.stringify(config)});
    if (!result.success) { showToast(result.error, 'error'); return; }
    activeRun = result.run; renderRun(); await refreshHistory();
  } finally { busy(false); }
};
workspaceHistory.onchange = async () => { if (!workspaceHistory.value || workspaceBusy) return; busy(true, 'Loading assessment…'); try { await loadRun(workspaceHistory.value); } finally { busy(false); } };
refreshHistory();
