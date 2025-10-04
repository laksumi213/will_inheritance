from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, Mapped
from typing import List
from db_config import Base


# 被相続人モデル
class Decedent(Base):
    __tablename__ = "decedents"

    # Mapped[型] = Column(...) の形で記述
    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String, index=True)
    death_date: Mapped[str] = Column(String)

    # 相続人とのリレーション
    # relationship() の結果を Mapped[List["Heir"]] に代入します
    heirs: Mapped[List["Heir"]] = relationship("Heir", back_populates="decedent", cascade="all, delete-orphan")


# 相続人モデル
class Heir(Base):
    __tablename__ = "heirs"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    decedent_id: Mapped[int] = Column(Integer, ForeignKey("decedents.id"))
    name: Mapped[str] = Column(String)
    relationship_name: Mapped[str] = Column(String)  # 'relationship'は予約語と紛らわしいため、'relationship_name'などに変更推奨

    # 被相続人とのリレーション
    # relationship() の結果を Mapped["Decedent"] に代入します
    decedent: Mapped["Decedent"] = relationship("Decedent", back_populates="heirs")