

## python
from sqlalchemy import create_engine, text

# PostgreSQL connection
db_url = "postgresql://nsamizi_user:##000000@localhost:5432/nsamizi_db"
engine = create_engine(db_url, echo=False, future=True)

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ PostgreSQL Connection Successful!")
        print(f"Database: nsamizi_db")
        print(f"User: nsamizi_user")
        print(f"Server: localhost:5432")
except Exception as e:
    print(f"❌ Connection Failed: {e}")

# List all tables
try:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema='public'
        """))
        tables = result.fetchall()
        print(f"\n✅ Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
except Exception as e:
    print(f"❌ Error listing tables: {e}")
