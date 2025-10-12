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

# --- データベース接続設定 ---
# 指定されたデータベースファイルパスを使用
DATABASE_URL = "sqlite:///data/customer_management.db"
Engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(autocommit=False, autoflush=False, bind=Engine)


def get_db():
    """DBセッションを取得するヘルパー関数"""
    db = Session()
    try:
        return db
    finally:
        db.close()


# --- 2. マスタテーブル (Master Data) ---


class User(Base):
    __tablename__ = "users"
    # 【役割】 アプリケーションの利用者（担当1・担当2・管理者）のマスター情報
    id = Column(Integer, primary_key=True)
    windows_id = Column(
        String, unique=True, nullable=False
    )  # Windowsログインアカウント名 (認証キー)
    role = Column(String, default="Operator")  # 役割 (Manager:担当1, Operator:担当2)
    name = Column(String, nullable=False)  # 担当者名（フルネーム）


class CaseStatus(Base):
    __tablename__ = "case_statuses"
    # 【役割】 案件が受託に至るまでの進捗ステータスを管理（例: 面談調整中, 受託）
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # ステータス名
    order_num = Column(Integer)  # ステータスの表示順/処理順


class FinancialInstitution(Base):
    __tablename__ = "institutions"
    # 【役割】 金融機関名のマスタ情報（表記ゆれ防止）
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


class DocumentType(Base):
    __tablename__ = "document_types"
    # 【役割】 原本追跡の対象となる書類の種類マスタ (例: 印鑑登録証明書, 戸籍謄本)
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


class ShippingMethod(Base):
    __tablename__ = "shipping_methods"
    # 【役割】 追跡管理を行う送付方法のマスタ（追跡URL自動生成の元データ）
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # 簡易書留, レターパックプラス
    tracking_base_url = Column(String, nullable=False)  # 追跡URLの基盤
    estimated_days = Column(Integer)  # 標準的な配達所要日数


class SubmissionDocType(Base):
    __tablename__ = "submission_doc_types"
    # 【役割】 お客様に提出を依頼する各種書類のマスタ（例: 通帳写し, 源泉徴収票）
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


# --- 3. 個人情報管理テーブル ---


class Address(Base):
    __tablename__ = "address"
    # 【役割】 住所情報を構成要素ごとに分離して管理
    id = Column(Integer, primary_key=True)
    zip_code = Column(String)
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
    __tablename__ = "contact"
    # 【役割】 電話番号やメールアドレスなど、連絡先本体を管理
    id = Column(Integer, primary_key=True)
    value = Column(String, nullable=False)  # 連絡先の値（例: 090-xxxx-xxxx）
    type = Column(String, nullable=False)  # 種別（PHONE, EMAIL）
    sub_type = Column(String)  # 詳細種別（自宅、携帯など）


class D_AddressHistory(Base):
    __tablename__ = "d_address_history"
    # 【役割】 被相続人の住所とAddressマスタを結びつけ、履歴を管理する中間テーブル
    id = Column(Integer, primary_key=True)
    deceased_id = Column(Integer, ForeignKey("deceased.id"), nullable=False)
    address_id = Column(Integer, ForeignKey("address.id"), nullable=False)
    is_last_address = Column(Boolean, nullable=False, default=False)  # 最後の住所フラグ

    deceased = relationship("Deceased", back_populates="address_links")
    address = relationship("Address", back_populates="deceased_history")


class H_AddressHistory(Base):
    __tablename__ = "h_address_history"
    # 【役割】 相続人の住所とAddressマスタを結びつけ、履歴を管理する中間テーブル
    id = Column(Integer, primary_key=True)
    heir_id = Column(Integer, ForeignKey("heirs.id"), nullable=False)
    address_id = Column(Integer, ForeignKey("address.id"), nullable=False)
    is_current_address = Column(
        Boolean, nullable=False, default=False
    )  # 現在の住所フラグ

    heir = relationship("Heir", back_populates="address_links")
    address = relationship("Address", back_populates="heir_history")


class D_ContactLink(Base):
    __tablename__ = "d_contact_link"
    # 【役割】 被相続人と連絡先（Contact）を結びつける中間テーブル
    id = Column(Integer, primary_key=True)
    deceased_id = Column(Integer, ForeignKey("deceased.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contact.id"), nullable=False)

    deceased = relationship("Deceased", back_populates="contact_links")
    contact = relationship("Contact")


class H_ContactLink(Base):
    __tablename__ = "h_contact_link"
    # 【役割】 相続人と連絡先（Contact）を結びつける中間テーブル
    id = Column(Integer, primary_key=True)
    heir_id = Column(Integer, ForeignKey("heirs.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contact.id"), nullable=False)

    heir = relationship("Heir", back_populates="contact_links")
    contact = relationship("Contact")


