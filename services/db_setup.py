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
)
from sqlalchemy.orm import (
    Session,
    declarative_base,
    joinedload,
    relationship,
    sessionmaker,
)

# サービス層内のインポートは、相対パスまたはsys.pathの調整が必要ですが、
# ここでは同じディレクトリに存在すると仮定して記述します。
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


# 💡 以下、既存コードで定義されていた全てのDBモデル

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


class FinancialInstitution(Base):
    __tablename__ = "institutions"  # 金融機関名のマスター
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # 金融機関名


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

    heirs = relationship("Heir", back_populates="deceased", cascade="all, delete-orphan")
    address_links = relationship(
        "D_AddressHistory", back_populates="deceased", cascade="all, delete-orphan"
    )
    contact_links = relationship(
        "D_ContactLink", back_populates="deceased", cascade="all, delete-orphan"
    )
    case = relationship("Case", back_populates="deceased_ref")


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
    __tablename__ = "financial_assets"
    asset_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    inst_id = Column(Integer, ForeignKey("institutions.id"))

    bank_name = Column(String)
    bank_code = Column(String)
    branch_name = Column(String)
    branch_code = Column(String)
    account_number = Column(String)
    balance = Column(Float, default=0.0)
    status = Column(String, default="調査中")

    case_ref = relationship("Case", back_populates="financial_assets")


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


# =======================================================
## データアクセス関数 (CRUD)
# =======================================================


# 💡 全ユーザーリストの取得 (担当者ドロップダウン用)
def get_all_users():
    """全てのユーザーIDと名前を取得する"""
    db = Session()
    try:
        users = db.query(User.id, User.name).order_by(User.id).all()
        # {ID: Name} の辞書形式で返す
        return {id: name for id, name in users}  # {ID: Name} の辞書形式で返す
    finally:
        db.close()


# 💡 未完了タスクの取得 (ダッシュボード左側用)
def get_incomplete_tasks(user_id=None):
    """未完了のタスクを取得する (ユーザーIDでフィルタ可能)"""
    db = Session()
    try:
        tasks = (
            db.query(Task, Case.case_number, User.name, Case.client_name)
            .join(Case, Task.case_id == Case.case_id)
            .join(User, Task.assigned_user_id == User.id)
            .filter(Task.is_completed == False)
            .filter(Task.assigned_user_id == user_id)
            .order_by(Task.due_date)
            .limit(10)
            .all()
        )

        tasks_data = []
        for task, case_number, assigned_user_name, client_name in tasks:
            tasks_data.append(
                {
                    "task_id": task.task_id,
                    "case_id": task.case_id,
                    "case_number": case_number,
                    "description": task.description,
                    "due_date": task.due_date.strftime("%Y/%m/%d") if task.due_date else "N/A",
                    "assigned_user": assigned_user_name,
                    "client_name": client_name,
                }
            )
        return tasks_data
    finally:
        db.close()


