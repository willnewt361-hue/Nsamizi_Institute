import sqlite3

DB = "nsamizi.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

tables = [
    "students",
    "people",
    "courses",
    "attendance",
    "notifications",
    "audit_logs"
]
print("\n=== DATABASE AUDIT ===\n")

for table in tables:
    try:
        cur.execute(
            f"SELECT COUNT(*) FROM {table}"
        )
        count = cur.fetchone()[0]

        print(
            f"{table:<20} {count}"
        )

    except Exception as e:
        print(
            f"{table:<20} ERROR"
        )
conn.close()