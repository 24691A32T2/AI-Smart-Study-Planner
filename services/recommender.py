"""Rule-based recommender (works offline) with an explanation for every suggestion."""
from datetime import date
from database import q
from services.scheduler import DIFF
from services.analytics import charts, stats

def recommend(uid):
    today = date.today(); u = q("select * from users where id=?", (uid,), True)
    subs = q("select s.*, e.exam_date from subjects s left join exam_details e on e.subject_id=s.id where s.user_id=?", (uid,))
    pend = {r['subject_id']: r['n'] for r in q("select subject_id, count(*) n from study_tasks where user_id=? and completed=0 group by subject_id", (uid,))}
    items = []
    for s in subs:
        days = (date.fromisoformat(s['exam_date']) - today).days if s['exam_date'] else None
        score = (100 - s['completion']) * 0.4 + DIFF[s['difficulty']] * 8 + s['priority'] * 6 + pend.get(s['id'], 0) * 3
        why = [f"{s['completion']}% of the syllabus is done", f"{s['difficulty']} difficulty"]
        if days is not None and days >= 0:
            score += 30 * max(0, (14 - days) / 14); why.append(f"exam in {days} day(s)")
        if pend.get(s['id']): why.append(f"{pend[s['id']]} pending task(s)")
        items.append(dict(id=s['id'], name=s['name'], score=round(score), days=days, completion=s['completion'],
                          weak=s['completion'] < 40 or (s['difficulty'] == 'Hard' and s['completion'] < 60), reason=', '.join(why)))
    items.sort(key=lambda x: -x['score'])
    revise = [dict(name=i['name'], text=f"Schedule a revision session for {i['name']}: exam in {i['days']} day(s) with {i['completion']}% covered.")
              for i in items if i['days'] is not None and 0 <= i['days'] <= 10]
    c = charts(uid); st = stats(uid); tips = []
    week = sum(c['daily']['data'])
    if week < u['daily_hours'] * 7 * 0.5: tips.append(f"You studied {week:.1f}h in the last 7 days, under half of your {u['daily_hours'] * 7:.0f}h goal. Try one fixed daily slot.")
    if c['consistency_pct'] < 60: tips.append(f"You studied on {c['consistency_pct']}% of the last 30 days. Short daily sessions beat occasional marathons.")
    if st['pending'] > st['done'] and st['pending']: tips.append(f"{st['pending']} tasks are pending versus {st['done']} done. Clear the oldest deadlines first.")
    if not tips: tips.append("Great consistency. Keep your current routine and add a weekly mock test.")
    return dict(next=items[0] if items else None, ranked=items, weak=[i for i in items if i['weak']], revise=revise, tips=tips,
                target=f"{u['daily_hours']}h today ({int(u['daily_hours'] * 60 // 25)} Pomodoros)")
