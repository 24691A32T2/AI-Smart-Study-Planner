from datetime import date, timedelta
import numpy as np, pandas as pd
from database import q

def stats(uid):
    subs = q("select * from subjects where user_id=?", (uid,))
    t = q("select completed from study_tasks where user_id=?", (uid,))
    done = sum(r['completed'] for r in t); pend = len(t) - done
    mins = q("select coalesce(sum(minutes),0) m from study_sessions where user_id=? and kind='focus'", (uid,), True)['m']
    syl = float(np.mean([s['completion'] for s in subs])) if subs else 0.0
    prog = syl if not t else 0.5 * syl + 0.5 * (100 * done / len(t))
    return dict(subjects=len(subs), hours=round(mins / 60, 1), done=done, pending=pend, progress=round(prog))

def charts(uid):
    today = date.today()
    rows = q("select date, minutes, subject_id from study_sessions where user_id=? and kind='focus'", (uid,))
    df = pd.DataFrame([dict(r) for r in rows], columns=['date', 'minutes', 'subject_id'])
    daily = df.groupby('date')['minutes'].sum() / 60 if len(df) else pd.Series(dtype=float)
    d7 = [(today - timedelta(d)).isoformat() for d in range(6, -1, -1)]
    d30 = [(today - timedelta(d)).isoformat() for d in range(29, -1, -1)]
    weeks = []
    for w in range(3, -1, -1):
        days = [(today - timedelta(w * 7 + d)).isoformat() for d in range(7)]
        weeks.append(round(float(daily.reindex(days).fillna(0).sum()), 1))
    subs = q("select name, completion from subjects where user_id=?", (uid,))
    s = stats(uid); studied = [1 if daily.get(x, 0) > 0 else 0 for x in d30]
    streak = 0
    for v in reversed(studied):
        if v: streak += 1
        else: break
    return dict(daily=dict(labels=d7, data=[round(float(daily.get(x, 0)), 2) for x in d7]),
        weekly=dict(labels=['3 wks ago', '2 wks ago', 'Last wk', 'This wk'], data=weeks),
        subjects=dict(labels=[r['name'] for r in subs], data=[r['completion'] for r in subs]),
        tasks=dict(labels=['Completed', 'Pending'], data=[s['done'], s['pending']]),
        consistency=dict(labels=d30, data=studied), streak=streak, consistency_pct=round(100 * sum(studied) / 30))
