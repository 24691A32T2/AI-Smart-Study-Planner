import os, sqlite3, random
from datetime import date, timedelta
from flask import g, current_app
from werkzeug.security import generate_password_hash
from models.schema import SCHEMA

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def q(sql, args=(), one=False):
    cur = get_db().execute(sql, args); rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows

def run(sql, args=()):
    db = get_db(); cur = db.execute(sql, args); db.commit(); return cur.lastrowid

def init_db(app):
    os.makedirs(app.instance_path, exist_ok=True)
    with sqlite3.connect(app.config['DATABASE']) as c: c.executescript(SCHEMA)

def seed_demo(app):
    """Creates demo@student.com / demo1234 with realistic sample data."""
    random.seed(7); today = date.today()
    c = sqlite3.connect(app.config['DATABASE']); c.execute('PRAGMA foreign_keys=ON')
    if c.execute("select 1 from users where email='demo@student.com'").fetchone():
        print('Demo user already exists.'); return
    uid = c.execute("insert into users(name,email,password_hash,daily_hours,pref_start,break_min) values(?,?,?,?,?,?)",
        ('Demo Student', 'demo@student.com', generate_password_hash('demo1234'), 4, '17:00', 10)).lastrowid
    subs = [('Data Structures','Hard',3,45,12),('Database Systems','Medium',3,60,9),('Machine Learning','Hard',2,30,18),
            ('Operating Systems','Medium',2,70,24),('Technical English','Easy',1,85,30)]
    ids = []
    for n,d,p,comp,days in subs:
        sid = c.execute("insert into subjects(user_id,name,difficulty,priority,completion) values(?,?,?,?,?)",(uid,n,d,p,comp)).lastrowid
        ids.append(sid)
        c.execute("insert into exam_details(user_id,subject_id,exam_date) values(?,?,?)",(uid,sid,(today+timedelta(days=days)).isoformat()))
    tasks = [('Solve 20 tree problems',0,2,0),('Revise normalization',1,4,1),('Finish ML assignment',2,3,0),
             ('Practice scheduling algorithms',3,6,0),('Write essay draft',4,5,1),('Mock test on SQL joins',1,7,0)]
    for t,i,dl,done in tasks:
        c.execute("insert into study_tasks(user_id,subject_id,title,deadline,completed) values(?,?,?,?,?)",
                  (uid,ids[i],t,(today+timedelta(days=dl)).isoformat(),done))
    for back in range(21):
        if random.random() < 0.8:
            for _ in range(random.randint(1,3)):
                c.execute("insert into study_sessions(user_id,subject_id,date,minutes,kind) values(?,?,?,?,'focus')",
                          (uid,random.choice(ids),(today-timedelta(days=back)).isoformat(),25*random.randint(1,2)))
    c.commit(); c.close(); print('Demo data created: demo@student.com / demo1234')
