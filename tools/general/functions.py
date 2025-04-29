

def store_fact(discord_id: str, fact: str):
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
    print(f"Storing fact for {discord_id}: {fact}")
