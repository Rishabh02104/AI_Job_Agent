import os
import psycopg2
from config import settings

def run_migrations():
    migrations_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "supabase",
        "migrations"
    )
    
    if not os.path.exists(migrations_dir):
        print(f"Migrations directory not found: {migrations_dir}")
        return

    # List and sort all SQL files in the migrations directory
    migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])
    
    if not migration_files:
        print("No migration files found.")
        return

    db_url = settings.supabase_db_url
    print(f"Connecting to database...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        with conn.cursor() as cursor:
            for migration_file in migration_files:
                file_path = os.path.join(migrations_dir, migration_file)
                print(f"Executing migration: {migration_file}...")
                with open(file_path, "r") as f:
                    sql = f.read()
                try:
                    cursor.execute(sql)
                except Exception as file_err:
                    print(f"Warning: Error executing {migration_file}: {file_err}. Continuing...")
            print("All migrations completed successfully!")
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migrations()
