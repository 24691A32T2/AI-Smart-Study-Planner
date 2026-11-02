import re
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import q, run
bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if 'uid' not in session: return redirect(url_for('auth.login'))
        return f(*a, **k)
    return w

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        n, e, p = request.form['name'].strip(), request.form['email'].strip().lower(), request.form['password']
        if len(n) < 2: flash('Name must be at least 2 characters.', 'danger')
        elif not re.match(r'^[^@\s]+@[^@\s]+\.\w+$', e): flash('Enter a valid email.', 'danger')
        elif len(p) < 6: flash('Password must be at least 6 characters.', 'danger')
        elif q('select 1 from users where email=?', (e,), True): flash('Email already registered.', 'danger')
        else:
            session['uid'] = run('insert into users(name,email,password_hash) values(?,?,?)', (n, e, generate_password_hash(p)))
            return redirect(url_for('main.dashboard'))
    return render_template('register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = q('select * from users where email=?', (request.form['email'].strip().lower(),), True)
        if u and check_password_hash(u['password_hash'], request.form['password']):
            session['uid'] = u['id']; return redirect(url_for('main.dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.clear(); return redirect(url_for('main.landing'))
