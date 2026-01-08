# 🎯 Quick Start: Adding Goal Tracking

I've created a basic goal tracking system for you! Here's how to integrate it:

## Step 1: Add Goal Tracker to Database Manager

Add this method to `src/database/db.py`:

```python
def get_goals_for_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
    """Get goals within a date range"""
    # Implementation similar to get_recent_activities
    pass
```

## Step 2: Integrate with ProductivityAgent

In `src/main_app.py`, add:

```python
from utils.goal_tracker import GoalTracker

class ProductivityAgent:
    def __init__(self, use_gui_tracker=False):
        # ... existing code ...
        self.goal_tracker = GoalTracker()
    
    def check_goals(self):
        """Check and update goal progress"""
        active_goals = self.goal_tracker.get_active_goals()
        for goal in active_goals:
            # Get activities for goal period
            activities = self.db.get_recent_activities(limit=100)
            progress = self.goal_tracker.update_goal_progress(goal['id'], activities)
            
            if progress.get('achieved'):
                self.show_notification(
                    "🎉 Goal Achieved!",
                    f"Congratulations! You achieved: {goal['description']}"
                )
```

## Step 3: Add GUI for Goals

In `src/main_modern_gui.py`, add a new tab:

```python
def setup_goals_tab(self):
    """Setup goals management tab"""
    tab = self.tabview.tab("🎯 Goals")
    
    # Goal creation form
    # Goal list with progress bars
    # Goal completion indicators
```

## Example: Create a Goal

```python
from utils.goal_tracker import GoalTracker
from datetime import datetime, timedelta

tracker = GoalTracker()

# Daily productivity goal
tracker.create_goal({
    'goal_type': 'daily',
    'target_score': 75,
    'description': 'Maintain 75% productivity today'
})

# Weekly coding goal
tracker.create_goal({
    'goal_type': 'weekly',
    'target_hours': 25,
    'target_category': 'productive',
    'description': 'Code for 25 hours this week',
    'start_date': datetime.now().date(),
    'end_date': (datetime.now() + timedelta(days=7)).date()
})
```

## Next Steps

1. ✅ Goal tracker created (`src/utils/goal_tracker.py`)
2. ⏳ Integrate with ProductivityAgent
3. ⏳ Add GUI components
4. ⏳ Add progress visualization
5. ⏳ Add achievement notifications

Would you like me to implement the full integration?
