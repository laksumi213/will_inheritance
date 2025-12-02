# /services/db_setup.py

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# データベースエンジンの設定
DATABASE_URL = "sqlite:///data/customer_management.db"
Engine = create_engine(DATABASE_URL, echo=False)
Base = declarative_base()
Session = sessionmaker(bind=Engine)


# --- 1. マスタテーブル (Master Data) ---


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    windows_id = Column(String, unique=True, nullable=False)
    role = Column(String, default="Operator")
    name = Column(String, nullable=False)


class CaseStatus(Base):
    __tablename__ = "case_statuses"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    order_num = Column(Integer)


class FinancialInstitution(Base):
    __tablename__ = "institutions"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


class DocumentType(Base):
    __tablename__ = "document_types"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


class ShippingMethod(Base):
    __tablename__ = "shipping_methods"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    tracking_base_url = Column(String)
    estimated_days = Column(Integer)


class SubmissionDocType(Base):
    __tablename__ = "submission_doc_types"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


# --- 2. 住所・連絡先マスタ ---


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
    type = Column(String, nullable=False)
    sub_type = Column(String)


# --- 3. 案件ハブテーブル (Core Case Management) ---


class Case(Base):
    __tablename__ = "cases"
    case_id = Column(Integer, primary_key=True)
    case_number = Column(String, unique=True, nullable=False)
    client_name = Column(String, nullable=False)
    deceased_name = Column(String)

    manager_id = Column(Integer, ForeignKey("users.id"))
    operator_id = Column(Integer, ForeignKey("users.id"))
    current_status_id = Column(Integer, ForeignKey("case_statuses.id"))
    date_of_death = Column(Date)
    interview_date = Column(DateTime)
    contract_date = Column(Date)
    tax_deadline = Column(DateTime)
    certs_of_seal_count = Column(Integer, default=0)
    fee_contract_amount = Column(Float, default=0.0)
    is_paid_in_full = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    manager = relationship("User", foreign_keys=[manager_id])
    operator = relationship("User", foreign_keys=[operator_id])
    status_ref = relationship("CaseStatus")
    deceased_ref = relationship(
        "Deceased", backref="case", uselist=False, cascade="all, delete-orphan"
    )
    financial_assets = relationship(
        "FinancialAsset", backref="case", cascade="all, delete-orphan"
    )
    real_estates = relationship(
        "RealEstateAsset", backref="case", cascade="all, delete-orphan"
    )
    tasks = relationship("Task", backref="case", cascade="all, delete-orphan")
    expenses = relationship("Expense", backref="case", cascade="all, delete-orphan")
    submitted_docs = relationship(
        "CaseSubmissionDoc", backref="case", cascade="all, delete-orphan"
    )
    contact_logs = relationship(
        "ContactLog", backref="case", cascade="all, delete-orphan"
    )
    insurance_assets = relationship(
        "InsuranceAsset", backref="case", cascade="all, delete-orphan"
    )
    other_assets = relationship(
        "OtherAsset", backref="case", cascade="all, delete-orphan"
    )
    liabilities = relationship(
        "Liability", backref="case", cascade="all, delete-orphan"
    )


# --- 4. 個人情報詳細テーブル (Deceased & Heir) ---


class Deceased(Base):
    __tablename__ = "deceased"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False, unique=True)

    name_last = Column(String, nullable=False)
    name_first = Column(String)
    name_last_kana = Column(String)
    name_first_kana = Column(String)
    hometown = Column(String)
    date_of_birth = Column(Date)
    date_of_death = Column(Date)
    relationship_type = Column(String)

    heirs = relationship(
        "Heir", back_populates="deceased", cascade="all, delete-orphan"
    )
    address_links = relationship(
        "D_AddressHistory", back_populates="deceased", cascade="all, delete-orphan"
    )
    contact_links = relationship(
        "D_ContactLink", back_populates="deceased", cascade="all, delete-orphan"
    )


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
    relationship_type = Column(String, nullable=False)

    deceased = relationship("Deceased", back_populates="heirs")
    address_links = relationship(
        "H_AddressHistory", back_populates="heir", cascade="all, delete-orphan"
    )
    contact_links = relationship(
        "H_ContactLink", back_populates="heir", cascade="all, delete-orphan"
    )


# 4-1. 住所・連絡先リンク履歴テーブル (中間テーブル)


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


# --- 5. 財産・トランザクション詳細テーブル (一部抜粋) ---


class FinancialAsset(Base):
    __tablename__ = "financial_assets"
    asset_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    inst_id = Column(Integer, ForeignKey("institutions.id"))

    bank_name = Column(String)
    account_number = Column(String)
    balance = Column(Float, default=0.0)
    status = Column(String, default="調査中")


class RealEstateAsset(Base):
    __tablename__ = "real_estate_assets"
    real_estate_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    municipality_name = Column(String, nullable=False)
    is_registration_complete = Column(Boolean, nullable=False, default=False)


class InsuranceAsset(Base):
    __tablename__ = "insurance_asset"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    company_name = Column(String, nullable=False)
    policy_type = Column(String, nullable=False)


