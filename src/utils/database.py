# src/utils/database.py
import logging
from typing import Generator
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base, Session

# ログ設定
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# DB接続設定 (SQLite)
# マルチスレッド(Flet)でのアクセスを許可するために check_same_thread=False を設定
DATABASE_URL = "sqlite:///inheritance.db"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()

def init_db() -> None:
    """
    データベースの初期化と、不足カラムの自動マイグレーションを行う。
    OperationalError: no such column を防ぐための処置。
    """
    # テーブルが存在しない場合は作成
    Base.metadata.create_all(bind=engine)
    
    # 既存テーブルへのカラム追加チェック (簡易マイグレーション)
    inspector = inspect(engine)
    
    # cases テーブルが存在するか確認
    if "cases" in inspector.get_table_names():
        existing_columns = [col["name"] for col in inspector.get_columns("cases")]
        
        # エラーの原因となっていた 'sol_case_number' がない場合に追加
        if "sol_case_number" not in existing_columns:
            print("【Migration】: 'cases' テーブルに不足しているカラム 'sol_case_number' を追加します。")
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE cases ADD COLUMN sol_case_number TEXT"))
                conn.commit()
                
        # 今後不足しそうな 'introduction_date' なども念のためチェック
        if "introduction_date" not in existing_columns:
             with engine.connect() as conn:
                conn.execute(text("ALTER TABLE cases ADD COLUMN introduction_date DATE"))
                conn.commit()

def get_db() -> Generator[Session, None, None]:
    """
    DBセッションの依存性注入用ジェネレータ
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()