# 💡 案件リストの取得 (メイン一覧用)
def get_case_list(search_term="", status_id=None, user_id=None):
    """案件一覧を取得する (検索・フィルタリング・担当者フィルタ対応)"""
    db = Session()
    try:
        query = (
            db.query(
                Case,  # 1. Caseオブジェクト全体
                Deceased.name_last,  # 2. Deceasedの姓
                Deceased.name_first,  # 3. Deceasedの名
                CaseStatus.name.label("status_name"),  # 4. ステータス名
                Task.description,
                Task.last_updated_at,
            )
            .join(
                Deceased, Case.case_id == Deceased.case_id, isouter=True
            )  # Deceasedテーブルとの結合
            .join(
                CaseStatus, Case.current_status_id == CaseStatus.id, isouter=True
            )  # CaseStatusテーブルとの結合
            .join(Task, Case.case_id == Task.case_id, isouter=True)  # Taskテーブルとの結合
            .order_by(Task.last_updated_at.desc())
        )

        # 検索条件
        if search_term:
            query = query.filter(
                (Case.case_number.ilike(f"%{search_term}%"))
                | (Case.client_name.ilike(f"%{search_term}%"))
                | (Case.client_name_kana.ilike(f"%{search_term}%"))
            )

        # ステータスフィルター
        if status_id:
            query = query.filter(Case.current_status_id == status_id)

        # 💡 担当者によるフィルタ
        if user_id:
            query = query.filter((Case.manager_id == user_id) | (Case.operator_id == user_id))

        cases_data = query.limit(50).all()

        case_list = []
        processed_case_ids = set()

        for (
            case,
            d_last,
            d_first,
            status_name,
            description,
            last_updated_at,
        ) in cases_data:
            if case.case_id in processed_case_ids:
                # 既に処理済みであれば、この行はタスク情報のみが異なる重複行であるため、
                # リストへの追加処理をスキップします。
                continue

            # 💡 案件IDの記録:
            #    - 処理を行う案件IDをセットに追加し、以降の行で重複として識別できるようにします。
            processed_case_ids.add(case.case_id)

            # --- 重複排除後に実行される、案件情報構築ロジック ---
            deceased_name = f"{d_last} {d_first}" if d_last else "N/A"

            # 担当ロールの決定 (ユーザーが担当1か担当2かを判定)
            role_label = ""
            if user_id:
                is_manager = case.manager_id == user_id
                is_operator = case.operator_id == user_id
                if is_manager and is_operator:
                    role_label = "担当1 & 2"
                elif is_manager:
                    role_label = "担当1"
                elif is_operator:
                    role_label = "担当2"

            case_list.append(
                {
                    "case_id": case.case_id,
                    "case_number": case.case_number,
                    "client_name": case.client_name,
                    "deceased_name": deceased_name,
                    "contract_date": case.contract_date.strftime("%Y/%m/%d")
                    if case.contract_date
                    else "N/A",
                    "status": status_name if status_name else "N/A",
                    "role_label": role_label,
                    "manager_id": case.manager_id,
                    "operator_id": case.operator_id,
                    "description": description,
                    "last_updated_at": (
                        last_updated_at.strftime("%Y/%m/%d") if last_updated_at else "N/A"
                    ),
                }
            )
            print()
            print(
                case.case_id,
                case.case_number,
                f"case.client_name:{case.client_name}",
                f"deceased_name:{deceased_name}",
            )
        return case_list
    finally:
        db.close()


# 💡 担当案件の取得 (get_case_listのuser_idフィルタとほぼ同じだが、既存コードに合わせたため残す)
def get_my_cases(user_id: int, limit: int = 10):
    """特定のユーザーが担当者(Manager)または実務担当者(Operator)である案件を取得する。"""
    db = Session()
    try:
        query = (
            db.query(Case)
            .options(joinedload(Case.deceased_ref), joinedload(Case.status_ref))
            .filter((Case.manager_id == user_id) | (Case.operator_id == user_id))
            .order_by(Case.current_status_id, Case.contract_date.desc())
        )

        cases = query.limit(limit).all()

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
                    "status": case.status_ref.name if case.status_ref else "N/A",
                }
            )
        return case_list
    finally:
        db.close()


# 💡 全担当者の業務キャパシティを取得 (管理職ビュー用)
def get_user_capacity_data():
    """管理職向け: 全担当者の業務キャパシティ（未完了タスク数、担当案件数）を取得する。"""
    db = Session()
    try:
        users = db.query(User).all()
        capacity_data = []

        for user in users:
            user_id = user.id

            task_count = (
                db.query(func.count(Task.task_id))
                .filter(Task.assigned_user_id == user_id, Task.is_completed == False)
                .scalar()
            )

            case_count = (
                db.query(func.count(Case.case_id))
                .filter((Case.manager_id == user_id) | (Case.operator_id == user_id))
                .scalar()
            )

            capacity_data.append(
                {
                    "user_id": user_id,
                    "name": user.name,
                    "role": user.role,
                    "total_incomplete_tasks": task_count,
                    "total_cases_handled": case_count,
                }
            )
        capacity_data.sort(key=lambda x: x["total_incomplete_tasks"], reverse=True)
        return capacity_data
    finally:
        db.close()


