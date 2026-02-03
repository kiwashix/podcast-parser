import sqlite3

DB_NAME = "podcasts.db"

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row  # ← Добавляем это
        return con

    def init_db(self):
        con = self._get_connection()
        cur = con.cursor()

        cur.execute("""
                    CREATE TABLE IF NOT EXISTS episodes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        podcast_id TEXT NOT NULL,
                        podcast_name TEXT NOT NULL,
                        podcast_title TEXT NOT NULL,
                        category TEXT NOT NULL,
                        published BOOL DEFAULT FALSE,
                        audio_url TEXT NOT NULL,
                        duration TEXT NOT NULL
                    )
        """)
        con.commit()
        con.close()

    def get_episode(self, podcast_id: str, podcast_title: str) -> list:
        con = self._get_connection()
        cur = con.cursor()
        res = cur.execute("SELECT * FROM episodes WHERE podcast_id = ? AND podcast_title = ?", (podcast_id, podcast_title))
        result = [dict(row) for row in res.fetchall()]  # ← Конвертируем в dict
        con.close()
        return result
    
    def episode_exist(self, podcast_id: str, podcast_title: str) -> bool:
        result = self.get_episode(podcast_id=podcast_id, podcast_title=podcast_title)
        return len(result) > 0
    
    def save_episode(self, podcast_id: str, podcast_name: str, podcast_title: str, category: str, published: str, audio_url: str, duration: str) -> None:
        con = self._get_connection()
        cur = con.cursor()
        cur.execute("""
                    INSERT INTO episodes (podcast_id, podcast_name, podcast_title, category, published, audio_url, duration) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (podcast_id, podcast_name, podcast_title, category, published, audio_url, duration))
        con.commit()
        con.close()

    def mark_as_used(self, id: int) -> None:
        con = self._get_connection()
        cur = con.cursor()
        cur.execute("""
                    UPDATE episodes SET published = 1 WHERE id = ?
                    """, (id, ))
        con.commit()
        con.close()

    def get_random(self, count: int = 1) -> list[dict]:
        """Получить случайные неопубликованные эпизоды из базы данных."""
        con = self._get_connection()
        cur = con.cursor()
        res = cur.execute("SELECT * FROM episodes WHERE published = 0 ORDER BY RANDOM() LIMIT ?", (count,))
        result = [dict(row) for row in res.fetchall()]  # ← Конвертируем в dict
        con.close()
        return result

DB = Database(DB_NAME)
DB.init_db()