class OtherAsset(Base):
    __tablename__ = "other_asset"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    asset_type = Column(String, nullable=False)
    estimated_value = Column(Float)


class Liability(Base):
    __tablename__ = "liability"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    is_debt = Column(Boolean, nullable=False, default=True)
    amount = Column(Float, nullable=False)
    is_funeral_cost = Column(Boolean, nullable=False, default=False)


class Task(Base):
    __tablename__ = "tasks"
    task_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    is_completed = Column(Boolean, default=False)


class TaskDocumentLog(Base):
    __tablename__ = "task_document_logs"
    log_id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.task_id"), nullable=False)


class Expense(Base):
    __tablename__ = "expenses"
    expense_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)


class ContactLog(Base):
    __tablename__ = "contact_logs"
    log_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)


class CaseSubmissionDoc(Base):
    __tablename__ = "case_submission_docs"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)


# --- DB操作関数 ---


def init_db():
    Base.metadata.create_all(Engine)


def add_initial_data():
    session = Session()
    if session.query(Case).count() == 0:
        user1 = User(windows_id="admin01", name="管理者 太郎", role="Manager")
        status1 = CaseStatus(name="受託", order_num=3)
        session.add_all([user1, status1])
        session.flush()

        case1 = Case(
            case_number="2025-001",
            client_name="山田 花子",
            deceased_name="山田 太郎",
            manager_id=user1.id,
            current_status_id=status1.id,
            contract_date=date(2025, 10, 1),
            fee_contract_amount=500000.0,
        )
        session.add(case1)
        session.flush()

        d1 = Deceased(
            case_id=case1.case_id,
            name_last="山田",
            name_first="太郎",
            date_of_birth=date(1950, 1, 1),
            date_of_death=date(2020, 3, 15),
            hometown="東京都港区",
            relationship_type="本人",
        )
        session.add(d1)
        session.flush()

        addr1 = Address(
            zip_code="100-0001",
            prefecture="東京都",
            city_ward_town="千代田区",
            street_address="丸の内1-1",
            building_name="中央ビル101",
        )
        session.add(addr1)
        session.flush()

        d1_addr_link = D_AddressHistory(
            deceased_id=d1.id, address_id=addr1.id, is_last_address=True
        )
        session.add(d1_addr_link)

        h1 = Heir(
            deceased_id=d1.id,
            name_last="山田",
            name_first="一郎",
            relationship_type="長男",
            date_of_birth=date(1980, 5, 10),
        )
        session.add(h1)

        contact_mobile = Contact(value="090-1111-2222", type="PHONE", sub_type="携帯")
        session.add(contact_mobile)
        session.flush()

        h1_contact_link = H_ContactLink(heir_id=h1.id, contact_id=contact_mobile.id)
        session.add(h1_contact_link)

        bank1 = FinancialAsset(
            case_id=case1.case_id,
            bank_name="みずほ銀行",
            account_number="1234567",
            balance=5000000.0,
            status="手続き中",
        )
        liability1 = Liability(
            case_id=case1.case_id,
            is_debt=False,
            description="葬儀費用",
            amount=2500000.0,
            is_funeral_cost=True,
        )
        session.add_all([bank1, liability1])

        session.commit()
    session.close()


import json

from sqlalchemy.orm import joinedload


def get_all_records(model_class):
    session = Session()
    if model_class.__name__ == "Heir":
        records = (
            session.query(model_class)
            .options(joinedload(model_class.address_links))
            .options(joinedload(model_class.contact_links))
            .all()
        )
    else:
        records = session.query(model_class).all()

    results = []
    for record in records:
        data = {}
        for column in record.__table__.columns:
            value = getattr(record, column.name)
            if isinstance(value, (date, datetime)):
                data[column.name] = str(value)
            else:
                data[column.name] = value

        if model_class.__name__ == "Heir":
            # 住所情報（H_AddressHistory & Address）
            addresses = []
            for addr_link in record.address_links:
                address_data = session.query(Address).get(addr_link.address_id)
                address_detail = {
                    "is_current": addr_link.is_current_address,
                    "zip_code": address_data.zip_code,
                    "address_full": f"{address_data.prefecture}{address_data.city_ward_town}{address_data.street_address} {address_data.building_name or ''}".strip(),
                }
                addresses.append(address_detail)
            data["addresses"] = addresses

            # 連絡先情報（H_ContactLink & Contact）
            contacts = []
            for contact_link in record.contact_links:
                contact_data = session.query(Contact).get(contact_link.contact_id)
                contacts.append(
                    {
                        "type": contact_data.type,
                        "sub_type": contact_data.sub_type,
                        "value": contact_data.value,
                    }
                )
            data["contacts"] = contacts

        results.append(data)

    session.close()
    return results


def display_records_pretty(model_class):
    records = get_all_records(model_class)
    print(f"\n===== {model_class.__name__} Table ({len(records)} records) =====")
    pretty_json = json.dumps(records, indent=2, ensure_ascii=False)
    print(pretty_json)
    print("=======================================\n")
