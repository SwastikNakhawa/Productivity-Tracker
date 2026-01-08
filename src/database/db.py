# database/db.py
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class DatabaseManager:
    def __init__(self, db_path: str = "productivity_tracker.db"):
        self.db_path = db_path
        self.setup_logging()
        self.init_database()

    def setup_logging(self):
        self.logger = logging.getLogger(__name__)

    def init_database(self):
        """Initialize database with all tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create tables
                tables = [
                    """
                    CREATE TABLE IF NOT EXISTS activities (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        app_name TEXT NOT NULL,
                        window_title TEXT,
                        category TEXT NOT NULL,
                        productivity_score INTEGER DEFAULT 50,
                        duration INTEGER DEFAULT 0,
                        start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                        end_time DATETIME,
                        tags TEXT,
                        user_feedback INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """,
                    """
                    CREATE TABLE IF NOT EXISTS llm_learning_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        activity_id INTEGER,
                        llm_prompt TEXT,
                        llm_response TEXT,
                        user_feedback INTEGER DEFAULT 0,
                        corrected_response TEXT,
                        context_data TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (activity_id) REFERENCES activities (id)
                    )
                    """,
                    """
                    CREATE TABLE IF NOT EXISTS productivity_patterns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pattern_type TEXT NOT NULL,
                        pattern_data TEXT NOT NULL,
                        confidence_score REAL DEFAULT 0.0,
                        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                    """,
                    """
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key TEXT UNIQUE NOT NULL,
                        value TEXT NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                ]

                for query in tables:
                    cursor.execute(query)

                # Create indexes
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_activities_time ON activities(start_time)",
                    "CREATE INDEX IF NOT EXISTS idx_activities_category ON activities(category)",
                    "CREATE INDEX IF NOT EXISTS idx_activities_score ON activities(productivity_score)",
                    "CREATE INDEX IF NOT EXISTS idx_learning_feedback ON llm_learning_data(user_feedback)"
                ]

                for index in indexes:
                    cursor.execute(index)

                conn.commit()
                self.logger.info("✅ Database initialized successfully")

        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}")
            raise

    def log_activity(self, activity_data: Dict) -> Optional[int]:
        """Log a new activity with enhanced data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                query = """
                INSERT INTO activities 
                (app_name, window_title, category, productivity_score, duration, start_time, end_time, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """

                tags_json = json.dumps(activity_data.get('tags', []))

                cursor.execute(query, (
                    activity_data.get('app_name'),
                    activity_data.get('window_title'),
                    activity_data.get('category'),
                    activity_data.get('productivity_score', 50),
                    activity_data.get('duration', 0),
                    activity_data.get('start_time', datetime.now()),
                    activity_data.get('end_time'),
                    tags_json
                ))

                activity_id = cursor.lastrowid
                conn.commit()

                self.logger.info(f"📝 Logged activity: {activity_data.get('app_name')} (ID: {activity_id})")
                return activity_id

        except Exception as e:
            self.logger.error(f"Error logging activity: {e}")
            return None

    # Add this alias for backward compatibility
    def insert_activity(self, activity_data: Dict) -> Optional[int]:
        """Alias for log_activity for backward compatibility"""
        return self.log_activity(activity_data)

    def log_llm_interaction(self, activity_id: int, prompt: str, response: str, context: Dict):
        """Log LLM interactions for learning"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                query = """
                INSERT INTO llm_learning_data 
                (activity_id, llm_prompt, llm_response, context_data)
                VALUES (?, ?, ?, ?)
                """

                context_json = json.dumps(context)

                cursor.execute(query, (
                    activity_id,
                    prompt,
                    response,
                    context_json
                ))

                conn.commit()
                self.logger.info("📚 Logged LLM interaction for learning")

        except Exception as e:
            self.logger.error(f"Error logging LLM interaction: {e}")

    def update_llm_feedback(self, llm_interaction_id: int, feedback: int, corrected_response: str = None):
        """Update LLM interaction with user feedback"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                query = """
                UPDATE llm_learning_data 
                SET user_feedback = ?, corrected_response = ?
                WHERE id = ?
                """

                cursor.execute(query, (feedback, corrected_response, llm_interaction_id))
                conn.commit()

                self.logger.info(f"📝 Updated LLM feedback: {feedback}")

        except Exception as e:
            self.logger.error(f"Error updating LLM feedback: {e}")

    def get_recent_activities(self, limit: int = 50, hours: int = None) -> List[Dict]:
        """Get recent activities with optional time filter - FIXED VERSION"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                if hours:
                    # Filter by hours
                    query = """
                    SELECT * FROM activities
                    WHERE start_time >= datetime('now', ?)
                    ORDER BY start_time DESC
                    LIMIT ?
                    """
                    cursor.execute(query, (f'-{hours} hours', limit))
                else:
                    # Get all recent activities
                    query = """
                    SELECT * FROM activities
                    ORDER BY start_time DESC
                    LIMIT ?
                    """
                    cursor.execute(query, (limit,))

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            self.logger.error(f"Error getting recent activities: {e}")
            return []

    def get_activities(self, limit: int = 50) -> List[Dict]:
        """Alias for get_recent_activities for backward compatibility"""
        return self.get_recent_activities(limit=limit)

    def get_user_productivity_patterns(self, days: int = 30) -> Dict:
        """Analyze and return user productivity patterns"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)

                patterns = {
                    'time_of_day_patterns': self._get_time_of_day_patterns(cursor, start_date, end_date),
                    'app_usage_patterns': self._get_app_usage_patterns(cursor, start_date, end_date),
                    'category_trends': self._get_category_trends(cursor, start_date, end_date),
                    'productivity_scores': self._get_productivity_scores(cursor, start_date, end_date),
                    'learning_preferences': self._get_learning_preferences(cursor)
                }

                return patterns

        except Exception as e:
            self.logger.error(f"Error getting productivity patterns: {e}")
            return {}

    def _get_time_of_day_patterns(self, cursor, start_date, end_date):
        """Get patterns based on time of day"""
        query = """
        SELECT 
            strftime('%H', start_time) as hour,
            AVG(productivity_score) as avg_score,
            COUNT(*) as activity_count
        FROM activities 
        WHERE start_time BETWEEN ? AND ?
        GROUP BY strftime('%H', start_time)
        ORDER BY hour
        """

        cursor.execute(query, (start_date, end_date))
        return [dict(row) for row in cursor.fetchall()]

    def _get_app_usage_patterns(self, cursor, start_date, end_date):
        """Get application usage patterns"""
        query = """
        SELECT 
            app_name,
            category,
            SUM(duration) as total_duration,
            AVG(productivity_score) as avg_score,
            COUNT(*) as usage_count
        FROM activities 
        WHERE start_time BETWEEN ? AND ?
        GROUP BY app_name, category
        HAVING total_duration > 300
        ORDER BY total_duration DESC
        LIMIT 20
        """

        cursor.execute(query, (start_date, end_date))
        return [dict(row) for row in cursor.fetchall()]

    def _get_category_trends(self, cursor, start_date, end_date):
        """Get category-based productivity trends"""
        query = """
        SELECT 
            category,
            SUM(duration) as total_duration,
            AVG(productivity_score) as avg_score,
            COUNT(*) as activity_count
        FROM activities 
        WHERE start_time BETWEEN ? AND ?
        GROUP BY category
        ORDER BY total_duration DESC
        """

        cursor.execute(query, (start_date, end_date))
        return [dict(row) for row in cursor.fetchall()]

    def _get_productivity_scores(self, cursor, start_date, end_date):
        """Get productivity score distribution"""
        query = """
        SELECT 
            CASE 
                WHEN productivity_score >= 80 THEN 'high'
                WHEN productivity_score >= 60 THEN 'medium'
                WHEN productivity_score >= 40 THEN 'low'
                ELSE 'very_low'
            END as score_range,
            COUNT(*) as count,
            SUM(duration) as total_duration
        FROM activities 
        WHERE start_time BETWEEN ? AND ?
        GROUP BY score_range
        """

        cursor.execute(query, (start_date, end_date))
        return [dict(row) for row in cursor.fetchall()]

    def _get_learning_preferences(self, cursor):
        """Get user learning preferences from LLM feedback"""
        query = """
        SELECT 
            context_data,
            llm_response,
            corrected_response,
            user_feedback
        FROM llm_learning_data
        WHERE user_feedback != 0
        ORDER BY created_at DESC
        LIMIT 50
        """

        cursor.execute(query)
        results = [dict(row) for row in cursor.fetchall()]

        # Also get from activities with user feedback
        feedback_query = """
        SELECT app_name, category, productivity_score, user_feedback, tags
        FROM activities
        WHERE user_feedback != 0
        ORDER BY created_at DESC
        LIMIT 50
        """

        cursor.execute(feedback_query)
        activity_feedback = [dict(row) for row in cursor.fetchall()]

        return {
            'llm_feedback': results,
            'activity_feedback': activity_feedback
        }

    def save_productivity_pattern(self, pattern_type: str, pattern_data: Dict, confidence: float):
        """Save discovered productivity patterns"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Deactivate old patterns of same type
                cursor.execute("""
                    UPDATE productivity_patterns 
                    SET is_active = FALSE 
                    WHERE pattern_type = ?
                """, (pattern_type,))

                # Insert new pattern
                query = """
                INSERT INTO productivity_patterns 
                (pattern_type, pattern_data, confidence_score)
                VALUES (?, ?, ?)
                """

                pattern_json = json.dumps(pattern_data)
                cursor.execute(query, (pattern_type, pattern_json, confidence))
                conn.commit()

                self.logger.info(f"💾 Saved productivity pattern: {pattern_type}")

        except Exception as e:
            self.logger.error(f"Error saving productivity pattern: {e}")