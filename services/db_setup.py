# /services/db_setup.py

from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

# データベースエンジンの設定
DATABASE_URL = "sqlite:///data/customer_management.db"
Engine = create_engine(
    DATABASE_URL, echo=False
)  # echoをFalseにしてmain.pyのログを減らす
Base = declarative_base()
Session = sessionmaker(bind=Engine)  # セッションファクトリの定義


# --- モデル定義 (Entity) ---


class Deceased(Base):
    __tablename__ = "deceased"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    date_of_birth = Column(String)
    heirs = relationship(
        "Heir", back_populates="deceased", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Deceased(id={self.id}, name='{self.name}')>"


class Heir(Base):
    __tablename__ = "heirs"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    relationship_name = Column(String)
    deceased_id = Column(Integer, ForeignKey("deceased.id"))
    deceased = relationship("Deceased", back_populates="heirs")

    def __repr__(self):
        return (
            f"<Heir(id={self.id}, name='{self.name}', deceased_id={self.deceased_id})>"
        )


# --- DB操作関数 ---


def init_db():
    Base.metadata.create_all(Engine)


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


# 注意: Engine, Session, Deceased, Heir は外部からインポートして利用されます
