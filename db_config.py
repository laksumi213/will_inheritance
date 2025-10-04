from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLiteデータベースファイルのパス
DATABASE_URL = "sqlite:///data/customer_data.db"

# SQLAlchemyエンジンの作成
engine = create_engine(DATABASE_URL, echo=True) # echo=Trueで実行されるSQLログを出力

# Baseの作成（モデルクラスの基底クラス）
Base = declarative_base()

# セッションファクトリの作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    セッションを取得するジェネレーター。
    with文での使用を想定し、確実にクローズする。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_database():
    """データベースとテーブルを作成（models.pyで定義されたもの）"""
    import os
    os.makedirs('data', exist_ok=True)
    Base.metadata.create_all(bind=engine)

# データベースの初期化を main.py で呼び出す