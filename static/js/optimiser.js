document.getElementById('optimiseBtn').onclick=async event=>{
  event.target.disabled=true;
  try{
    const query=document.getElementById('sqlQuery').value;
    const data=await apiCall('/api/optimise-query',{method:'POST',body:JSON.stringify({query})});
    if(!data.success){showToast(data.error,'error');return;}
    document.getElementById('originalSql').textContent=data.original_query;
    document.getElementById('proposedSql').textContent=data.proposed_query || 'No automatic rewrite. Review the candidate indexes below.';
    document.getElementById('timeBefore').textContent=data.execution_time_before+' ms (actual PostgreSQL execution)';
    await loadRecommendations();
    const area=document.getElementById('suggestions');area.replaceChildren();
    for(const s of data.suggestions){
      const p=document.createElement('p');p.textContent=s.description;area.append(p);
    }
    if(!data.suggestions.length)area.textContent='No new heuristic recommendations. Existing indexes may already cover this query.';
  }finally{event.target.disabled=false;}
};
async function loadRecommendations(){
  const data=await apiCall('/api/recommendations');if(!data.success){showToast(data.error,'error');return;}
  const area=document.getElementById('recommendations');area.replaceChildren();
  for(const r of data.recommendations){
    const card=document.createElement('div');card.className='border rounded p-3 mb-3';
    const heading=document.createElement('strong');heading.textContent=r.title+' · '+r.status;card.append(heading);
    const query=document.createElement('pre');query.textContent=r.query_text;card.append(query);
    const sql=document.createElement('pre');sql.textContent=r.sql_statement;card.append(sql);
    const description=document.createElement('p');description.textContent=r.description;card.append(description);
    if(r.status==='Pending' && document.body.dataset.role==='Admin'){
      for(const action of ['Apply and benchmark','Reject']){
        const button=document.createElement('button');button.className='btn btn-sm btn-outline-primary me-2';button.textContent=action;
        button.onclick=async()=>{
          if(action==='Apply and benchmark' && !await confirmAction('Create this index and measure the original query?\n'+r.sql_statement))return;
          button.disabled=true;
          const result=await apiCall(action==='Reject'?`/api/recommendations/${r.id}/reject`:'/api/apply-optimization',{method:'POST',body:JSON.stringify({recommendation_id:r.id,confirm:true})});
          if(!result.success)showToast(result.error,'error');else{showToast(action==='Reject'?'Recommendation rejected.':`Baseline ${result.time_before.toFixed(3)} ms; after ${result.time_after.toFixed(3)} ms; gain ${result.improvement?.toFixed(2)??'unavailable'}%. Results equivalent: ${result.equivalent}. ${result.note}`);}
          await loadRecommendations();
        };card.append(button);
      }
    }
    area.append(card);
  }
  if(!data.recommendations.length)area.textContent='No recommendations recorded yet.';
}
loadRecommendations();