# 💡 月ごとの面談スケジュールを取得
def get_interviews_by_month(year: int, month: int):
    """指定された年月に面談予定がある案件のリストを取得する。"""
    db = Session()
    try:
        # 月の開始日と終了日を計算
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        query = (
            db.query(Case, Deceased.name_last, Deceased.name_first)
            .join(Deceased, Case.case_id == Deceased.case_id, isouter=True)
            .filter(Case.interview_date.isnot(None))
            .filter(Case.interview_date >= start_date)
            .filter(Case.interview_date < end_date)
            .order_by(Case.interview_date)
        )

        results = query.all()

        interview_list = []
        for case, d_last, d_first in results:
            deceased_name = f"{d_last} {d_first}" if d_last else "N/A"

            interview_list.append(
                {
                    "case_id": case.case_id,
                    "case_number": case.case_number,
                    "client_name": case.client_name,
                    "deceased_name": deceased_name,
                    "interview_date": case.interview_date,
                    "manager_id": case.manager_id,
                    "operator_id": case.operator_id,
                }
            )
        return interview_list
    finally:
        db.close()


# --- DB初期化関数 ---
def init_db():
    Base.metadata.create_all(Engine)


# --- DB操作関数 ---


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
            case_number="G0001",
            client_name="山田 花子",
            client_name_kana="やまだ　はなこ",
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

    # from services.db_setup import Base, Engine, Session
    # 💡 クラス: データベースの宣言的ベースクラス (SQLAlchemy)
    # 💡 クラス: データベース接続エンジン (SQLAlchemy)
    # 💡 クラス: データベース操作を行うセッションクラス (SQLAlchemy)

    # DBテーブル構造の作成（db_setup.pyで定義した全てのテーブルを作成）
    # Base.metadata.create_all(Engine)

    # DBセッション開始
    with Session() as db:  # 💡 変数: データベースセッションオブジェクト
        # ユーザーとテンプレートの初期投入
        case_id, tanaka_id, sato_id = seed_db_users_and_cases(
            db
        )  # 💡 変数: case_id (案件ID), tanaka_id (担当1 ID), sato_id (担当2 ID)
        setup_task_templates(db)

        # 既存タスクをクリア (テスト再実行用)
        db.query(Task).delete()
        db.commit()

        # 案件ID:1をトリガーにしてタスクを自動生成
        print("---------------------------------------")
        print(f"案件ID: {case_id} のタスク生成を開始します。")
        generate_case_tasks(db, case_id)
        print("---------------------------------------")

        # 結果の確認
        generated_tasks = db.query(
            Task
        ).all()  # 💡 変数: 生成された全てのタスク (Task) のDBレコードリスト
        print(f"生成されたタスク総数: {len(generated_tasks)} 件")


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


def get_case_folder_path(case_id: int) -> str | None:
    """
    Case ID に紐づくフォルダパス (Case.folder_path) を取得する。
    """
    with Session(bind=Engine) as session:
        case = session.query(Case).filter(Case.case_id == case_id).first()
        # フォルダパスが存在しない場合や Case が見つからない場合は None を返す
        return case.folder_path if case and case.folder_path else None


def get_case_by_number(case_number: str):
    """
    案件番号を指定して、Caseレコードを一つ取得する。
    存在しない場合は None を返す。
    """
    db = Session()
    try:
        case = db.query(Case).filter(Case.case_number == case_number).first()
        return case
    finally:
        db.close()


# 次の案件番号を生成する関数
def get_next_case_number():
    """
    既存の案件番号 'GXXXX' のうち最大の番号を取得し、次の番号 (GXXXX+1) を生成する。
    案件番号がない場合は 'G0001' を返す。
    """
    with Session() as db:
        # 1. 案件番号が 'G' で始まるレコードをフィルタ
        # 2. 案件番号の末尾の4桁の数字部分を抽出 (SUBSTR) し、それを最大値として取得

        # SQLiteのSUBSTR/CASTを仮定
        max_num_str = (
            db.query(func.max(func.cast(func.substr(Case.case_number, 2), Integer)))
            .filter(Case.case_number.like("G%"))
            .scalar()
        )

        if max_num_str is None:
            # 案件が一つもない場合
            next_number = 1
        else:
            # 最大値に1を加える
            next_number = int(max_num_str) + 1

        # 案件番号 'G' + 4桁のゼロパディング形式にフォーマット
        return f"G{next_number:04d}"


