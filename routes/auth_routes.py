from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash
from models.user import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username', '')).first()
        if user and check_password_hash(user.password, request.form.get('password', '')):
            session.clear()
            session.update(user_id=user.id, username=user.username, role=user.role)
            return redirect(url_for('dashboard.index'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
