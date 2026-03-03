import sqlite3
from pathlib import Path
from typing import List, Dict, Optional


class Database:
    def __init__(self, db_path: str = "voice_training.db"):
        # Normalize DB path so running from different working directories is consistent.
        p = Path(db_path)
        if not p.is_absolute():
            p = Path(__file__).resolve().parent / p
        self.db_path = str(p)
        self.init_database()

    def init_database(self):
        """Initialize SQLite database with required tables (and lightweight migrations)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Sessions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                persona_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                cartridge_id TEXT,
                scenario_id TEXT,
                score_total INTEGER DEFAULT 0,
                score_count INTEGER DEFAULT 0
            )
            """
        )

        # Lightweight migrations
        cursor.execute("PRAGMA table_info(sessions)")
        session_cols = {row[1] for row in cursor.fetchall()}
        if "cartridge_id" not in session_cols:
            cursor.execute("ALTER TABLE sessions ADD COLUMN cartridge_id TEXT")
        if "scenario_id" not in session_cols:
            cursor.execute("ALTER TABLE sessions ADD COLUMN scenario_id TEXT")
        if "score_total" not in session_cols:
            cursor.execute("ALTER TABLE sessions ADD COLUMN score_total INTEGER DEFAULT 0")
        if "score_count" not in session_cols:
            cursor.execute("ALTER TABLE sessions ADD COLUMN score_count INTEGER DEFAULT 0")

        # Messages table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                speaker TEXT NOT NULL,  -- 'user' or 'ai'
                text TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
            """
        )

        # Feedback score events (optional but useful for trend lines)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS session_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
            """
        )

        conn.commit()
        conn.close()

    def create_session(
        self,
        session_id: str,
        persona_id: str,
        user_name: str,
        cartridge_id: Optional[str] = None,
        scenario_id: Optional[str] = None,
    ):
        """Create a new training session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO sessions (id, persona_id, user_name, cartridge_id, scenario_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, persona_id, user_name, cartridge_id, scenario_id),
        )

        conn.commit()
        conn.close()

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """Get recent training sessions"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM sessions
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def add_message(self, session_id: str, speaker: str, text: str):
        """Add a message to the conversation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO messages (session_id, speaker, text)
            VALUES (?, ?, ?)
            """,
            (session_id, speaker, text),
        )

        cursor.execute(
            """
            UPDATE sessions
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (session_id,),
        )

        conn.commit()
        conn.close()

    def get_messages(self, session_id: str) -> List[Dict]:
        """Get all messages for a session"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
            """,
            (session_id,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def record_feedback_score(self, session_id: str, score: int) -> Optional[int]:
        """Record a feedback score event and update the session running average.

        Returns the updated average score, or None if session not found.
        """

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Update totals
        cursor.execute(
            """
            UPDATE sessions
            SET
                score_total = COALESCE(score_total, 0) + ?,
                score_count = COALESCE(score_count, 0) + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (score, session_id),
        )

        if cursor.rowcount == 0:
            conn.commit()
            conn.close()
            return None

        # Insert event
        cursor.execute(
            """
            INSERT INTO session_scores (session_id, score)
            VALUES (?, ?)
            """,
            (session_id, score),
        )

        # Compute and set average
        cursor.execute("SELECT score_total, score_count FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        total = int(row[0] or 0)
        count = int(row[1] or 0)
        avg = round(total / count) if count > 0 else 0

        cursor.execute(
            """
            UPDATE sessions
            SET score = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (avg, session_id),
        )

        conn.commit()
        conn.close()

        return avg

    def get_session_scores(self, session_id: str) -> List[Dict]:
        """Get all feedback score events for a session"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT score, timestamp
            FROM session_scores
            WHERE session_id = ?
            ORDER BY timestamp ASC
            """,
            (session_id,),
        )

        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_session_score(self, session_id: str, score: int):
        """Finalize session score (mark completed)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE sessions
            SET score = ?, status = 'completed', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (score, session_id),
        )

        conn.commit()
        conn.close()

    def get_session_stats(self) -> Dict:
        """Get overall platform statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM sessions")
        total_sessions = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM sessions WHERE status = 'completed'")
        completed_sessions = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(score) FROM sessions WHERE score > 0")
        avg_score_result = cursor.fetchone()[0]
        avg_score = round(avg_score_result, 1) if avg_score_result else 0

        cursor.execute("SELECT COUNT(*) FROM messages")
        total_messages = cursor.fetchone()[0]

        conn.close()

        return {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "avg_score": avg_score,
            "total_messages": total_messages,
        }
