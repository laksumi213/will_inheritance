# src/models/tables.py
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.models.database import Base

# --- 2. マスタテーブル (Master Data) ---


class User(Base):
    __tablename__ = "users"  # 担当者（アプリケーション利用者）
    id = Column(Integer, primary_key=True)
    windows_id = Column(String, unique=True, nullable=False)  # 認証キー
    role = Column(String, default="Operator")  # 役割 (Manager: 担当1, Operator: 担当2)
    name = Column(String, nullable=False)  # 担当者名


class CaseStatus(Base):
    __tablename__ = "case_statuses"  # 案件の進捗ステータス
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # ステータス名 (例: 受託)
    order_num = Column(Integer)  # ステータスの表示/処理順序


# 1. 口座種類マスタ
class AccountTypeMaster(Base):
    __tablename__ = "account_type_master"
    id = Column(Integer, primary_key=True, index=True)
    type_name = Column(String, unique=True, nullable=False)  # 例: 普通預金

    financial_assets = relationship("FinancialAsset", back_populates="account_type_ref")


# 2. 銀行マスタ
class BankMaster(Base):
    __tablename__ = "bank_master"
    id = Column(Integer, primary_key=True, index=True)
    bank_name = Column(String, nullable=False)
    bank_code = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("bank_name", name="_bank_name_uc"),
        UniqueConstraint("bank_code", name="_bank_code_uc"),
    )

    branches = relationship("BranchMaster", back_populates="bank_ref", cascade="all, delete-orphan")
    financial_assets = relationship("FinancialAsset", back_populates="bank_ref")


# 3. 支店マスタ
class BranchMaster(Base):
    __tablename__ = "branch_master"
    id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(Integer, ForeignKey("bank_master.id", ondelete="CASCADE"), nullable=False)
    branch_name = Column(String, nullable=False)
    branch_code = Column(String, nullable=False)

    __table_args__ = (UniqueConstraint("bank_id", "branch_code", name="_bank_branch_code_uc"),)

    bank_ref = relationship("BankMaster", back_populates="branches")
    financial_assets = relationship("FinancialAsset", back_populates="branch_ref")


class DocumentType(Base):
    __tablename__ = "document_types"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


class ShippingMethod(Base):
    __tablename__ = "shipping_methods"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    tracking_base_url = Column(String, nullable=False)
    estimated_days = Column(Integer)


class SubmissionDocType(Base):
    __tablename__ = "submission_doc_types"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


# --- 3. 個人情報管理テーブル ---


class Address(Base):
    __tablename__ = "address"
    id = Column(Integer, primary_key=True)
    zip_code = Column(String)
    prefecture = Column(String, nullable=False)
    city_ward_town = Column(String)
    street_address = Column(String, nullable=False)
    building_name = Column(String)

    deceased_history = relationship(
        "D_AddressHistory", back_populates="address", cascade="all, delete-orphan"
    )
    heir_history = relationship(
        "H_AddressHistory", back_populates="address", cascade="all, delete-orphan"
    )


class Contact(Base):
    __tablename__ = "contact"
    id = Column(Integer, primary_key=True)
    value = Column(String, nullable=False)
    type = Column(String, nullable=False)  # PHONE, EMAIL
    sub_type = Column(String)


class D_AddressHistory(Base):
    __tablename__ = "d_address_history"
    id = Column(Integer, primary_key=True)
    deceased_id = Column(Integer, ForeignKey("deceased.id"), nullable=False)
    address_id = Column(Integer, ForeignKey("address.id"), nullable=False)
    is_last_address = Column(Boolean, nullable=False, default=False)

    deceased = relationship("Deceased", back_populates="address_links")
    address = relationship("Address", back_populates="deceased_history")


class H_AddressHistory(Base):
    __tablename__ = "h_address_history"
    id = Column(Integer, primary_key=True)
    heir_id = Column(Integer, ForeignKey("heirs.id"), nullable=False)
    address_id = Column(Integer, ForeignKey("address.id"), nullable=False)
    is_current_address = Column(Boolean, nullable=False, default=False)

    heir = relationship("Heir", back_populates="address_links")
    address = relationship("Address", back_populates="heir_history")


class D_ContactLink(Base):
    __tablename__ = "d_contact_link"
    id = Column(Integer, primary_key=True)
    deceased_id = Column(Integer, ForeignKey("deceased.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contact.id"), nullable=False)

    deceased = relationship("Deceased", back_populates="contact_links")
    contact = relationship("Contact")


class H_ContactLink(Base):
    __tablename__ = "h_contact_link"
    id = Column(Integer, primary_key=True)
    heir_id = Column(Integer, ForeignKey("heirs.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contact.id"), nullable=False)

    heir = relationship("Heir", back_populates="contact_links")
    contact = relationship("Contact")


