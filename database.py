# database.py

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

# データベースエンジンの設定
DATABASE_URL = "sqlite:///customer_management.db"
Engine = create_engine(DATABASE_URL, echo=True)
Base = declarative_base()


# 被相続人モデル
class Deceased(Base):
    __tablename__ = 'deceased'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    date_of_birth = Column(String)  # 簡易化のためString

    # 相続人とのリレーションシップを定義 (一対多)
    heirs = relationship("Heir", back_populates="deceased", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Deceased(id={self.id}, name='{self.name}')>"


# 相続人モデル
class Heir(Base):
    __tablename__ = 'heirs'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    relationship_name = Column(String)  # 被相続人との続柄

    # 外部キー
    deceased_id = Column(Integer, ForeignKey('deceased.id'))

    # 被相続人とのリレーションシップを定義
    deceased = relationship("Deceased", back_populates="heirs")

    def __repr__(self):
        return f"<Heir(id={self.id}, name='{self.name}', deceased_id={self.deceased_id})>"


# テーブルの作成
def init_db():
    Base.metadata.create_all(Engine)


# セッションの作成
Session = sessionmaker(bind=Engine)


# 初期データ投入（テスト用）
def add_initial_data():
    session = Session()
    if session.query(Deceased).count() == 0:
        d1 = Deceased(name="山田 太郎", date_of_birth="1950-01-01")
        h1 = Heir(name="山田 一郎", relationship_name="長男")
        h2 = Heir(name="山田 花子", relationship_name="長女")

        d1.heirs.extend([h1, h2])
        session.add(d1)
        session.commit()
    session.close()


if __name__ == '__main__':
    init_db()
    add_initial_data()
    print("データベース初期化完了。")