from typing import Any, Optional

from tools.database.database import Database

# TODO maybe fact type


def store_fact(discord_id: str, fact: str) -> str:
    """
    Stores a personal fact about a user in memory. A personal fact is a fact about a user's life that is not related to their role in the club. These facts are later retrieved by the bot to understand a user.
    Good facts are:
    - Favorite food
    - Favorite color
    - Favorite movie
    - Favorite TV show
    - Favorite music artist
    - Favorite music song
    Bad facts are:
    - This person was active on discord today
    - This person was hungry 30 minutes ago
    - This person missed class yesterday
    Args:
        discord_id: The Discord ID of the user to store the fact for.
        fact: The fact to store.
    """
    db = Database()
    db.set_user_fact(discord_id, fact)
    print(f"Stored fact for {discord_id}: {fact}")
    return f"Stored fact for {discord_id}: {fact}"


def get_all_facts(discord_id: str) -> str:
    db = Database()
    facts: list[dict[str, Any]] = db.get_user_fact(discord_id)
    return str(facts)


def get_user_info(discord_id: str) -> str:
    db = Database()
    user_info: Optional[dict[str, Any]] = db.get_user(discord_id)
    return str(user_info)
