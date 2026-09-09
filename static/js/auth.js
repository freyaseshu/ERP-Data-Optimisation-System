document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;
  const errorBox = document.getElementById('loginError');
  const btn = document.getElementById('loginBtn');
  const btnText = document.getElementById('loginBtnText');

  errorBox.classList.add('d-none');
  btn.disabled = true;
  btnText.textContent = 'Signing in...';

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const body = await res.json();
    if (body.success) {
      window.location.href = '/dashboard';
    } else {
      errorBox.textContent = body.message || 'Login failed.';
      errorBox.classList.remove('d-none');
    }
  } catch (err) {
    errorBox.textContent = 'Could not reach the server. Please try again.';
    errorBox.classList.remove('d-none');
  } finally {
    btn.disabled = false;
    btnText.textContent = 'Sign In';
  }
});