class CaseContactPoint(Base):
    __tablename__ = "case_contact_points"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    contact_person_name = Column(String)
    relationship_to_client = Column(String)
    address_id = Column(Integer, ForeignKey("address.id"))
    contact_id = Column(Integer, ForeignKey("contact.id"))

    is_primary_contact = Column(Boolean, default=False)
    is_primary_mail_send_destination = Column(Boolean, default=False)

    case_ref = relationship("Case", back_populates="contact_points")
    address_ref = relationship("Address")
    contact_ref = relationship("Contact")


# --- 4. 案件ハブテーブル (Core Case Management) ---


class Case(Base):
    __tablename__ = "cases"
    case_id = Column(Integer, primary_key=True)
    case_number = Column(String, unique=True, nullable=False)  # G0001
    folder_path = Column(String)
    client_name = Column(String, nullable=False)
    client_name_kana = Column(String)

    manager_id = Column(Integer, ForeignKey("users.id"))
    operator_id = Column(Integer, ForeignKey("users.id"))
    current_status_id = Column(Integer, ForeignKey("case_statuses.id"))

    fee_contract_amount = Column(Float, default=0.0)
    deposit_required_amount = Column(Float, default=0.0)
    deposit_paid_amount = Column(Float, default=0.0)
    is_paid_in_full = Column(Boolean, default=False)

    certs_of_seal_count = Column(Integer, default=0)
    power_of_attorney_count = Column(Integer, default=0)

    # 日付関連
    date_of_death = Column(Date)
    interview_date = Column(DateTime)
    contract_date = Column(Date)
    tax_deadline = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)

    # --- 新規追加カラム (紹介情報・SOL連携) ---
    sol_case_number = Column(String, nullable=True, comment="SOL案件No")
    introduction_date = Column(Date, nullable=True, comment="紹介日")
    referral_sec_branch_name = Column(String, nullable=True, comment="証券会社支店名")
    referral_sec_rep_name = Column(String, nullable=True, comment="証券会社担当者名")
    consent_date = Column(Date, nullable=True, comment="同意書日付")

    # リレーション定義
    manager = relationship("User", foreign_keys=[manager_id])
    operator = relationship("User", foreign_keys=[operator_id])
    status_ref = relationship("CaseStatus")

    deceased_ref = relationship(
        "Deceased", back_populates="case", uselist=False, cascade="all, delete-orphan"
    )
    financial_assets = relationship(
        "FinancialAsset", back_populates="case_ref", cascade="all, delete-orphan"
    )
    real_estates = relationship(
        "RealEstateAsset", back_populates="case_ref", cascade="all, delete-orphan"
    )
    tasks = relationship("Task", back_populates="case_ref", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="case_ref", cascade="all, delete-orphan")
    submitted_docs = relationship(
        "CaseSubmissionDoc", back_populates="case_ref", cascade="all, delete-orphan"
    )
    contact_logs = relationship(
        "ContactLog", back_populates="case_ref", cascade="all, delete-orphan"
    )
    insurance_assets = relationship(
        "InsuranceAsset", back_populates="case_ref", cascade="all, delete-orphan"
    )
    other_assets = relationship(
        "OtherAsset", back_populates="case_ref", cascade="all, delete-orphan"
    )
    liabilities = relationship("Liability", back_populates="case_ref", cascade="all, delete-orphan")
    contact_points = relationship(
        "CaseContactPoint", back_populates="case_ref", cascade="all, delete-orphan"
    )


# --- 5. タスクテンプレートと実行タスクモデル ---


class TaskTemplate(Base):
    __tablename__ = "task_templates"
    template_id = Column(Integer, primary_key=True)
    description = Column(String, nullable=False)
    default_due_days = Column(Integer, default=1)
    is_manager_task = Column(Boolean, default=False)
    depends_on_template_id = Column(Integer, ForeignKey("task_templates.template_id"))

    depends_on = relationship("TaskTemplate", remote_side=[template_id])


class Task(Base):
    __tablename__ = "tasks"
    task_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    template_id = Column(Integer, ForeignKey("task_templates.template_id"))
    description = Column(String, nullable=False)
    last_updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    assigned_user_id = Column(Integer, ForeignKey("users.id"))
    due_date = Column(DateTime)
    is_completed = Column(Boolean, default=False)

    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    template_ref = relationship("TaskTemplate")
    document_logs = relationship(
        "TaskDocumentLog", back_populates="task_ref", cascade="all, delete-orphan"
    )
    case_ref = relationship("Case", back_populates="tasks")


class TaskDocumentLog(Base):
    __tablename__ = "task_document_logs"
    log_id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.task_id"), nullable=False)
    document_type_id = Column(Integer, ForeignKey("document_types.id"), nullable=False)
    shipping_method_id = Column(Integer, ForeignKey("shipping_methods.id"), nullable=False)
    sent_date = Column(DateTime, nullable=False)
    sent_to = Column(String, nullable=False)
    tracking_number = Column(String, unique=True)
    is_returned = Column(Boolean, default=False)

    document_type = relationship("DocumentType")
    shipping_method = relationship("ShippingMethod")
    task_ref = relationship("Task", back_populates="document_logs")


