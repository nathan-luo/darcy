from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Any, Optional






class Database:
    def __init__(self, database_url: Optional[str] = None) -> None:
        load_dotenv()
        self.database_url : Optional[str] = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL is not set.")
        
        self.engine = create_engine(self.database_url)
        self.Session = sessionmaker(bind=self.engine)

    def get_user(self, discord_id: str) -> Optional[dict[str, Any]]:
        query = text("""
            SELECT *
            FROM gold.users_base
            WHERE discord_id = :discord_id
            LIMIT 1
        """)
        with self.engine.connect() as conn:
            result = conn.execute(query, {"discord_id": discord_id})
            user = result.mappings().first()
            return dict(user) if user else None

    def get_user_fact(self, discord_id: str, days_back: int = 30) -> list[dict[str, Any]]:
        days_ago = datetime.now() - timedelta(days=days_back)
        
        query = text("""
            SELECT f.*
            FROM gold.all_facts f
            JOIN gold.users_base u ON f.user_name = u.name
            WHERE u.discord_id = :discord_id
              AND f.created_at >= :days_ago
            ORDER BY f.created_at DESC
        """)
        with self.engine.connect() as conn:
            result = conn.execute(query, {"discord_id": discord_id, "days_ago": days_ago})
            facts = result.mappings().all()
            return [dict(fact) for fact in facts]

    def set_user_fact(self, discord_id: str, fact_text: str) -> None:
        # Find user first
        user_query = text("""
            SELECT id
            FROM silver.user
            WHERE discord_id = :discord_id
            LIMIT 1
        """)
        with self.engine.begin() as conn:
            user_result = conn.execute(user_query, {"discord_id": discord_id})
            user = user_result.fetchone()
            if not user:
                raise ValueError(f"No user found with discord_id {discord_id}")

            user_id = user.id
            insert_query = text("""
                INSERT INTO silver.fact (user_id, fact_text)
                VALUES (:user_id, :fact_text)
            """)
            conn.execute(insert_query, {"user_id": user_id, "fact_text": fact_text})
            print(f"✅ Inserted fact for user {discord_id}")

