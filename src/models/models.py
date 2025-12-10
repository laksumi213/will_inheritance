# src/models/models.py
from datetime import date, datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship, Mapped
from src.utils.database import Base

class Case(Base):
    """
    相続案件管理モデル
    """
    __tablename__ = "cases"

    case_id: int = Column(Integer, primary_key=True, index=True)
    case_number: str = Column(String, unique=True, index=True, comment="案件管理番号")
    sol_case_number: str = Column(String, nullable=True, comment="司法書士案件番号(SOL)") # 今回のエラー箇所
    
    folder_path: str = Column(String, nullable=True)
    client_name: str = Column(String, nullable=False)
    client_name_kana: str = Column(String, nullable=True)
    
    manager_id: int = Column(Integer, index=True) # 担当マネージャーID
    operator_id: int = Column(Integer, index=True) # 作業担当者ID
    
    current_status_id: int = Column(Integer, ForeignKey("case_statuses.id"), nullable=True)
    
    # 金額関連
    fee_contract_amount: float = Column(Float, default=0.0)
    deposit_required_amount: float = Column(Float, default=0.0)
    deposit_paid_amount: float = Column(Float, default=0.0)
    is_paid_in_full: bool = Column(Boolean, default=False)
    
    # 書類枚数
    certs_of_seal_count: int = Column(Integer, default=0)
    power_of_attorney_count: int = Column(Integer, default=0)
    
    # 日付関連
    date_of_death: date = Column(Date, nullable=True)
    interview_date: date = Column(Date, nullable=True)
    contract_date: date = Column(Date, nullable=True)
    tax_deadline: date = Column(Date, nullable=True)
    introduction_date: date = Column(Date, nullable=True)
    consent_date: date = Column(Date, nullable=True)
    
    # 紹介元情報
    referral_sec_branch_name: str = Column(String, nullable=True)
    referral_sec_rep_name: str = Column(String, nullable=True)
    
    created_at: datetime = Column(DateTime, default=datetime.now)

    # リレーション定義
    status = relationship("CaseStatus", back_populates="cases")
    deceased_list = relationship("Deceased", back_populates="case")

class CaseStatus(Base):
    """案件ステータスマスタ"""
    __tablename__ = "case_statuses"
    
    id: int = Column(Integer, primary_key=True)
    name: str = Column(String, unique=True)
    order_num: int = Column(Integer, default=0)
    
    cases = relationship("Case", back_populates="status")

class Deceased(Base):
    """被相続人（故人）情報"""
    __tablename__ = "deceased"
    
    id: int = Column(Integer, primary_key=True)
    case_id: int = Column(Integer, ForeignKey("cases.case_id"))
    
    name_last: str = Column(String)
    name_first: str = Column(String)
    name_last_kana: str = Column(String)
    name_first_kana: str = Column(String)
    hometown: str = Column(String)
    date_of_birth: date = Column(Date)
    date_of_death: date = Column(Date)
    relationship_type: str = Column(String)
    last_address_id: int = Column(Integer)
    
    case = relationship("Case", back_populates="deceased_list")