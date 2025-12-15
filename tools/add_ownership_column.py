# tools/add_ownership_column.py
import os
import sqlite3

# DBファイルのパス (環境に合わせて調整してください)
DB_PATH = "database.sqlite"


def add_column():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file '{DB_PATH}' not found.")
        return

    print(f"Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 現在のカラムを確認
        cursor.execute("PRAGMA table_info(real_estate_assets)")
        columns = [info[1] for info in cursor.fetchall()]
        print(f"Current columns: {columns}")

        # ownership_share がなければ追加
        if "ownership_share" not in columns:
            print("Adding column 'ownership_share'...")
            cursor.execute("ALTER TABLE real_estate_assets ADD COLUMN ownership_share TEXT")
            conn.commit()
            print("✅ Column added successfully.")
        else:
            print("ℹ️ Column already exists.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    add_column()
