# tools/rebuild_tables.py
import sys
import os

# プロジェクトのルートディレクトリをパスに追加して、srcモジュールを読み込めるようにする
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    # あなたの環境に合わせてインポートを試行します
    # パターンA: 共有いただいた deceased_service.py の構成
    from src.models.database import engine, Base
    from src.models import tables  # テーブル定義(Caseクラス等)を読み込み
    print("Imported from src.models.database & tables")
except ImportError:
    # パターンB: 私が以前提案した src/utils/database.py の構成
    from src.utils.database import engine, Base
    from src.models import models as tables
    print("Imported from src.utils.database & models")

def rebuild_database():
    print("🔄 Starting database rebuild...")
    
    # 1. 念のため既存のテーブルを全て削除（クリーンな状態にする）
    print("1. Dropping existing tables (if any)...")
    Base.metadata.drop_all(bind=engine)
    
    # 2. テーブルを新規作成
    # ここで tables.py に定義されている最新の構成（sol_case_number付き）で作成されます
    print("2. Creating new tables...")
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database tables created successfully!")

if __name__ == "__main__":
    rebuild_database()