import sqlite3

DB_NAME = "podcasts.db"

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def init_db(self):
        self.con = sqlite3.connect(self.db_path)
        cur = self.con.cursor()

        cur.execute("""
                    CREATE TABLE IF NOT EXISTS episodes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        podcast_id TEXT NOT NULL,
                        podcast_title TEXT NOT NULL,
                        category TEXT NOT NULL,
                        published TEXT NOT NULL,
                        audio_url TEXT NOT NULL,
                        duration TEXT NOT NULL
                    )
        """)

    def get_episode(self, podcast_id: str, podcast_title: str) -> list:
        cur = self.con.cursor()
        res = cur.execute("SELECT * FROM episodes WHERE podcast_id = ? AND podcast_name = ?", (podcast_id, podcast_title))

        return res.fetchall()
    
    def episode_exist(self, podcast_id: str, podcast_title: str) -> bool:
        if self.get_episode(podcast_id=podcast_id, podcast_title=podcast_title) is None:
            return False
        return True
    
    def save_episode(self, podcast_id: str, podcast_title: str, category: str, published: str, audio_url: str, duration: str) -> None:
        cur = self.con.cursor()
        cur.execute("""
                    INSERT INTO episodes (podcast_id, podcast_title, category, published, audio_url, duration) VALUES (?, ?, ?, ?, ?, ?)
                    """, (podcast_id, podcast_title, category, published, audio_url, duration))
        self.con.commit()

DB = Database(DB_NAME)
DB.init_db()