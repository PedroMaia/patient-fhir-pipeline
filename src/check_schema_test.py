"""Quick schema inspection."""
from db import get_connection

with get_connection() as con:
    print("Tables:")
    print(con.execute("SHOW TABLES").fetchall())
    print("\nPatient schema:")
    print(con.execute("DESCRIBE patient").fetchdf())