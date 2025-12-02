# src/models/base.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from src.config import settings

# データベースエンジンの作成
# check_same_thread=False はSQLiteをFlet(スレッド)で使用するために必要
engine = create_engine(
    f"sqlite:///{settings.DB_PATH}", echo=False, connect_args={"check_same_thread": False}
)

# セッション作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# モデルの基底クラス
Base = declarative_base()


def get_db():
    """DBセッションを取得するジェネレータ (Dependency Injection用)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """テーブルを作成する"""
    try:
        Base.metadata.create_all(bind=engine)
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database initialization failed: {e}")
