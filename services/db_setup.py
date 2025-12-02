# /services/db_setup.py

import json
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
    func,
    UniqueConstraint
)
from sqlalchemy.orm import (
    Session,
    declarative_base,
    joinedload,
    relationship,
    sessionmaker,
)

from services.task_generation_logic import (
    generate_case_tasks,
    seed_db_users_and_cases,
    setup_task_templates,
)

# --- データベース接続設定 ---
DATABASE_URL = "sqlite:///data/customer_management.db"
Engine = create_engine(DATABASE_URL)
Base = declarative_base()
# セッションクラスを定義
Session = sessionmaker(autocommit=False, autoflush=False, bind=Engine)


def get_db():
    """DBセッションを取得するヘルパー関数"""
    db = Session()
    try:
        yield db
    finally:
        db.close()


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


# 1. 口座種類マスタ (AccountTypeMaster)
class AccountTypeMaster(Base):
    __tablename__ = "account_type_master"
    id = Column(Integer, primary_key=True, index=True)
    type_name = Column(String, unique=True, nullable=False) # 例: 普通預金, 定期預金
    
    financial_assets = relationship("FinancialAsset", back_populates="account_type_ref")

# 2. 銀行マスタ (BankMaster)
class BankMaster(Base):
    __tablename__ = "bank_master"
    id = Column(Integer, primary_key=True, index=True)
    bank_name = Column(String, nullable=False)
    bank_code = Column(String, nullable=False)
    
    # 複合ユニーク制約: 銀行名または銀行コードで一意
    __table_args__ = (UniqueConstraint('bank_name', name='_bank_name_uc'),
                      UniqueConstraint('bank_code', name='_bank_code_uc'))
    
    # 支店と金融資産へのリレーション
    branches = relationship("BranchMaster", back_populates="bank_ref", cascade="all, delete-orphan")
    financial_assets = relationship("FinancialAsset", back_populates="bank_ref")

# 3. 支店マスタ (BranchMaster)
class BranchMaster(Base):
    __tablename__ = "branch_master"
    id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(Integer, ForeignKey("bank_master.id", ondelete="CASCADE"), nullable=False)
    branch_name = Column(String, nullable=False)
    branch_code = Column(String, nullable=False)
    
    # 複合ユニーク制約 (同じ銀行内で支店コードは一意)
    __table_args__ = (UniqueConstraint('bank_id', 'branch_code', name='_bank_branch_code_uc'),)

    bank_ref = relationship("BankMaster", back_populates="branches")
    financial_assets = relationship("FinancialAsset", back_populates="branch_ref")


class DocumentType(Base):
    __tablename__ = "document_types"  # 原本追跡対象書類のマスター
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # 書類名 (例: 戸籍謄本)


class ShippingMethod(Base):
    __tablename__ = "shipping_methods"  # 追跡管理を行う送付方法のマスター
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # 送付方法名 (例: レターパック)
    tracking_base_url = Column(String, nullable=False)  # 追跡URLの基盤
    estimated_days = Column(Integer)  # 標準的な配達所要日数


class SubmissionDocType(Base):
    __tablename__ = "submission_doc_types"  # 顧客提出依頼書類のマスター
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # 書類名 (例: 通帳写し)


# --- 3. 個人情報管理テーブル ---


class Address(Base):
    __tablename__ = "address"  # 住所情報の構成要素
    id = Column(Integer, primary_key=True)
    zip_code = Column(String)  # 郵便番号
    prefecture = Column(String, nullable=False)  # 都道府県
    city_ward_town = Column(String)  # 市区町村
    street_address = Column(String, nullable=False)  # 番地、丁目
    building_name = Column(String)  # 建物名、部屋番号

    deceased_history = relationship(
        "D_AddressHistory", back_populates="address", cascade="all, delete-orphan"
    )
    heir_history = relationship(
        "H_AddressHistory", back_populates="address", cascade="all, delete-orphan"
    )


class Contact(Base):
    __tablename__ = "contact"  # 連絡先本体 (電話番号、メールなど)
    id = Column(Integer, primary_key=True)
    value = Column(String, nullable=False)  # 連絡先の値
    type = Column(String, nullable=False)  # 種別 (PHONE, EMAIL)
    sub_type = Column(String)  # 詳細種別 (自宅、携帯など)


