import db
period = db.get_latest_feedback_period()
print("Latest period:", period)

summary = db.get_feedback_summary()
for r in summary:
    print(r)
