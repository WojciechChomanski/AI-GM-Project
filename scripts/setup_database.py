import sqlite3
import os

# === DATABASE SETTINGS ===
DATABASE_PATH = "../database/characters.db"

# === DATABASE INITIALIZATION ===
def initialize_database():
    """Creates the characters database and the necessary table if they don't exist."""
    if not os.path.exists("../database"):
        os.makedirs("../database")

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    # Create characters table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        gender TEXT,
        race TEXT,
        background TEXT,
        character_class TEXT,
        strength INTEGER,
        toughness INTEGER,
        agility INTEGER,
        mobility INTEGER,
        willpower INTEGER,
        charisma INTEGER,
        intelligence INTEGER,
        perception INTEGER,
        corruption INTEGER DEFAULT 0,
        stress INTEGER DEFAULT 0
    );
    """)

    connection.commit()
    connection.close()
    print("✅ Database initialized and ready.")

# === QUICK TEST: RUN DIRECTLY ===
if __name__ == "__main__":
    initialize_database()