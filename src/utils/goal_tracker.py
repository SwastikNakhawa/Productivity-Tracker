"""
Goal Tracking System for Productivity Agent
Allows users to set and track productivity goals
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class GoalTracker:
    """Track productivity goals and progress"""
    
    def __init__(self, db_path: str = "productivity_tracker.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_goals_table()
    
    def _init_goals_table(self):
        """Initialize goals table if it doesn't exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS goals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        goal_type TEXT NOT NULL,
                        target_score INTEGER,
                        target_hours REAL,
                        target_category TEXT,
                        description TEXT,
                        start_date DATE NOT NULL,
                        end_date DATE,
                        achieved BOOLEAN DEFAULT FALSE,
                        current_progress REAL DEFAULT 0.0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                self.logger.info("✅ Goals table initialized")
        except Exception as e:
            self.logger.error(f"Error initializing goals table: {e}")
    
    def create_goal(self, goal_data: Dict) -> Optional[int]:
        """Create a new productivity goal"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                query = """
                INSERT INTO goals 
                (goal_type, target_score, target_hours, target_category, description, start_date, end_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(query, (
                    goal_data.get('goal_type'),  # 'daily', 'weekly', 'monthly'
                    goal_data.get('target_score'),  # Target productivity score
                    goal_data.get('target_hours'),  # Target hours
                    goal_data.get('target_category'),  # Specific category
                    goal_data.get('description', ''),
                    goal_data.get('start_date', datetime.now().date()),
                    goal_data.get('end_date')
                ))
                goal_id = cursor.lastrowid
                conn.commit()
                self.logger.info(f"✅ Created goal: {goal_data.get('description', 'No description')}")
                return goal_id
        except Exception as e:
            self.logger.error(f"Error creating goal: {e}")
            return None
    
    def get_active_goals(self, goal_type: str = None) -> List[Dict]:
        """Get all active (not achieved) goals"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if goal_type:
                    query = """
                    SELECT * FROM goals 
                    WHERE achieved = FALSE AND (end_date IS NULL OR end_date >= date('now'))
                    AND goal_type = ?
                    ORDER BY created_at DESC
                    """
                    cursor.execute(query, (goal_type,))
                else:
                    query = """
                    SELECT * FROM goals 
                    WHERE achieved = FALSE AND (end_date IS NULL OR end_date >= date('now'))
                    ORDER BY created_at DESC
                    """
                    cursor.execute(query)
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error getting active goals: {e}")
            return []
    
    def update_goal_progress(self, goal_id: int, activities: List[Dict]) -> Dict:
        """Update goal progress based on activities"""
        try:
            goal = self.get_goal(goal_id)
            if not goal:
                return {"error": "Goal not found"}
            
            # Calculate progress based on goal type
            if goal['target_score']:
                # Score-based goal
                avg_score = sum(a.get('productivity_score', 0) for a in activities) / len(activities) if activities else 0
                progress = (avg_score / goal['target_score']) * 100
            elif goal['target_hours']:
                # Hours-based goal
                total_hours = sum(a.get('duration', 0) for a in activities) / 3600
                progress = (total_hours / goal['target_hours']) * 100
            elif goal['target_category']:
                # Category-based goal
                category_time = sum(
                    a.get('duration', 0) for a in activities 
                    if a.get('category') == goal['target_category']
                ) / 3600
                if goal.get('target_hours'):
                    progress = (category_time / goal['target_hours']) * 100
                else:
                    progress = min(100, category_time * 10)  # 10 hours = 100%
            else:
                progress = 0
            
            # Update goal progress
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                achieved = progress >= 100
                cursor.execute("""
                    UPDATE goals 
                    SET current_progress = ?, achieved = ?
                    WHERE id = ?
                """, (min(100, progress), achieved, goal_id))
                conn.commit()
            
            return {
                "goal_id": goal_id,
                "progress": min(100, progress),
                "achieved": progress >= 100,
                "current_value": avg_score if goal['target_score'] else total_hours if goal['target_hours'] else category_time
            }
        except Exception as e:
            self.logger.error(f"Error updating goal progress: {e}")
            return {"error": str(e)}
    
    def get_goal(self, goal_id: int) -> Optional[Dict]:
        """Get a specific goal by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM goals WHERE id = ?", (goal_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Error getting goal: {e}")
            return None
    
    def get_goals_progress(self) -> List[Dict]:
        """Get all goals with their current progress"""
        goals = self.get_active_goals()
        progress_list = []
        
        for goal in goals:
            # This would need to be called with actual activities
            # For now, return goal with current_progress
            progress_list.append({
                "goal": goal,
                "progress_percent": goal.get('current_progress', 0),
                "achieved": goal.get('achieved', False)
            })
        
        return progress_list
    
    def mark_goal_achieved(self, goal_id: int) -> bool:
        """Manually mark a goal as achieved"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE goals 
                    SET achieved = TRUE, current_progress = 100.0
                    WHERE id = ?
                """, (goal_id,))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error marking goal achieved: {e}")
            return False
    
    def delete_goal(self, goal_id: int) -> bool:
        """Delete a goal"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error deleting goal: {e}")
            return False


# Example usage
if __name__ == "__main__":
    tracker = GoalTracker()
    
    # Create a daily goal
    daily_goal = tracker.create_goal({
        'goal_type': 'daily',
        'target_score': 70,
        'description': 'Achieve 70% productivity today'
    })
    
    # Create a weekly goal
    weekly_goal = tracker.create_goal({
        'goal_type': 'weekly',
        'target_hours': 20,
        'target_category': 'productive',
        'description': 'Code for 20 hours this week',
        'start_date': datetime.now().date(),
        'end_date': (datetime.now() + timedelta(days=7)).date()
    })
    
    print(f"Created goals: {daily_goal}, {weekly_goal}")
    print(f"Active goals: {len(tracker.get_active_goals())}")