# --- 6. 個人情報詳細テーブル (Deceased & Heir) ---


class Deceased(Base):
    __tablename__ = "deceased"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False, unique=True)
    name_last = Column(String)
    name_first = Column(String)
    name_last_kana = Column(String)
    name_first_kana = Column(String)
    hometown = Column(String)
    date_of_birth = Column(Date)
    date_of_death = Column(Date)
    relationship_type = Column(String)
    last_address_id = Column(Integer, ForeignKey("address.id"))

    heirs = relationship("Heir", back_populates="deceased", cascade="all, delete-orphan")
    address_links = relationship(
        "D_AddressHistory", back_populates="deceased", cascade="all, delete-orphan"
    )
    contact_links = relationship(
        "D_ContactLink", back_populates="deceased", cascade="all, delete-orphan"
    )
    case = relationship("Case", back_populates="deceased_ref")
    last_address = relationship("Address", foreign_keys=[last_address_id])


class Heir(Base):
    __tablename__ = "heirs"
    id = Column(Integer, primary_key=True)
    deceased_id = Column(Integer, ForeignKey("deceased.id"), nullable=False)
    name_last = Column(String, nullable=False)
    name_first = Column(String)
    name_last_kana = Column(String)
    name_first_kana = Column(String)
    hometown = Column(String)
    date_of_birth = Column(Date)
    date_of_death = Column(Date)
    relationship_type = Column(String)
    is_contracting_party = Column(Boolean, default=False)

    deceased = relationship("Deceased", back_populates="heirs")
    address_links = relationship(
        "H_AddressHistory", back_populates="heir", cascade="all, delete-orphan"
    )
    contact_links = relationship(
        "H_ContactLink", back_populates="heir", cascade="all, delete-orphan"
    )


# --- 7. 財産・トランザクション詳細テーブル ---


class FinancialAsset(Base):
    __tablename__ = "financial_asset"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False)
    asset_type = Column(String, default="BANK")

    bank_id = Column(Integer, ForeignKey("bank_master.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branch_master.id"))
    account_type_id = Column(Integer, ForeignKey("account_type_master.id"), nullable=True)

    account_number = Column(String)
    balance = Column(Float, default=0.0)
    status = Column(String, default="未確認")

    case_ref = relationship("Case", back_populates="financial_assets")
    bank_ref = relationship("BankMaster", back_populates="financial_assets")
    branch_ref = relationship("BranchMaster", back_populates="financial_assets")
    account_type_ref = relationship("AccountTypeMaster", back_populates="financial_assets")


class RealEstateAsset(Base):
    __tablename__ = "real_estate_assets"
    real_estate_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    municipality_name = Column(String, nullable=False)

    case_ref = relationship("Case", back_populates="real_estates")


class Liability(Base):
    __tablename__ = "liability"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    is_debt = Column(Boolean, nullable=False, default=True)
    description = Column(String)
    amount = Column(Float, nullable=False)
    is_funeral_cost = Column(Boolean, nullable=False, default=False)

    case_ref = relationship("Case", back_populates="liabilities")


class InsuranceAsset(Base):
    __tablename__ = "insurance_assets"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    insurance_company = Column(String)
    policy_number = Column(String)
    estimated_value = Column(Float)

    case_ref = relationship("Case", back_populates="insurance_assets")


class OtherAsset(Base):
    __tablename__ = "other_assets"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    description = Column(String)
    estimated_value = Column(Float)

    case_ref = relationship("Case", back_populates="other_assets")


class Expense(Base):
    __tablename__ = "expenses"
    expense_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    description = Column(String)
    amount = Column(Float, nullable=False)
    expense_date = Column(Date)

    case_ref = relationship("Case", back_populates="expenses")


class ContactLog(Base):
    __tablename__ = "contact_logs"
    log_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    contact_content = Column(String, nullable=False)
    is_thank_you_payment = Column(Boolean, default=False)

    case_ref = relationship("Case", back_populates="contact_logs")


class CaseSubmissionDoc(Base):
    __tablename__ = "case_submission_docs"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)

    case_ref = relationship("Case", back_populates="submitted_docs")


# --- 8. PDF座標管理用テーブル (新規追加) ---


class Coordinate(Base):
    """PDF印字用の座標データモデル"""

    __tablename__ = "coordinates"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, nullable=False, comment="項目名")
    x_point = Column(Float, nullable=False, comment="X座標")
    y_point = Column(Float, nullable=False, comment="Y座標")
    value = Column(String, nullable=True, comment="テスト値")
    description = Column(String, nullable=True, comment="備考")