# --- 6. 個人情報詳細テーブル (Deceased & Heir) を Case より先に定義する (リレーションシップ解決のため) ---
# Case が Deceased を参照し、Deceased が Case を逆参照しているため、
# 互いに参照し合うリレーションシップは back_populates を使用し、
# どちらを先に定義しても問題ないようにします。ただし、今回は Deceased を先に定義します。


class Deceased(Base):
    __tablename__ = "deceased"
    # 【役割】 被相続人の戸籍上の基本情報と、案件への紐付け (Caseのコア情報)
    id = Column(Integer, primary_key=True)
    case_id = Column(
        Integer, ForeignKey("cases.case_id"), nullable=False, unique=True
    )  # 案件ID (FK)

    name_last = Column(String, nullable=False)
    name_first = Column(String)
    name_last_kana = Column(String)
    name_first_kana = Column(String)
    hometown = Column(String)
    date_of_birth = Column(Date)
    date_of_death = Column(Date)
    relationship_type = Column(String)  # 本人

    heirs = relationship(
        "Heir", back_populates="deceased", cascade="all, delete-orphan"
    )  # 相続人一覧
    address_links = relationship(
        "D_AddressHistory", back_populates="deceased", cascade="all, delete-orphan"
    )  # 住所履歴 (中間テーブル)
    contact_links = relationship(
        "D_ContactLink", back_populates="deceased", cascade="all, delete-orphan"
    )  # 連絡先履歴 (中間テーブル)
    # 💡 修正1: Caseへの逆参照を back_populates に変更 (Case側も修正が必要)
    case = relationship("Case", back_populates="deceased_ref")


class Heir(Base):
    __tablename__ = "heirs"
    # 【役割】 個々の相続人の戸籍上の基本情報と、被相続人への紐付け (遺産分割協議の対象者)
    id = Column(Integer, primary_key=True)
    deceased_id = Column(
        Integer, ForeignKey("deceased.id"), nullable=False
    )  # 被相続人ID (FK)

    name_last = Column(String, nullable=False)
    name_first = Column(String)
    name_last_kana = Column(String)
    name_first_kana = Column(String)
    hometown = Column(String)
    date_of_birth = Column(Date)
    relationship_type = Column(String, nullable=False)  # 続柄（例: 長男、配偶者）

    deceased = relationship("Deceased", back_populates="heirs")  # Deceasedへの逆参照
    address_links = relationship(
        "H_AddressHistory", back_populates="heir", cascade="all, delete-orphan"
    )
    contact_links = relationship(
        "H_ContactLink", back_populates="heir", cascade="all, delete-orphan"
    )


# --- 4. 案件ハブテーブル (Core Case Management) ---


class Case(Base):
    __tablename__ = "cases"
    # 【役割】 遺産整理業務全体のハブ、進捗、担当者、入金、期限を一元管理
    case_id = Column(Integer, primary_key=True)
    case_number = Column(String, unique=True, nullable=False)  # 案件番号 (例: G0001)
    client_name = Column(String, nullable=False)  # 依頼者（契約者）名
    # 💡 修正5: 初期データ投入でエラーになるため、一時的にコメントアウトされていたdeceased_nameを削除

    # 担当者とステータス
    manager_id = Column(Integer, ForeignKey("users.id"))  # 担当1: 進捗管理責任者 (FK)
    operator_id = Column(Integer, ForeignKey("users.id"))  # 担当2: 実務担当者 (FK)
    current_status_id = Column(
        Integer, ForeignKey("case_statuses.id")
    )  # 受託までのステータス (FK)

    # 入金情報
    fee_contract_amount = Column(Float, default=0.0)  # 契約時の総報酬額
    deposit_required_amount = Column(Float, default=0.0)  # 着手金の請求額
    deposit_paid_amount = Column(Float, default=0.0)  # 着手金の入金額
    is_paid_in_full = Column(Boolean, default=False)  # 全額入金完了フラグ

    # 提出書類数量
    certs_of_seal_count = Column(Integer, default=0)  # 印鑑証明書の受領枚数
    power_of_attorney_count = Column(Integer, default=0)  # 委任状の受領枚数 (追加)

    # 日程情報
    date_of_death = Column(Date)  # 死亡日 (簡略化されたフィールド)
    interview_date = Column(DateTime)  # 面談日時
    contract_date = Column(Date)  # 受託日 (契約締結日)
    tax_deadline = Column(DateTime)  # 相続税申告期限
    created_at = Column(DateTime, default=datetime.now)

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
    tasks = relationship(
        "Task", back_populates="case_ref", cascade="all, delete-orphan"
    )
    expenses = relationship(
        "Expense", back_populates="case_ref", cascade="all, delete-orphan"
    )
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
    liabilities = relationship(
        "Liability", back_populates="case_ref", cascade="all, delete-orphan"
    )


