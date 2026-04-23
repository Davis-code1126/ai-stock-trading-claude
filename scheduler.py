import schedule
import time
from analyzer import run_daily_analysis

def job():
    print("Scheduled job starting...")
    run_daily_analysis()

# Run every day at 6:00 AM Pacific Time (before market open)
schedule.every().day.at("06:00").do(job)

# Run every day at 1:30 PM Pacific Time (after market close)
schedule.every().day.at("13:30").do(job)

print("Scheduler started. Running automatically at 06:00 and 13:30 daily...")
print("Keep this window open. Press Ctrl+C to stop.")

while True:
    schedule.run_pending()
    time.sleep(60)