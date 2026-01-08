import sys
import os
from datetime import datetime, timedelta

# Add src directory to Python path for proper imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from analysis.local_llm_analyzer import LocalLLMAnalyzer
from database.db import DatabaseManager
from notifications import show_notification


def main():
    print("=== Console Productivity Tracker ===")
    db = DatabaseManager()
    analyzer = LocalLLMAnalyzer(model="mistral")

    # Analyze last 3 hours of activity
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=3)

    print(f"Analyzing activity from {start_date} to {end_date}...")
    report = analyzer.generate_report(start_date, end_date)

    if isinstance(report, dict):
        print("\n📊 Productivity Report:")
        print(f"Score: {report.get('score', 'N/A')}")
        print(f"Summary: {report.get('summary', '')}")
        print(f"Strengths: {report.get('strengths', [])}")
        print(f"Improvements: {report.get('improvements', [])}")
        print(f"Recommendations: {report.get('recommendations', [])}")
        print(f"Quote: {report.get('quote', '')}")
        print(f"Reward: {report.get('reward', '')}")

        # Trigger motivational notification
        if report.get("score", 0) < 60:
            show_notification("⚠️ Stay Focused!", report.get("quote", "Keep going!"))
        else:
            show_notification("✅ Great Work!", report.get("quote", "Nice job!"))

    else:
        print("\n🧠 Raw LLM Response:")
        print(report)


if __name__ == "__main__":
    main()
