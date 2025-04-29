from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Your database URL
DATABASE_URL = "postgresql://postgres:7crQ9MrrBC216QmgSB^S@darcydb.crgk48smefvn.ap-southeast-2.rds.amazonaws.com:5432/postgres"

# Create engine
engine = create_engine(DATABASE_URL)

# Test connection
try:
    # Connect and execute a simple query
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        version = result.fetchone()
        print(f"Successfully connected to PostgreSQL. Version: {version[0]}")

except Exception as e:
    print(f"Error connecting to PostgreSQL database: {e}")
