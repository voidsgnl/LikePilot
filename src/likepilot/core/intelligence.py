"""
LikePilot Intelligence Engine
Local, heuristic-based optimization without LLMs or external APIs.
Uses statistical analysis, weighted random selection, and adaptive algorithms.
"""
import sqlite3
import time
import random
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict

class IntelligenceEngine:
    """
    Local intelligence layer for LikePilot.
    Provides node scoring, cooldown management, profile health, and anomaly detection.
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or ':memory:'
        # Keep a persistent connection for in-memory databases
        if self.db_path == ':memory:':
            self._persistent_conn = sqlite3.connect(':memory:', check_same_thread=False)
            self._persistent_conn.row_factory = sqlite3.Row
            self._init_schema(self._persistent_conn)
        else:
            self._persistent_conn = None
            self._init_schema()
        
        # In-memory caches for performance
        self.node_scores: Dict[str, float] = {}
        self.cooldown_timers: Dict[str, float] = {}
        self.profile_health: Dict[str, float] = {}
        self.recent_errors: List[Dict] = []
    
    def _get_conn(self):
        """Get database connection."""
        if self._persistent_conn:
            return self._persistent_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_schema(self, conn=None):
        """Initialize intelligence-specific tables."""
        if conn is None:
            conn = self._get_conn()
        cursor = conn.cursor()
        
        # Node Performance Table: Track success/failure per platform+node combination
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS node_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                node_type TEXT NOT NULL,  -- follow, like, comment
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success INTEGER NOT NULL,  -- 1 for success, 0 for failure
                response_time REAL,  -- Time taken to complete task
                credits_earned INTEGER DEFAULT 0
            )
        """)
        
        # Cooldown Events Table: Track when platforms throttle/ban
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cooldown_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                event_type TEXT NOT NULL,  -- throttle, captcha, ban, unavailable
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                duration_seconds INTEGER,  -- How long the cooldown lasted
                resolved INTEGER DEFAULT 0
            )
        """)
        
        # Profile Health Table: Long-term scoring of account quality
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profile_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT UNIQUE NOT NULL,
                platform TEXT NOT NULL,
                score REAL DEFAULT 100.0,  -- 0-100 health score
                total_tasks INTEGER DEFAULT 0,
                successes INTEGER DEFAULT 0,
                failures INTEGER DEFAULT 0,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'  -- active, warning, retired
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_node_perf_time ON node_performance(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_node_perf_platform ON node_performance(platform, node_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cooldown_platform ON cooldown_events(platform, resolved)")
        
        conn.commit()
        # Don't close persistent connection
        if not self._persistent_conn:
            if not self._persistent_conn: conn.close()
    
    # ==================== NODE SCORING & SELECTION ====================
    
    def record_node_result(self, platform: str, node_type: str, success: bool, 
                          response_time: float = 0.0, credits_earned: int = 0):
        """Record the outcome of a node execution for performance tracking."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO node_performance (platform, node_type, success, response_time, credits_earned)
            VALUES (?, ?, ?, ?, ?)
        """, (platform, node_type, 1 if success else 0, response_time, credits_earned))
        
        conn.commit()
        # Don't close persistent connection
        if not self._persistent_conn:
            if not self._persistent_conn: conn.close()
        
        # Update in-memory cache
        key = f"{platform}:{node_type}"
        self._recalculate_node_score(key)
    
    def _recalculate_node_score(self, key: str, window_minutes: int = 60):
        """Recalculate node score based on recent performance."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        since = datetime.now() - timedelta(minutes=window_minutes)
        
        cursor.execute("""
            SELECT success, response_time, credits_earned
            FROM node_performance
            WHERE platform || ':' || node_type = ?
            AND timestamp >= ?
            ORDER BY timestamp DESC
        """, (key, since.isoformat()))
        
        rows = cursor.fetchall()
        if not self._persistent_conn: conn.close()
        
        if not rows:
            self.node_scores[key] = 50.0  # Neutral score for new nodes
            return
        
        successes = sum(r['success'] for r in rows)
        total = len(rows)
        avg_response = statistics.mean(r['response_time'] for r in rows if r['response_time'] > 0) if rows else 0
        avg_credits = statistics.mean(r['credits_earned'] for r in rows) if rows else 0
        
        # Scoring algorithm:
        # - Base: Success rate (0-100)
        # - Bonus: Fast response (<2s = +10, <5s = +5)
        # - Bonus: High credit yield (>5 credits = +5)
        base_score = (successes / total) * 100
        
        speed_bonus = 0
        if avg_response > 0:
            if avg_response < 2.0:
                speed_bonus = 10
            elif avg_response < 5.0:
                speed_bonus = 5
        
        yield_bonus = 5 if avg_credits > 5 else 0
        
        final_score = min(100.0, base_score + speed_bonus + yield_bonus)
        self.node_scores[key] = final_score
    
    def get_best_nodes(self, available_nodes: List[Tuple[str, str]], top_n: int = 3) -> List[Tuple[str, str, float]]:
        """
        Return top N nodes sorted by score using weighted random selection.
        Returns: [(platform, node_type, score), ...]
        """
        scored_nodes = []
        
        for platform, node_type in available_nodes:
            key = f"{platform}:{node_type}"
            
            # Use cached score or calculate fresh
            if key not in self.node_scores:
                self._recalculate_node_score(key)
            
            score = self.node_scores.get(key, 50.0)
            
            # Check if node is in cooldown
            if self.is_in_cooldown(platform):
                score *= 0.1  # Heavily penalize nodes on throttled platforms
            
            scored_nodes.append((platform, node_type, score))
        
        # Sort by score descending
        scored_nodes.sort(key=lambda x: x[2], reverse=True)
        
        # Return top N with some randomness (weighted selection)
        if len(scored_nodes) <= top_n:
            return scored_nodes
        
        # Weighted random selection from top candidates
        top_candidates = scored_nodes[:top_n * 2]  # Consider more candidates
        weights = [max(1, s[2]) for s in top_candidates]
        
        selected = random.choices(top_candidates, weights=weights, k=top_n)
        return sorted(selected, key=lambda x: x[2], reverse=True)
    
    # ==================== COOLDOWN MANAGEMENT ====================
    
    def report_cooldown_event(self, platform: str, event_type: str, auto_resolve_minutes: int = 30):
        """
        Report a throttle/ban/CAPTCHA event.
        Automatically sets a cooldown timer.
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO cooldown_events (platform, event_type, duration_seconds)
            VALUES (?, ?, ?)
        """, (platform, event_type, auto_resolve_minutes * 60))
        
        conn.commit()
        if not self._persistent_conn: conn.close()
        
        # Set in-memory cooldown timer
        cooldown_key = platform
        self.cooldown_timers[cooldown_key] = time.time() + (auto_resolve_minutes * 60)
        
        print(f"[INTELLIGENCE] Platform '{platform}' entered cooldown ({event_type}) for {auto_resolve_minutes} minutes")
    
    def is_in_cooldown(self, platform: str) -> bool:
        """Check if a platform is currently in cooldown."""
        # Check in-memory timer first
        if platform in self.cooldown_timers:
            if time.time() < self.cooldown_timers[platform]:
                return True
            else:
                # Timer expired, remove it
                del self.cooldown_timers[platform]
        
        # Check database for unresolved events
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, start_time, duration_seconds
            FROM cooldown_events
            WHERE platform = ? AND resolved = 0
            ORDER BY id DESC
            LIMIT 1
        """, (platform,))
        
        row = cursor.fetchone()
        
        if row:
            start_time = datetime.fromisoformat(row['start_time']).timestamp()
            duration = row['duration_seconds'] or 1800  # Default 30 min
            
            if time.time() < start_time + duration:
                if not self._persistent_conn: conn.close()
                return True
            else:
                # Auto-resolve expired cooldown
                cursor.execute("UPDATE cooldown_events SET resolved = 1, end_time = ? WHERE id = ?",
                             (datetime.now(), row['id']))
                conn.commit()
        
        if not self._persistent_conn: conn.close()
        return False
    
    def get_cooldown_remaining(self, platform: str) -> Optional[int]:
        """Get remaining cooldown time in seconds, or None if not in cooldown."""
        if platform in self.cooldown_timers:
            remaining = self.cooldown_timers[platform] - time.time()
            return max(0, int(remaining))
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT start_time, duration_seconds
            FROM cooldown_events
            WHERE platform = ? AND resolved = 0
            ORDER BY id DESC
            LIMIT 1
        """, (platform,))
        
        row = cursor.fetchone()
        if not self._persistent_conn: conn.close()
        
        if row:
            start_time = datetime.fromisoformat(row['start_time']).timestamp()
            duration = row['duration_seconds'] or 1800
            remaining = start_time + duration - time.time()
            return max(0, int(remaining))
        
        return None
    
    def adaptive_delay(self, platform: str, base_delay: float = 2.0) -> float:
        """
        Calculate adaptive delay based on recent error rate for platform.
        Increases delay if errors are detected to avoid detection.
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Get error rate in last 10 minutes
        since = datetime.now() - timedelta(minutes=10)
        
        cursor.execute("""
            SELECT COUNT(*) as errors
            FROM node_performance np
            JOIN cooldown_events ce ON np.platform = ce.platform
            WHERE np.platform = ?
            AND np.timestamp >= ?
            AND np.success = 0
        """, (platform, since.isoformat()))
        
        recent_errors = cursor.fetchone()['errors']
        if not self._persistent_conn: conn.close()
        
        # Increase delay based on error count
        multiplier = 1.0 + (recent_errors * 0.5)  # +50% per error
        multiplier = min(multiplier, 5.0)  # Cap at 5x
        
        jitter = random.uniform(0.8, 1.2)  # Add randomness
        return base_delay * multiplier * jitter
    
    # ==================== PROFILE HEALTH SCORING ====================
    
    def update_profile_health(self, profile_id: str, platform: str, success: bool):
        """Update profile health score based on task outcome."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Upsert profile record
        cursor.execute("""
            INSERT INTO profile_health (profile_id, platform, total_tasks, successes, failures, last_activity)
            VALUES (?, ?, 1, ?, ?, ?)
            ON CONFLICT(profile_id) DO UPDATE SET
                total_tasks = total_tasks + 1,
                successes = successes + ?,
                failures = failures + ?,
                last_activity = ?
        """, (profile_id, platform, 1 if success else 0, 0 if success else 1, datetime.now(),
              1 if success else 0, 1 if success else 0, datetime.now()))
        
        conn.commit()
        
        # Recalculate score
        cursor.execute("""
            SELECT total_tasks, successes, failures
            FROM profile_health
            WHERE profile_id = ?
        """, (profile_id,))
        
        row = cursor.fetchone()
        
        if row and row['total_tasks'] > 0:
            success_rate = (row['successes'] / row['total_tasks']) * 100
            
            # Penalize heavy if success rate drops below 70%
            if success_rate < 70:
                score = max(0, success_rate - 20)
            elif success_rate < 85:
                score = success_rate
            else:
                score = min(100, success_rate + 5)  # Small bonus for excellent performance
            
            # Determine status
            if score < 50:
                status = 'retired'
            elif score < 70:
                status = 'warning'
            else:
                status = 'active'
            
            cursor.execute("""
                UPDATE profile_health
                SET score = ?, status = ?
                WHERE profile_id = ?
            """, (score, status, profile_id))
            
            conn.commit()
            
            self.profile_health[f"{profile_id}:{platform}"] = score
            
            if status == 'retired':
                print(f"[INTELLIGENCE] Profile '{profile_id}' retired on {platform} (score: {score:.1f})")
        
        if not self._persistent_conn: conn.close()
    
    def get_profile_status(self, profile_id: str, platform: str) -> Tuple[float, str]:
        """Get profile health score and status."""
        key = f"{profile_id}:{platform}"
        
        if key in self.profile_health:
            # Return cached value
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT score, status FROM profile_health WHERE profile_id = ? AND platform = ?",
                         (profile_id, platform))
            row = cursor.fetchone()
            if not self._persistent_conn: conn.close()
            
            if row:
                return (row['score'], row['status'])
        
        return (100.0, 'active')  # Default for new profiles
    
    def get_available_profiles(self, platform: str, min_score: float = 50.0) -> List[Dict]:
        """Get list of healthy profiles for a platform."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT profile_id, platform, score, status, total_tasks, successes, failures
            FROM profile_health
            WHERE platform = ?
            AND status != 'retired'
            AND score >= ?
            ORDER BY score DESC
        """, (platform, min_score))
        
        results = [dict(row) for row in cursor.fetchall()]
        if not self._persistent_conn: conn.close()
        
        return results
    
    # ==================== ANOMALY DETECTION ====================
    
    def detect_anomaly(self, platform: str, current_error_rate: float, 
                      window_minutes: int = 15) -> Optional[str]:
        """
        Detect anomalies in error patterns.
        Returns anomaly type if detected, None otherwise.
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        since = datetime.now() - timedelta(minutes=window_minutes)
        
        # Get historical error rate for comparison
        cursor.execute("""
            SELECT AVG(CASE WHEN success = 0 THEN 1.0 ELSE 0.0 END) * 100 as avg_error_rate,
                   COUNT(*) as total_tasks
            FROM node_performance
            WHERE platform = ?
            AND timestamp >= ?
            AND timestamp < datetime('now', '-' || ? || ' minutes')
        """, (platform, since.isoformat(), window_minutes))
        
        row = cursor.fetchone()
        if not self._persistent_conn: conn.close()
        
        if not row or row['total_tasks'] < 5:
            return None  # Not enough data
        
        historical_error_rate = row['avg_error_rate'] or 0
        
        # Detect sudden spike (3x normal error rate)
        if current_error_rate > (historical_error_rate * 3) and current_error_rate > 30:
            return "error_spike"
        
        # Detect complete failure (100% errors in last 5 tasks)
        if current_error_rate == 100:
            return "complete_failure"
        
        return None
    
    def log_recent_error(self, platform: str, error_type: str):
        """Log recent error for anomaly detection."""
        self.recent_errors.append({
            'platform': platform,
            'error_type': error_type,
            'timestamp': time.time()
        })
        
        # Keep only last 100 errors
        if len(self.recent_errors) > 100:
            self.recent_errors = self.recent_errors[-100:]
    
    def get_error_trend(self, platform: str, window_seconds: int = 300) -> str:
        """
        Analyze error trend in recent window.
        Returns: 'increasing', 'stable', or 'decreasing'
        """
        now = time.time()
        cutoff = now - window_seconds
        
        recent = [e for e in self.recent_errors 
                 if e['platform'] == platform and e['timestamp'] > cutoff]
        
        if len(recent) < 3:
            return 'stable'
        
        # Split into two halves
        mid = len(recent) // 2
        first_half = len(recent[:mid])
        second_half = len(recent[mid:])
        
        if second_half > first_half * 1.5:
            return 'increasing'
        elif second_half < first_half * 0.5:
            return 'decreasing'
        else:
            return 'stable'


# Singleton instance
intelligence = IntelligenceEngine()
