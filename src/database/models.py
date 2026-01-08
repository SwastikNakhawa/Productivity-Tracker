# database/models.py
from datetime import datetime
from typing import Dict, List, Optional
import json
import sqlite3


class ActivityModel:
    def __init__(self):
        self.table_name = "activities"
        self.llm_learning_table = "llm_learning_data"
        self.productivity_patterns_table = "productivity_patterns"

    def get_create_queries(self):
        return [
            f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                window_title TEXT,
                category TEXT NOT NULL,
                productivity_score INTEGER DEFAULT 50,
                duration INTEGER DEFAULT 0,
                start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_time DATETIME,
                tags TEXT, -- JSON array of tags
                user_feedback INTEGER DEFAULT 0, -- -1: wrong, 0: neutral, 1: correct
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {self.llm_learning_table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_id INTEGER,
                llm_prompt TEXT,
                llm_response TEXT,
                user_feedback INTEGER DEFAULT 0,
                corrected_response TEXT,
                context_data TEXT, -- JSON of context when response was generated
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (activity_id) REFERENCES {self.table_name} (id)
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {self.productivity_patterns_table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL, -- 'time_of_day', 'app_usage', 'category_trend'
                pattern_data TEXT NOT NULL, -- JSON data of the pattern
                confidence_score REAL DEFAULT 0.0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS productivity_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_type TEXT NOT NULL, -- 'deep_work', 'learning', 'meeting', 'break'
                start_time DATETIME,
                end_time DATETIME,
                productivity_score INTEGER,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]