# --- 5. タスクテンプレートと実行タスクモデル ---


class TaskTemplate(Base):
    __tablename__ = "task_templates"
    # 【役割】定型タスクの定義マスター (ロジックの元データ)
    template_id = Column(Integer, primary_key=True)
    description = Column(
        String, nullable=False
    )  # タスク名 (例: 【承認】目録ドラフトの最終チェック)
    default_due_days = Column(Integer, default=1)  # 契約日から何日後か
    is_manager_task = Column(Boolean, default=False)  # True: 担当1(Manager)に割り当て
    depends_on_template_id = Column(
        Integer, ForeignKey("task_templates.template_id")
    )  # 依存先タスクID

    # 自己参照リレーション
    depends_on = relationship("TaskTemplate", remote_side=[template_id])


class Task(Base):
    __tablename__ = "tasks"
    # 【役割】実行中の個別のTODOレコード (担当者に割り当てられる具体的な作業)
    task_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    template_id = Column(
        Integer, ForeignKey("task_templates.template_id")
    )  # テンプレートID (どの定型タスクか)

    description = Column(String, nullable=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id"))  # 実行担当者ID (FK)
    due_date = Column(DateTime)  # 実行期限
    is_completed = Column(Boolean, default=False)  # 完了フラグ

    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    template_ref = relationship("TaskTemplate")
    document_logs = relationship(
        "TaskDocumentLog",
        back_populates="task_ref",
        cascade="all, delete-orphan",
    )
    case_ref = relationship("Case", back_populates="tasks")


class TaskDocumentLog(Base):
    __tablename__ = "task_document_logs"
    # 【役割】 原本追跡ログ (いつ、どの原本を、誰に、何で送ったかの監査ログ)
    log_id = Column(Integer, primary_key=True)
    task_id = Column(
        Integer, ForeignKey("tasks.task_id"), nullable=False
    )  # 紐づくタスクID
    document_type_id = Column(
        Integer, ForeignKey("document_types.id"), nullable=False
    )  # 原本の種類 (例: 印鑑証明書)
    shipping_method_id = Column(
        Integer, ForeignKey("shipping_methods.id"), nullable=False
    )  # 送付方法 (例: レターパック)

    sent_date = Column(DateTime, nullable=False)
    sent_to = Column(String, nullable=False)  # 送付先（例: 〇〇銀行 or 司法書士）
    tracking_number = Column(String, unique=True)  # 追跡番号
    is_returned = Column(Boolean, default=False)  # 還付完了フラグ

    document_type = relationship("DocumentType")
    shipping_method = relationship("ShippingMethod")
    task_ref = relationship("Task", back_populates="document_logs")


# --- 7. 財産・トランザクション詳細テーブル (未定義だったクラスを Case の後に定義) ---


class FinancialAsset(Base):
    __tablename__ = "financial_assets"
    # ... 以前の定義のまま ...
    asset_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    inst_id = Column(Integer, ForeignKey("institutions.id"))  # 金融機関マスタへのFK

    bank_name = Column(String)
    account_number = Column(String)
    balance = Column(Float, default=0.0)
    status = Column(String, default="調査中")

    institution = relationship("FinancialInstitution")  # 銀行マスタへのリレーション
    case_ref = relationship("Case", back_populates="financial_assets")


class RealEstateAsset(Base):
    __tablename__ = "real_estate_assets"
    # ... 以前の定義のまま ...
    real_estate_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    municipality_name = Column(String, nullable=False)  # 名寄帳取得時の市区町村名

    case_ref = relationship("Case", back_populates="real_estates")


class InsuranceAsset(Base):
    __tablename__ = "insurance_assets"
    # 💡 修正4で Case に追加されたリレーションに対応
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    # ... (保険固有のフィールドを追加)
    insurance_company = Column(String)
    policy_number = Column(String)
    estimated_value = Column(Float)

    case_ref = relationship("Case", back_populates="insurance_assets")


class OtherAsset(Base):
    __tablename__ = "other_assets"
    # 💡 修正4で Case に追加されたリレーションに対応
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    # ... (その他財産固有のフィールドを追加)
    description = Column(String)
    estimated_value = Column(Float)

    case_ref = relationship("Case", back_populates="other_assets")


class Liability(Base):
    __tablename__ = "liability"
    # 💡 修正6: 初期データ投入でエラーになるため、descriptionカラムを追加
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    is_debt = Column(Boolean, nullable=False, default=True)  # 借金か費用か
    description = Column(String)  # 💡 修正: 初期データ投入時に参照されるため追加
    amount = Column(Float, nullable=False)
    is_funeral_cost = Column(Boolean, nullable=False, default=False)  # 葬儀費用フラグ

    case_ref = relationship("Case", back_populates="liabilities")


class Expense(Base):
    __tablename__ = "expenses"
    # 【役割】 会社が立て替えた実費 (レターパック代、戸籍代など)
    expense_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    # ... (金額、費目、日付などのフィールドが続く)

    case_ref = relationship("Case", back_populates="expenses")


class ContactLog(Base):
    __tablename__ = "contact_logs"
    # 【役割】 顧客連絡履歴 (いつ、誰が、何を連絡したか)
    log_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    contact_content = Column(String, nullable=False)
    is_thank_you_payment = Column(Boolean, default=False)  # 入金お礼連絡フラグ

    case_ref = relationship("Case", back_populates="contact_logs")


class CaseSubmissionDoc(Base):
    __tablename__ = "case_submission_docs"
    # 【役割】 お客様への提出依頼書類の進捗管理 (柔軟な提出リスト)
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)

    case_ref = relationship("Case", back_populates="submitted_docs")


