from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash
from models.user import User
from utils.security import consume_login_attempt, clear_account_throttle

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()[:50]
        password = request.form.get('password', '')
        if not consume_login_attempt(username, request.remote_addr):
            return render_template('login.html', login_error='Too many sign-in attempts. Try again after ten minutes.'), 429, {'Retry-After': '600'}
        user = User.query.filter_by(username=username).first()
        if user and len(password) <= 1024 and check_password_hash(user.password, password):
            clear_account_throttle(username)
            session.clear()
            session.update(user_id=user.id, username=user.username, role=user.role)
            session.permanent = True
            return redirect(url_for('dashboard.index'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
