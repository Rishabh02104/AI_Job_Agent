import os
import psycopg2
from config import settings

def run_migrations():
    migration_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "supabase",
        "migrations",
        "20260611000100_add_settings.sql"
    )
    
    if not os.path.exists(migration_file):
        print(f"Migration file not found: {migration_file}")
        return

    print(f"Reading migration file: {migration_file}")
    with open(migration_file, "r") as f:
        sql = f.read()

    db_url = settings.supabase_db_url
    print(f"Connecting to database...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        with conn.cursor() as cursor:
            print("Executing migration SQL...")
            cursor.execute(sql)
            print("Migration completed successfully!")
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migrations()