# 💡 追加: 未完了タスクの取得
def get_incomplete_tasks(user_id=None):
    """未完了のタスクを取得する (ユーザーIDでフィルタ可能)"""
    db = Session()
    try:
        query = db.query(Task).filter(Task.is_completed == False)

        if user_id:
            query = query.filter(Task.assigned_user_id == user_id)

        # 期限が近い順にソート
        tasks = query.order_by(Task.due_date).limit(10).all()

        # 案件番号と担当者名を取得するために結合（Eager Loading）
        tasks_data = []
        for task in tasks:
            case_number = task.case_ref.case_number if task.case_ref else "N/A"
            assigned_user = task.assigned_user.name if task.assigned_user else "未割当"

            tasks_data.append(
                {
                    "task_id": task.task_id,
                    "case_number": case_number,
                    "description": task.description,
                    "due_date": task.due_date.strftime("%Y/%m/%d")
                    if task.due_date
                    else "N/A",
                    "assigned_user": assigned_user,
                }
            )
        return tasks_data
    finally:
        db.close()


# 💡 追加: 案件リストの取得 (メイン一覧用)
def get_case_list(search_term="", status_id=None):
    """案件一覧を取得する (検索・フィルタリング対応)"""
    db = Session()
    try:
        query = (
            db.query(Case)
            .options(joinedload(Case.deceased_ref))
            .order_by(Case.contract_date.desc())
        )

        # 検索条件
        if search_term:
            query = query.filter(
                (Case.case_number.ilike(f"%{search_term}%"))
                | (Case.client_name.ilike(f"%{search_term}%"))
            )

        # ステータスフィルター
        if status_id:
            query = query.filter(Case.current_status_id == status_id)

        cases = query.limit(50).all()

        case_list = []
        for case in cases:
            deceased_name = (
                case.deceased_ref.name_last + " " + case.deceased_ref.name_first
                if case.deceased_ref
                else "N/A"
            )

            case_list.append(
                {
                    "case_id": case.case_id,
                    "case_number": case.case_number,
                    "client_name": case.client_name,
                    "deceased_name": deceased_name,
                    "contract_date": case.contract_date.strftime("%Y/%m/%d")
                    if case.contract_date
                    else "N/A",
                    "status": case.status_ref.name if case.status_ref else "N/A",
                }
            )
        return case_list
    finally:
        db.close()


# --- DB操作関数 ---


def init_db():
    Base.metadata.create_all(Engine)


def add_initial_data():
    session = Session()
    if session.query(Case).count() == 0:
        user1 = User(windows_id="admin01", name="管理者 太郎", role="Manager")
        status1 = CaseStatus(name="受託", order_num=3)
        # 💡 修正7: FinancialInstitutionを初期データに追加
        inst1 = FinancialInstitution(name="みずほ銀行")
        session.add_all([user1, status1, inst1])
        session.flush()

        case1 = Case(
            case_number="2025-001",
            client_name="山田 花子",
            # 💡 修正5: Caseモデルから deceased_name は削除されたため、初期データからも削除
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
            inst_id=inst1.id,  # 💡 修正7: inst_idにFinancialInstitutionのIDを設定
            bank_name="みずほ銀行",
            account_number="1234567",
            balance=5000000.0,
            status="手続き中",
        )
        liability1 = Liability(
            case_id=case1.case_id,
            is_debt=False,
            description="葬儀費用",  # 💡 修正6: descriptionカラムが初期データに必要
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
