from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, abort
from database import q, run
from routes.auth import login_required
from services import scheduler, analytics, recommender
bp = Blueprint('main', __name__)
uid = lambda: session['uid']

def valid_date(s):
    try: date.fromisoformat(s); return True
    except (ValueError, TypeError): return False

def regen():
    if q('select 1 from study_schedules where user_id=? limit 1', (uid(),), True): scheduler.generate(uid())

@bp.app_context_processor
def inject():
    u = q('select * from users where id=?', (session['uid'],), True) if 'uid' in session else None
    return dict(user=u, today=date.today().isoformat())

@bp.route('/')
def landing(): return render_template('landing.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    sched = q("select sc.*, s.name from study_schedules sc left join subjects s on s.id=sc.subject_id where sc.user_id=? and sc.date=? order by start", (uid(), date.today().isoformat()))
    return render_template('dashboard.html', st=analytics.stats(uid()), sched=sched, exams=exam_rows()[:3], rec=recommender.recommend(uid())['next'])

# ---- subjects ----
@bp.route('/subjects')
@login_required
def subjects():
    rows = q("select s.*, e.exam_date from subjects s left join exam_details e on e.subject_id=s.id where s.user_id=? order by s.name", (uid(),))
    edit = q('select s.*, e.exam_date from subjects s left join exam_details e on e.subject_id=s.id where s.id=? and s.user_id=?', (request.args.get('edit'), uid()), True) if request.args.get('edit') else None
    return render_template('subjects.html', rows=rows, edit=edit)

@bp.route('/subjects/save', methods=['POST'])
@login_required
def subject_save():
    f = request.form; name = f.get('name', '').strip(); sid = f.get('id')
    try: comp = int(f.get('completion', 0)); pr = int(f.get('priority', 2))
    except ValueError: comp, pr = -1, 0
    if not name or f.get('difficulty') not in ('Easy', 'Medium', 'Hard') or not 0 <= comp <= 100 or pr not in (1, 2, 3) or (f.get('exam_date') and not valid_date(f['exam_date'])):
        flash('Please check the form: name, difficulty, priority (1-3), completion (0-100) and date must be valid.', 'danger'); return redirect(url_for('main.subjects'))
    if sid:
        if not q('select 1 from subjects where id=? and user_id=?', (sid, uid()), True): abort(404)
        run('update subjects set name=?,difficulty=?,priority=?,completion=? where id=?', (name, f['difficulty'], pr, comp, sid))
    else:
        sid = run('insert into subjects(user_id,name,difficulty,priority,completion) values(?,?,?,?,?)', (uid(), name, f['difficulty'], pr, comp))
    run('delete from exam_details where subject_id=?', (sid,))
    if f.get('exam_date'): run('insert into exam_details(user_id,subject_id,exam_date) values(?,?,?)', (uid(), sid, f['exam_date']))
    regen(); flash('Subject saved.', 'success'); return redirect(url_for('main.subjects'))

@bp.route('/subjects/<int:i>/delete', methods=['POST'])
@login_required
def subject_delete(i):
    run('delete from subjects where id=? and user_id=?', (i, uid())); regen(); flash('Subject deleted.', 'info'); return redirect(url_for('main.subjects'))

# ---- tasks ----
@bp.route('/tasks')
@login_required
def tasks():
    flt = request.args.get('f', 'all'); cond = {'pending': 'and t.completed=0', 'done': 'and t.completed=1'}.get(flt, '')
    rows = q(f"select t.*, s.name sname from study_tasks t left join subjects s on s.id=t.subject_id where t.user_id=? {cond} order by t.completed, t.deadline", (uid(),))
    edit = q('select * from study_tasks where id=? and user_id=?', (request.args.get('edit'), uid()), True) if request.args.get('edit') else None
    return render_template('tasks.html', rows=rows, edit=edit, flt=flt, subs=q('select * from subjects where user_id=?', (uid(),)))

@bp.route('/tasks/save', methods=['POST'])
@login_required
def task_save():
    f = request.form; title = f.get('title', '').strip(); sub = f.get('subject_id') or None; dl = f.get('deadline') or None
    if not title or (dl and not valid_date(dl)) or (sub and not q('select 1 from subjects where id=? and user_id=?', (sub, uid()), True)):
        flash('Task needs a title, a valid deadline and one of your subjects.', 'danger'); return redirect(url_for('main.tasks'))
    if f.get('id'):
        run('update study_tasks set title=?,subject_id=?,deadline=? where id=? and user_id=?', (title, sub, dl, f['id'], uid()))
    else: run('insert into study_tasks(user_id,subject_id,title,deadline) values(?,?,?,?)', (uid(), sub, title, dl))
    flash('Task saved.', 'success'); return redirect(url_for('main.tasks'))

@bp.route('/tasks/<int:i>/toggle', methods=['POST'])
@login_required
def task_toggle(i):
    run('update study_tasks set completed=1-completed where id=? and user_id=?', (i, uid())); return redirect(request.referrer or url_for('main.tasks'))

@bp.route('/tasks/<int:i>/delete', methods=['POST'])
@login_required
def task_delete(i):
    run('delete from study_tasks where id=? and user_id=?', (i, uid())); return redirect(url_for('main.tasks'))

# ---- planner ----
@bp.route('/planner', methods=['GET', 'POST'])
@login_required
def planner():
    if request.method == 'POST':
        f = request.form
        try:
            h, b = float(f['daily_hours']), int(f['break_min']); ok = 0.5 <= h <= 16 and 0 <= b <= 60 and len(f['pref_start']) == 5
        except (ValueError, KeyError): ok = False
        if not ok: flash('Hours must be 0.5-16, break 0-60 minutes, and start time valid.', 'danger')
        elif not q('select 1 from subjects where user_id=?', (uid(),), True): flash('Add at least one subject first.', 'warning')
        else:
            run('update users set daily_hours=?,pref_start=?,break_min=? where id=?', (h, f['pref_start'], b, uid()))
            n = scheduler.generate(uid()); flash(f'Timetable generated with {n} study blocks.', 'success')
        return redirect(url_for('main.planner'))
    rows = q("select sc.*, s.name from study_schedules sc left join subjects s on s.id=sc.subject_id where sc.user_id=? and sc.date>=? order by date, start", (uid(), date.today().isoformat()))
    days = {}
    for r in rows: days.setdefault(r['date'], []).append(r)
    return render_template('planner.html', days=days)

# ---- insights / exams / analytics / pomodoro ----
@bp.route('/insights')
@login_required
def insights(): return render_template('insights.html', r=recommender.recommend(uid()))

def exam_rows():
    out = []
    for e in q("select e.exam_date, s.* from exam_details e join subjects s on s.id=e.subject_id where e.user_id=? and e.exam_date>=? order by e.exam_date", (uid(), date.today().isoformat())):
        tk = q("select title, deadline from study_tasks where subject_id=? and completed=0 and (deadline is null or deadline<=?)", (e['id'], e['exam_date']))
        out.append(dict(e, days=(date.fromisoformat(e['exam_date']) - date.today()).days, tasks=tk))
    return out

@bp.route('/exams')
@login_required
def exams(): return render_template('exams.html', exams=exam_rows())

@bp.route('/analytics')
@login_required
def analytics_page(): return render_template('analytics.html', c=analytics.charts(uid()))

@bp.route('/api/analytics')
@login_required
def api_analytics(): return jsonify(analytics.charts(uid()))

@bp.route('/pomodoro')
@login_required
def pomodoro():
    rows = q("select ss.*, s.name from study_sessions ss left join subjects s on s.id=ss.subject_id where ss.user_id=? and ss.date=?", (uid(), date.today().isoformat()))
    return render_template('pomodoro.html', subs=q('select * from subjects where user_id=?', (uid(),)), rows=rows)

@bp.route('/api/session', methods=['POST'])
@login_required
def api_session():
    d = request.get_json(silent=True) or {}; sub = d.get('subject_id') or None
    if sub and not q('select 1 from subjects where id=? and user_id=?', (sub, uid()), True): return jsonify(error='Invalid subject'), 400
    if not isinstance(d.get('minutes'), int) or not 1 <= d['minutes'] <= 180: return jsonify(error='Invalid minutes'), 400
    run("insert into study_sessions(user_id,subject_id,date,minutes,kind) values(?,?,?,?,'focus')", (uid(), sub, date.today().isoformat(), d['minutes']))
    return jsonify(ok=True)
