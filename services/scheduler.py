"""Smart timetable generator: weighted greedy allocation of study blocks."""
from datetime import date, datetime, timedelta
from database import q, run
DIFF = {'Easy': 1, 'Medium': 2, 'Hard': 3}
BLOCK = 50  # minutes per study block

def weight(s, day):
    w = DIFF.get(s['difficulty'], 2) * s['priority'] * (1.2 - s['completion'] / 100)
    if s['exam_date']:
        left = max((date.fromisoformat(s['exam_date']) - day).days, 1)
        w *= 1 + 14 / left          # approaching exams get more time
    return w

def generate(uid, days=7):
    u = q("select * from users where id=?", (uid,), True)
    subs = q("select s.*, e.exam_date from subjects s left join exam_details e on e.subject_id=s.id where s.user_id=?", (uid,))
    today = date.today()
    run("delete from study_schedules where user_id=? and date>=?", (uid, today.isoformat()))
    brk = u['break_min']; n = max(1, int(u['daily_hours'] * 60 // (BLOCK + brk))); count = 0
    for d in range(days):
        day = today + timedelta(days=d)
        active = [s for s in subs if s['completion'] < 100 and (not s['exam_date'] or date.fromisoformat(s['exam_date']) >= day)]
        if not active: continue
        w = {s['id']: weight(s, day) for s in active}; used = {s['id']: 0 for s in active}; order = []
        for _ in range(n):
            cands = [i for i in w if not (order and i == order[-1] and len(w) > 1)]
            pick = max(cands, key=lambda i: w[i] / (used[i] + 1)); used[pick] += 1; order.append(pick)
        t = datetime.combine(day, datetime.strptime(u['pref_start'], '%H:%M').time())
        for k, sid in enumerate(order):
            e = t + timedelta(minutes=BLOCK)
            run("insert into study_schedules(user_id,subject_id,date,start,end,kind) values(?,?,?,?,?,'study')",
                (uid, sid, day.isoformat(), t.strftime('%H:%M'), e.strftime('%H:%M'))); count += 1
            t = e
            if brk and k < len(order) - 1:
                e = t + timedelta(minutes=brk)
                run("insert into study_schedules(user_id,subject_id,date,start,end,kind) values(?,?,?,?,?,'break')",
                    (uid, None, day.isoformat(), t.strftime('%H:%M'), e.strftime('%H:%M'))); t = e
    return count