class D_AddressHistory(Base):
    __tablename__ = "d_address_history"  # 被相続人の住所履歴 (中間テーブル)
    id = Column(Integer, primary_key=True)
    deceased_id = Column(Integer, ForeignKey("deceased.id"), nullable=False)  # 被相続人ID
    address_id = Column(Integer, ForeignKey("address.id"), nullable=False)  # 住所ID
    is_last_address = Column(Boolean, nullable=False, default=False)  # 最後の住所フラグ

    deceased = relationship("Deceased", back_populates="address_links")
    address = relationship("Address", back_populates="deceased_history")


class H_AddressHistory(Base):
    __tablename__ = "h_address_history"  # 相続人の住所履歴 (中間テーブル)
    id = Column(Integer, primary_key=True)
    heir_id = Column(Integer, ForeignKey("heirs.id"), nullable=False)  # 相続人ID
    address_id = Column(Integer, ForeignKey("address.id"), nullable=False)  # 住所ID
    is_current_address = Column(Boolean, nullable=False, default=False)  # 現在の住所フラグ

    heir = relationship("Heir", back_populates="address_links")
    address = relationship("Address", back_populates="heir_history")


class D_ContactLink(Base):
    __tablename__ = "d_contact_link"  # 被相続人と連絡先を結ぶ中間テーブル
    id = Column(Integer, primary_key=True)
    deceased_id = Column(Integer, ForeignKey("deceased.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contact.id"), nullable=False)

    deceased = relationship("Deceased", back_populates="contact_links")
    contact = relationship("Contact")


class H_ContactLink(Base):
    __tablename__ = "h_contact_link"  # 相続人と連絡先を結ぶ中間テーブル
    id = Column(Integer, primary_key=True)
    heir_id = Column(Integer, ForeignKey("heirs.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contact.id"), nullable=False)

    heir = relationship("Heir", back_populates="contact_links")
    contact = relationship("Contact")


class CaseContactPoint(Base):
    __tablename__ = "case_contact_points"  # 案件ごとの特別な連絡窓口
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)  # 案件ID
    contact_person_name = Column(String)  # 第三者連絡先氏名
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
    __tablename__ = "cases"  # 遺産整理業務案件のコアハブ
    case_id = Column(Integer, primary_key=True)
    case_number = Column(String, unique=True, nullable=False)  # 案件番号 (G0001)
    folder_path = Column(String)
    client_name = Column(String, nullable=False)  # 依頼者（契約者）名
    client_name_kana = Column(String)  # 依頼者（契約者）ふりがな

    manager_id = Column(Integer, ForeignKey("users.id"))  # 担当1 (進捗管理責任者)
    operator_id = Column(Integer, ForeignKey("users.id"))  # 担当2 (実務担当者)
    current_status_id = Column(Integer, ForeignKey("case_statuses.id"))  # 現在のステータス

    fee_contract_amount = Column(Float, default=0.0)  # 契約時の総報酬額
    deposit_required_amount = Column(Float, default=0.0)
    deposit_paid_amount = Column(Float, default=0.0)
    is_paid_in_full = Column(Boolean, default=False)

    certs_of_seal_count = Column(Integer, default=0)
    power_of_attorney_count = Column(Integer, default=0)

    date_of_death = Column(Date)  # 死亡日
    interview_date = Column(DateTime)  # 面談日時
    contract_date = Column(Date)  # 受託日 (契約締結日)
    tax_deadline = Column(DateTime)  # 相続税申告期限
    created_at = Column(DateTime, default=datetime.now)  # 案件作成日時

    manager = relationship("User", foreign_keys=[manager_id])  # 担当1 Userオブジェクト
    operator = relationship("User", foreign_keys=[operator_id])  # 担当2 Userオブジェクト
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
    __tablename__ = "task_templates"  # 定型タスクの定義マスター
    template_id = Column(Integer, primary_key=True)
    description = Column(String, nullable=False)  # タスク名
    default_due_days = Column(Integer, default=1)  # 契約日からの標準的な期限日数
    is_manager_task = Column(Boolean, default=False)  # 担当1 (Manager) への割り当てフラグ
    depends_on_template_id = Column(Integer, ForeignKey("task_templates.template_id"))

    depends_on = relationship("TaskTemplate", remote_side=[template_id])