def delete_case_and_all_related_data(case_number: str):
    """
    指定された案件番号のCaseレコードと、それにカスケード削除される全ての関連レコードを削除する。
    さらに、孤立した Address, Contact レコードを削除する。
    """
    db = Session()
    try:
        # 1. Caseレコードを取得
        case_to_delete = db.query(Case).filter(Case.case_number == case_number).first()

        if not case_to_delete:
            print(f"案件番号 {case_number} は見つかりませんでした。")
            return False

        case_id = case_to_delete.case_id
        print(f"案件ID {case_id} ({case_number}) の削除を開始します...")

        # 2. Caseに紐づく Deceased と Heir の ID を事前に取得 (クリーンアップのため)
        deceased = db.query(Deceased).filter(Deceased.case_id == case_id).first()
        deceased_id = deceased.id if deceased else None

        heir_ids = []
        if deceased_id:
            heir_ids = [h.id for h in db.query(Heir).filter(Heir.deceased_id == deceased_id).all()]

        # 3. Caseの削除を実行
        #    - Case, Deceased, Heir, Task, Asset... (cascade設定されているもの全て) が自動削除される
        #    - D_AddressHistory, H_AddressHistory, D_ContactLink, H_ContactLink も自動削除される
        db.delete(case_to_delete)
        db.commit()
        print(
            f"Case ID {case_id} およびカスケード関連データ ({len(heir_ids)}件の相続人を含む) の削除が完了しました。"
        )

        # 4. 孤立した Address および Contact レコードのクリーンアップ

        # 4-1. 孤立した Address レコードの削除
        # どの D_AddressHistory/H_AddressHistory からも参照されていない Address を削除する
        # (NOT EXISTS を使用)

        # Address が D_AddressHistory/H_AddressHistory のどちらからも参照されていない Address ID を見つける
        subquery_deceased = db.query(D_AddressHistory.address_id)
        subquery_heir = db.query(H_AddressHistory.address_id)

        delete_count_addr = (
            db.query(Address)
            .filter(~Address.id.in_(subquery_deceased), ~Address.id.in_(subquery_heir))
            .delete(synchronize_session="fetch")
        )
        db.commit()
        print(f"孤立した Address レコードを {delete_count_addr} 件削除しました。")

        # 4-2. 孤立した Contact レコードの削除
        # どの D_ContactLink/H_ContactLink/CaseContactPoint からも参照されていない Contact を削除する
        subquery_d = db.query(D_ContactLink.contact_id)
        subquery_h = db.query(H_ContactLink.contact_id)
        subquery_c = db.query(CaseContactPoint.contact_id)

        delete_count_contact = (
            db.query(Contact)
            .filter(
                ~Contact.id.in_(subquery_d),
                ~Contact.id.in_(subquery_h),
                ~Contact.id.in_(subquery_c),
            )
            .delete(synchronize_session="fetch")
        )
        db.commit()
        print(f"孤立した Contact レコードを {delete_count_contact} 件削除しました。")

        return True

    except Exception as e:
        db.rollback()
        print(f"データ削除中にエラーが発生しました: {e}")
        return False
    finally:
        db.close()


def create_contact_and_link_to_heir(
    db: Session, heir_id: int, contacts: list[dict], contact_type: str
):
    """
    収集された連絡先リストを Contact テーブルに登録し、H_ContactLink を介して相続人に紐づける。

    Args:
        db (Session): SQLAlchemy セッション
        heir_id (int): 紐づける相続人のID
        contacts (list[dict]): [{'value': '090...', 'sub_type': '携帯'}, ...]
        contact_type (str): "PHONE" または "EMAIL"
    """
    # リストをループして各連絡先を処理
    for contact_data in contacts:
        value = contact_data.get("value")
        sub_type = contact_data.get("sub_type")

        # 値が空でなければ登録
        if value:
            # 1. Contact レコードの作成
            new_contact = Contact(
                value=value,
                type=contact_type,
                sub_type=sub_type,
            )
            db.add(new_contact)
            db.flush()  # IDを取得

            # 2. H_ContactLink レコードの作成
            link = H_ContactLink(heir_id=heir_id, contact_id=new_contact.id)
            db.add(link)
