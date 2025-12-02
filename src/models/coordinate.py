# models/coordinate.py
from sqlalchemy import Column, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ベースクラスの作成
Base = declarative_base()


class Coordinate(Base):
    """
    PDF上の入力座標を管理するデータモデル
    """

    __tablename__ = "coordinates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String, nullable=False, comment="項目名（例: 被相続人氏名）")
    page_number = Column(Integer, default=1, comment="ページ番号")
    x_point = Column(Float, nullable=False, comment="X座標")
    y_point = Column(Float, nullable=False, comment="Y座標")
    value = Column(String, nullable=True, comment="テスト用入力値")

    def __repr__(self):
        return f"<Coordinate(label='{self.label}', x={self.x_point}, y={self.y_point})>"


# DB初期化設定 (SQLite)
# 実際の接続セッション管理はService層で行うか、ここからFactoryを提供する形にします
DB_PATH = "sqlite:///inheritance_app.db"
engine = create_engine(DB_PATH, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """データベースとテーブルの作成"""
    Base.metadata.create_all(engine)