class Task(Base):
    __tablename__ = "tasks"  # 実行中の個別のTODOレコード
    task_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)  # 案件ID
    template_id = Column(Integer, ForeignKey("task_templates.template_id"))  # テンプレートID
    description = Column(String, nullable=False)  # 次のアクション名を格納
    last_updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )  # 最終更新日/進捗確認日
    assigned_user_id = Column(Integer, ForeignKey("users.id"))  # 実行担当者ID
    due_date = Column(DateTime)  # 実行期限
    is_completed = Column(Boolean, default=False)  # 完了フラグ

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
    document_type_id = Column(
        Integer, ForeignKey("document_types.id"), nullable=False
    )  # 原本の種類
    shipping_method_id = Column(
        Integer, ForeignKey("shipping_methods.id"), nullable=False
    )  # 送付方法
    sent_date = Column(DateTime, nullable=False)
    sent_to = Column(String, nullable=False)  # 送付先
    tracking_number = Column(String, unique=True)  # 追跡番号
    is_returned = Column(Boolean, default=False)

    document_type = relationship("DocumentType")
    shipping_method = relationship("ShippingMethod")
    task_ref = relationship("Task", back_populates="document_logs")


# --- 6. 個人情報詳細テーブル (Deceased & Heir) ---


class Deceased(Base):
    __tablename__ = "deceased"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False, unique=True)
    name_last = Column(String)  # 姓
    name_first = Column(String)  # 名
    name_last_kana = Column(String)
    name_first_kana = Column(String)
    hometown = Column(String)
    date_of_birth = Column(Date)
    date_of_death = Column(Date)
    relationship_type = Column(String)  # 続柄 (通常は「本人」)
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
    relationship_type = Column(String)  # 続柄（例: 長男、配偶者）
    is_contracting_party = Column(Boolean, default=False)  # 契約者本人であるか

    deceased = relationship("Deceased", back_populates="heirs")
    address_links = relationship(
        "H_AddressHistory", back_populates="heir", cascade="all, delete-orphan"
    )
    contact_links = relationship(
        "H_ContactLink", back_populates="heir", cascade="all, delete-orphan"
    )


# --- 7. 財産・トランザクション詳細テーブル (一部抜粋) ---


class FinancialAsset(Base):
    __tablename__ = "financial_asset"
    
    id = Column(Integer, primary_key=True, index=True) 
    case_id = Column(Integer, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False)
    asset_type = Column(String, default="BANK") 

    # --- 💡 マスタID参照に置き換え ---
    bank_id = Column(Integer, ForeignKey("bank_master.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branch_master.id")) 
    account_type_id = Column(Integer, ForeignKey("account_type_master.id"), nullable=True)
    # ---------------------------------
    
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


# --- DB初期化関数 ---
def init_db():
    Base.metadata.create_all(Engine)


