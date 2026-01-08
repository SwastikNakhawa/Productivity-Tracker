# check_database.py
import sqlite3
import os
from datetime import datetime


def check_database():
    db_path = "productivity_tracker.db"

    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return

    print(f"✅ Database found: {db_path}")
    print(f"📊 File size: {os.path.getsize(db_path)} bytes")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"📋 Tables in database: {[table[0] for table in tables]}")

        # Check activities count
        cursor.execute("SELECT COUNT(*) FROM activities;")
        activity_count = cursor.fetchone()[0]
        print(f"📝 Total activities logged: {activity_count}")

        # Show recent activities
        if activity_count > 0:
            cursor.execute(
                "SELECT app_name, category, productivity_score, start_time FROM activities ORDER BY start_time DESC LIMIT 5;")
            recent_activities = cursor.fetchall()
            print("🕒 Recent activities:")
            for activity in recent_activities:
                print(f"   - {activity[0]} ({activity[1]}) - Score: {activity[2]} - {activity[3]}")

        # Check LLM interactions
        cursor.execute("SELECT COUNT(*) FROM llm_learning_data;")
        llm_count = cursor.fetchone()[0]
        print(f"🤖 LLM interactions logged: {llm_count}")

        conn.close()

    except Exception as e:
        print(f"❌ Error checking database: {e}")


if __name__ == "__main__":
    check_database()