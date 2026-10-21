function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
}
function showToast(message, type='success') {
  const container = document.getElementById('messages');
  const item = document.createElement('div');
  item.className = 'alert alert-' + (type === 'error' ? 'danger' : 'success');
  item.textContent = message;
  container.replaceChildren(item);
}
async function apiCall(url, options={}) {
  try {
    const res = await fetch(url, { ...options, headers: {'Content-Type':'application/json', ...(options.headers || {})} });
    const data = await res.json();
    if (!res.ok && !data.error) data.error = data.message || 'Request failed.';
    if (res.status === 401) window.location.assign('/login');
    return data;
  } catch (_) { return {success:false, error:'Unable to reach the server.', message:'Unable to reach the server.'}; }
}

function confirmAction(message){
  return new Promise(resolve=>{
    const element=document.getElementById('actionConfirmation');
    document.getElementById('actionConfirmationMessage').textContent=message;
    const modal=bootstrap.Modal.getOrCreateInstance(element);
    const approve=document.getElementById('actionConfirmationApprove');
    let accepted=false;
    approve.onclick=()=>{accepted=true;modal.hide();};
    element.addEventListener('hidden.bs.modal',()=>{approve.onclick=null;resolve(accepted);},{once:true});
    modal.show();
  });
}
