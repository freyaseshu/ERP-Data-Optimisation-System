const queryInput = document.getElementById('sqlQuery');
document.getElementById('predefinedQuery').onchange = event => { if(event.target.value) queryInput.value = event.target.value; };
async function analyse(actual) {
  const button = document.getElementById(actual ? 'actualBtn' : 'analyseBtn'); button.disabled=true;
  try {
    const data = await apiCall('/api/analyse-query',{method:'POST',body:JSON.stringify({query:queryInput.value,run_analyze:actual})});
    if(!data.success){showToast(data.error,'error'); return;}
    document.getElementById('resultsArea').hidden=false;
    document.getElementById('analysisSummary').textContent = actual ? `Actual execution: ${data.execution_time_ms} ms · Planning: ${data.planning_time_ms} ms · Rows returned by plan: ${data.returned_rows}` : 'Estimated plan: costs are planner units, not milliseconds. No actual execution measurement.';
    document.getElementById('warningsContainer').textContent = data.warnings.join(' ') || 'No heuristic warnings. A sequential scan can be appropriate for small tables and broad filters.';
    const body=document.getElementById('planBody'); body.replaceChildren();
    for(const row of data.plan){
      const tr=document.createElement('tr');
      for(const v of ['  '.repeat(row.depth)+row.node_type,row.table,row.estimated_rows,row.actual_rows,row.total_cost,row.actual_time_ms,row.index,row.filter]){
        const td=document.createElement('td'); td.textContent=v??'—';tr.append(td);
      }body.append(tr);
    }
    document.getElementById('rawPlan').textContent=JSON.stringify(data.raw_plan,null,2);
  }finally{button.disabled=false;}
}
document.getElementById('analyseBtn').onclick=()=>analyse(false);
document.getElementById('actualBtn').onclick=()=>analyse(true);
document.getElementById('executeBtn').onclick=async event=>{
  event.target.disabled=true;
  try{
    const data=await apiCall('/api/execute-query',{method:'POST',body:JSON.stringify({query:queryInput.value})});
    if(!data.success){showToast(data.error,'error');return;}
    document.getElementById('queryResults').textContent=JSON.stringify(data,null,2);
  }finally{event.target.disabled=false;}
};