# --- DB操作関数 ---
def add_initial_data():
    session = Session()
    # 既存データの有無に関わらず、マスタデータの不足分を追加するように修正
    # ただし、Case作成などのサンプルデータは初回のみとするため、Caseカウントチェックは残す
    
    # 1. 担当者とステータスの初期登録 (存在チェック付き)
    if not session.query(User).filter_by(windows_id="admin01").first():
        user1 = User(windows_id="admin01", name="管理者 太郎", role="Manager")
        session.add(user1)
    
    if not session.query(CaseStatus).filter_by(name="受託").first():
        status1 = CaseStatus(name="受託", order_num=3)
        session.add(status1)
    
    session.flush()

    # 2. 銀行マスタの初期登録
    if not session.query(BankMaster).filter_by(bank_code="0001").first():
        bank_master = BankMaster(bank_name="みずほ銀行", bank_code="0001")
        session.add(bank_master)
        session.flush()
        
        # 2-2. 支店マスタ
        branch_master = BranchMaster(
            bank_id=bank_master.id,
            branch_name="銀座中央",
            branch_code="050"
        )
        session.add(branch_master)
    
    # 2-3. 口座種類マスタ (拡張)
    initial_account_types = [
        "普通預金",
        "定期預金",
        "当座預金",
        "普通貯金",
        "定期貯金",
        "投資信託",
        "外貨預金"
    ]
    
    for type_name in initial_account_types:
        if not session.query(AccountTypeMaster).filter_by(type_name=type_name).first():
            session.add(AccountTypeMaster(type_name=type_name))
            
    session.commit()

    # 3. サンプル案件データの登録 (初回のみ)
    if session.query(Case).count() == 0:
        # ID再取得
        user1 = session.query(User).filter_by(windows_id="admin01").first()
        status1 = session.query(CaseStatus).filter_by(name="受託").first()
        
        # 案件 (Case: G2103) の登録
        case1 = Case(
            case_number="G2103",
            client_name="水谷 昌代",
            client_name_kana="みずたに　まさよ",
            manager_id=user1.id,
            current_status_id=status1.id,
            contract_date=date(2025, 10, 1),
            fee_contract_amount=500000.0,
            folder_path=r"\\192.168.11.20\行政書士法人チェスター\01.個別ＪＯＢ\G2103水谷昌代様（スタンダードプラン）"
        )
        session.add(case1)
        session.flush()

        # 4. 被相続人 (Deceased: 水谷 弘) の登録
        addr_deceased = Address(
            zip_code="104-0053",
            prefecture="東京都",
            city_ward_town="中央区晴海",
            street_address="二丁目5番16号",
            building_name="1101号",
        )
        session.add(addr_deceased)
        session.flush()
        
        d1 = Deceased(
            case_id=case1.case_id,
            name_last="水谷",
            name_first="弘",
            name_last_kana="みずたに",
            name_first_kana="ひろし",
            date_of_birth=date(1935, 1, 12),
            date_of_death=date(2025, 5, 16),
            hometown="東京都台東区東上野一丁目1番地",
            relationship_type="本人",
            last_address_id=addr_deceased.id
        )
        session.add(d1)
        session.flush()
        
        # 5. 契約者 (Heir: 水谷 昌代, 妻) の登録
        h1 = Heir(
            deceased_id=d1.id,
            name_last="水谷",
            name_first="昌代",
            name_last_kana="みずたに",
            name_first_kana="まさよ",
            relationship_type="妻",
            date_of_birth=date(1946, 11, 29),
            hometown="東京都台東区東上野1-1",
            is_contracting_party=True, # 契約者フラグ
        )
        session.add(h1)
        session.flush()
        
        h1_addr_link = H_AddressHistory(
            heir_id=h1.id, 
            address_id=addr_deceased.id, 
            is_current_address=True
        )
        session.add(h1_addr_link)
        
        contact_phone = Contact(value="03-3533-1675", type="PHONE", sub_type="Primary")
        session.add(contact_phone)
        session.flush()
        
        h1_contact_link = H_ContactLink(heir_id=h1.id, contact_id=contact_phone.id)
        session.add(h1_contact_link)

        # 6. 金融資産 (FinancialAsset) の登録
        # マスタ取得
        bank_master = session.query(BankMaster).filter_by(bank_code="0001").first()
        branch_master = session.query(BranchMaster).filter_by(bank_id=bank_master.id, branch_code="050").first()
        account_type_master = session.query(AccountTypeMaster).filter_by(type_name="普通預金").first()

        if bank_master and branch_master and account_type_master:
            bank1 = FinancialAsset(
                case_id=case1.case_id,
                bank_id=bank_master.id,       
                branch_id=branch_master.id,   
                account_type_id=account_type_master.id, 
                account_number="1234567",
                balance=5000000.0,
                status="調査中",
            )
            session.add(bank1)
        
        # 7. 負債/葬儀費用の登録
        liability1 = Liability(
            case_id=case1.case_id,
            is_debt=False,
            description="葬儀費用",
            amount=2500000.0,
            is_funeral_cost=True,
        )
        session.add(liability1)

        session.commit()
    
    session.close()