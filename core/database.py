"""
LikePilot Persistent Storage Layer
Uses SQLite for local, serverless persistence of session data, credit history, and analytics.
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'likepilot.db')

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_schema()

    @contextmanager
    def get_cursor(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_schema(self):
        """Initialize database tables if they don't exist."""
        with self.get_cursor() as cursor:
            # Sessions Table: Tracks individual agent runs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    status TEXT DEFAULT 'running', -- running, stopped, crashed
                    total_credits INTEGER DEFAULT 0,
                    tasks_completed INTEGER DEFAULT 0,
                    errors_count INTEGER DEFAULT 0
                )
            """)

            # Credit Logs Table: Granular history of every credit earned
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS credit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    agent_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    credits_earned INTEGER NOT NULL,
                    task_type TEXT NOT NULL, -- follow, like, comment
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    verification_time REAL, -- Time taken to verify credit
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
            """)

            # Error Logs Table: Track failures for analysis
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    agent_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    error_type TEXT NOT NULL, -- captcha, network, element_not_found, banned
                    error_message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
            """)

            # Stats Snapshot Table: For quick dashboard loading without aggregating logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stats_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_credits INTEGER DEFAULT 0,
                    active_agents INTEGER DEFAULT 0,
                    total_tasks INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_credit_logs_time ON credit_logs(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions(agent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_logs_time ON error_logs(timestamp)")

    def start_session(self, agent_id: str, platform: str) -> int:
        """Start a new agent session and return the session ID."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO sessions (agent_id, platform, status)
                VALUES (?, ?, 'running')
            """, (agent_id, platform))
            return cursor.lastrowid

    def end_session(self, session_id: int, status: str = 'stopped', total_credits: int = 0, tasks: int = 0, errors: int = 0):
        """End an agent session."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE sessions 
                SET end_time = ?, status = ?, total_credits = ?, tasks_completed = ?, errors_count = ?
                WHERE id = ?
            """, (datetime.now(), status, total_credits, tasks, errors, session_id))

    def log_credit(self, session_id: int, agent_id: str, platform: str, credits: int, task_type: str, verification_time: float = 0.0):
        """Log a successful credit earning event."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO credit_logs (session_id, agent_id, platform, credits_earned, task_type, verification_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, agent_id, platform, credits, task_type, verification_time))
            
            # Update session total
            cursor.execute("""
                UPDATE sessions SET total_credits = total_credits + ?, tasks_completed = tasks_completed + 1
                WHERE id = ?
            """, (credits, session_id))

    def log_error(self, session_id: Optional[int], agent_id: str, platform: str, error_type: str, message: str):
        """Log an error event."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO error_logs (session_id, agent_id, platform, error_type, error_message)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, agent_id, platform, error_type, message))
            
            if session_id:
                cursor.execute("UPDATE sessions SET errors_count = errors_count + 1 WHERE id = ?", (session_id,))

    def get_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Get aggregated analytics for the dashboard."""
        with self.get_cursor() as cursor:
            since = datetime.now().timestamp() - (hours * 3600)
            
            # Total Credits
            cursor.execute("""
                SELECT COALESCE(SUM(credits_earned), 0) as total 
                FROM credit_logs 
                WHERE timestamp >= datetime('now', '-' || ? || ' hours')
            """, (hours,))
            total_credits = cursor.fetchone()['total']

            # Tasks by Platform
            cursor.execute("""
                SELECT platform, COUNT(*) as count, SUM(credits_earned) as credits
                FROM credit_logs 
                WHERE timestamp >= datetime('now', '-' || ? || ' hours')
                GROUP BY platform
            """, (hours,))
            platform_stats = {row['platform']: {'tasks': row['count'], 'credits': row['credits']} for row in cursor.fetchall()}

            # Error Rate
            cursor.execute("""
                SELECT COUNT(*) as errors FROM error_logs 
                WHERE timestamp >= datetime('now', '-' || ? || ' hours')
            """, (hours,))
            total_errors = cursor.fetchone()['errors']
            
            total_tasks = sum(p['tasks'] for p in platform_stats.values())
            success_rate = ((total_tasks - total_errors) / total_tasks * 100) if total_tasks > 0 else 100.0

            # Hourly Chart Data
            cursor.execute("""
                SELECT strftime('%Y-%m-%d %H:00', timestamp) as hour, SUM(credits_earned) as credits
                FROM credit_logs 
                WHERE timestamp >= datetime('now', '-' || ? || ' hours')
                GROUP BY hour
                ORDER BY hour
            """, (hours,))
            chart_data = {row['hour']: row['credits'] for row in cursor.fetchall()}

            return {
                'total_credits': total_credits,
                'platforms': platform_stats,
                'success_rate': round(success_rate, 2),
                'total_errors': total_errors,
                'hourly_chart': chart_data
            }

    def save_snapshot(self, total_credits: int, active_agents: int, total_tasks: int, success_rate: float):
        """Save a current state snapshot for quick dashboard loading."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO stats_snapshots (total_credits, active_agents, total_tasks, success_rate)
                VALUES (?, ?, ?, ?)
            """, (total_credits, active_agents, total_tasks, success_rate))
            
            # Keep only last 1000 snapshots to prevent DB bloat
            cursor.execute("DELETE FROM stats_snapshots WHERE id < (SELECT MAX(id) - 1000 FROM stats_snapshots)")

# Singleton instance
db = Database()
