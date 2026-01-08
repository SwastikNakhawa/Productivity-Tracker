import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Now import your modules
from trackers.windows_tracker import WindowsActivityTracker
import unittest


class TestWindowsTracker(unittest.TestCase):
    def test_classify_activity(self):
        # Mock database for testing
        class MockDB:
            def insert_activity(self, activity):
                return 1

        tracker = WindowsActivityTracker(MockDB())
        window_info = {'app_name': 'code.exe', 'window_title': 'main.py'}
        category, score = tracker.classify_activity(window_info)
        self.assertEqual(category, 'productive')


if __name__ == '__main__':
    unittest.main()