# tools/fix_db_schema.py
import sqlite3
import os

# DBファイルのパス (環境に合わせて調整してください)
DB_PATH = "inheritance.db"

def fix_database():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file '{DB_PATH}' not found.")
        return

    print(f"Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. cases テーブルの現在のカラムを確認
        cursor.execute("PRAGMA table_info(cases)")
        columns = [info[1] for info in cursor.fetchall()]
        print(f"Current columns in 'cases': {columns}")

        # 2. sol_case_number の追加
        if "sol_case_number" not in columns:
            print("Adding missing column: sol_case_number...")
            cursor.execute("ALTER TABLE cases ADD COLUMN sol_case_number TEXT")
            print(" -> Added.")
        else:
            print("Column 'sol_case_number' already exists.")

        # 3. introduction_date の追加 (念のため)
        if "introduction_date" not in columns:
            print("Adding missing column: introduction_date...")
            cursor.execute("ALTER TABLE cases ADD COLUMN introduction_date DATE")
            print(" -> Added.")
        else:
            print("Column 'introduction_date' already exists.")

        conn.commit()
        print("✅ Database schema fixed successfully.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error updating database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_database()