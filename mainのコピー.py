import flet as ft
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
    or_,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# --- 1. データベース設定とBaseクラス ---

# SQLiteの設定（isan_seiri.dbが作成されます）
DATABASE_URL = "sqlite:///isan_seiri.db"
engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """DBセッションを取得するヘルパー関数"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


# --- 2. モデル定義 (全テーブルをここに集約) ---


# マスタテーブル
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
    tracking_base_url = Column(String, nullable=False)
    estimated_days = Column(Integer)


class SubmissionDocType(Base):
    __tablename__ = "submission_doc_types"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


# 個人情報管理関連 (簡略化)
class Address(Base):
    __tablename__ = "address"
    id = Column(Integer, primary_key=True)
    prefecture = Column(String, nullable=False)


class Contact(Base):
    __tablename__ = "contact"
    id = Column(Integer, primary_key=True)
    value = Column(String, nullable=False)


class D_AddressHistory(Base):
    __tablename__ = "d_address_history"
    id = Column(Integer, primary_key=True)
    deceased_id = Column(Integer, ForeignKey("deceased.id"), nullable=False)
    address_id = Column(Integer, ForeignKey("address.id"), nullable=False)


class D_ContactLink(Base):
    __tablename__ = "d_contact_link"
    id = Column(Integer, primary_key=True)
    deceased_id = Column(Integer, ForeignKey("deceased.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contact.id"), nullable=False)


# 案件ハブテーブル
class Case(Base):
    __tablename__ = "cases"
    case_id = Column(Integer, primary_key=True)
    case_number = Column(String, unique=True, nullable=False)  # G0001
    client_name = Column(String, nullable=False)
    deceased_name = Column(String)
    date_of_death = Column(Date)

    # 担当者とステータス
    manager_id = Column(Integer, ForeignKey("users.id"))  # 担当1
    operator_id = Column(Integer, ForeignKey("users.id"))  # 担当2
    current_status_id = Column(Integer, ForeignKey("case_statuses.id"))
    tax_deadline = Column(DateTime)

    # 入金情報 (サマリー用)
    fee_contract_amount = Column(Float, default=0.0)
    is_paid_in_full = Column(Boolean, default=False)

    # リレーションシップ
    manager = relationship("User", foreign_keys=[manager_id])
    operator = relationship("User", foreign_keys=[operator_id])
    status_ref = relationship("CaseStatus")

    # スポークテーブルへのリレーション (全トランザクションの基盤)
    deceased_ref = relationship(
        "Deceased", backref="case", uselist=False, cascade="all, delete-orphan"
    )
    financial_assets = relationship(
        "FinancialAsset", backref="case", cascade="all, delete-orphan"
    )
    tasks = relationship("Task", backref="case", cascade="all, delete-orphan")
    # ... 他のスポークテーブルも同様に定義されます ...


# 被相続人・相続人・トランザクション（簡略化）
class Deceased(Base):
    __tablename__ = "deceased"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    name_last = Column(String, nullable=False)
    date_of_death = Column(Date)
    heirs = relationship(
        "Heir", back_populates="deceased", cascade="all, delete-orphan"
    )


class Heir(Base):
    __tablename__ = "heirs"
    id = Column(Integer, primary_key=True)
    deceased_id = Column(Integer, ForeignKey("deceased.id"), nullable=False)
    name_last = Column(String, nullable=False)
    relationship_type = Column(String, nullable=False)
    deceased = relationship("Deceased", back_populates="heirs")


class FinancialAsset(Base):
    __tablename__ = "financial_assets"
    asset_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    balance = Column(Float, default=0.0)


class Task(Base):
    __tablename__ = "tasks"
    task_id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.case_id"), nullable=False)
    description = Column(String, nullable=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id"))
    is_completed = Column(Boolean, default=False)


# --- 3. Flet UI (HubView) の実装 ---


class HubView(ft.View):
    def __init__(self, page: ft.Page, session, current_user_id: int):
        super().__init__(route="/hub")
        self.page = page
        self.session = session
        self.current_user_id = current_user_id

        # 状態管理変数: 'ALL' (全案件) または 'MY_TODO' (担当案件のみ)
        self.filter_mode = "ALL"

        # UIコンポーネントの初期化
        self.summary_cards = ft.Container()  # 初期化
        self.controls_area = self.create_controls_area()
        self.main_datatable = self.create_main_datatable()

        # 初期データのロード
        self.load_data()

        self.controls = [
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "遺産整理案件管理ハブ", size=24, weight=ft.FontWeight.BOLD
                        ),
                        # 1. サマリーカードエリア (データをロード後に更新)
                        self.summary_cards,
                        ft.Divider(),
                        # 2. コントロールエリア
                        self.controls_area,
                        # 3. メイン一覧エリア
                        self.main_datatable,
                    ],
                    spacing=20,
                    scroll=ft.ScrollMode.ADAPTIVE,
                ),
                padding=20,
                expand=True,
            )
        ]

    # --- 1. サマリーカードエリアの実装 ---
    def create_summary_cards(self, total_active, my_todo, total_assets):
        def create_card(title, value, color):
            return ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(title, size=14, color=ft.Colors.BLACK54),
                            ft.Text(
                                f"{value}",
                                size=28,
                                weight=ft.FontWeight.BOLD,
                                color=color,
                            ),
                        ],
                        spacing=5,
                    ),
                    padding=15,
                    width=250,
                ),
                elevation=5,
            )

        self.summary_cards.content = ft.Row(
            [
                create_card("総アクティブ案件数", total_active, ft.Colors.BLUE_700),
                create_card("My TODO案件数", my_todo, ft.Colors.RED_600),
                create_card(
                    "総資産評価額 (モック)",
                    f"¥{total_assets / 1000000}M",
                    ft.Colors.GREEN_700,
                ),
            ],
            wrap=True,
            spacing=20,
        )
        return self.summary_cards

    # --- 2. コントロールエリアの実装 ---
    def create_controls_area(self):
        def toggle_my_todo(e):
            """My TODOフィルターの切り替え処理"""
            if self.filter_mode == "ALL":
                self.filter_mode = "MY_TODO"
                e.control.text = "全案件表示に戻す"
            else:
                self.filter_mode = "ALL"
                e.control.text = "My TODO案件のみ表示"
            self.load_data()
            self.page.update()

        return ft.Row(
            [
                ft.TextField(hint_text="案件番号または契約者名を検索...", width=300),
                ft.VerticalDivider(),
                ft.ElevatedButton("新規案件作成", icon=ft.Icons.ADD),
                ft.VerticalDivider(),
                ft.ElevatedButton("My TODO案件のみ表示", on_click=toggle_my_todo),
            ],
            spacing=10,
        )

    # --- 3. メイン一覧エリアの実装 (DataTable) ---
    def create_main_datatable(self):
        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("案件番号")),
                ft.DataColumn(ft.Text("契約者名")),
                ft.DataColumn(ft.Text("ステータス")),
                ft.DataColumn(ft.Text("申告期限")),
                ft.DataColumn(ft.Text("担当1/担当2")),
            ],
            rows=[],
        )

    # --- データ取得・更新ロジック ---
    def load_data(self):
        """DBから案件データを取得し、UIを更新する"""

        # 1. フィルタリング条件の構築
        query = self.session.query(Case)

        # 未完了案件のみをベースとする
        active_query = query.filter(Case.current_status_id != 6)

        # 'My TODO'モードの場合、フィルタを適用
        if self.filter_mode == "MY_TODO":
            # ログインユーザーが担当1 OR 担当2 に割り当てられている案件
            query = active_query.filter(
                or_(
                    (Case.manager_id == self.current_user_id),
                    (Case.operator_id == self.current_user_id),
                )
            )
        else:
            query = active_query

        cases = query.order_by(Case.tax_deadline).all()  # 期限が近い順にソート

        # 2. KPI計算 (モック)
        total_active_count = (
            self.session.query(Case).filter(Case.current_status_id != 6).count()
        )
        my_todo_count = active_query.filter(
            or_(
                (Case.manager_id == self.current_user_id),
                (Case.operator_id == self.current_user_id),
            )
        ).count()
        total_asset_mock = 2500000000  # 25億円モック

        # 3. サマリーカードの更新
        self.create_summary_cards(total_active_count, my_todo_count, total_asset_mock)

        # 4. DataTableの行を更新
        rows = []
        for case in cases:
            status_name = case.status_ref.name if case.status_ref else "不明"
            tax_deadline_str = (
                case.tax_deadline.strftime("%Y-%m-%d") if case.tax_deadline else "N/A"
            )

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(case.case_number)),
                        ft.DataCell(ft.Text(case.client_name)),
                        ft.DataCell(ft.Text(status_name)),
                        ft.DataCell(ft.Text(tax_deadline_str)),
                        ft.DataCell(
                            ft.Text(f"{case.manager.name}/{case.operator.name}")
                        ),
                    ],
                    on_select_changed=lambda e, c=case: self.page.go(
                        f"/case/{c.case_id}"
                    ),
                )
            )

        self.main_datatable.rows = rows


# --- 4. メイン実行関数 ---


def main(page: ft.Page):
    page.title = "遺産整理業務管理システム"
    page.vertical_alignment = ft.CrossAxisAlignment.START

    # 認証: Windowsアカウントのモック取得
    # 実際には os.environ.get('USERNAME') などを使用します。ここでは tanaka_a で固定
    # current_windows_id = os.environ.get('USERNAME', 'tanaka_a')
    current_windows_id = "tanaka_a"

    # DB接続
    db = SessionLocal()

    # ログインユーザーのDB IDを取得
    current_user_db = (
        db.query(User).filter(User.windows_id == current_windows_id).first()
    )
    if not current_user_db:
        # ユーザーが見つからない場合のフォールバック（管理者でログイン）
        current_user_db = db.query(User).filter(User.windows_id == "admin").first()

    user_id = current_user_db.id if current_user_db else 1

    # ルーティング（今回はHubViewのみ）
    def route_change(route):
        page.views.clear()
        page.views.append(HubView(page, db, user_id))
        page.update()

    page.on_route_change = route_change
    page.go(page.route)

    # --- 5. seed_database(db) 関数の定義 ---


def seed_database(db):
    """Fletアプリのテストに必要な初期データを投入する"""

    # 1. ユーザーデータの投入
    users_data = [
        {"windows_id": "tanaka_a", "role": "Manager", "name": "田中 篤志"},
        {"windows_id": "sato_b", "role": "Operator", "name": "佐藤 華子"},
        {"windows_id": "admin", "role": "Admin", "name": "システム管理者"},
    ]
    for data in users_data:
        if not db.query(User).filter(User.windows_id == data["windows_id"]).first():
            db.add(User(**data))

    db.commit()
    tanaka = db.query(User).filter(User.windows_id == "tanaka_a").first()
    sato = db.query(User).filter(User.windows_id == "sato_b").first()

    # 2. マスタデータの投入 (簡略化されたもの)
    statuses = ["面談調整中", "面談日決定", "契約検討", "受託", "不受理/辞退", "完了"]
    for i, name in enumerate(statuses):
        if not db.query(CaseStatus).filter(CaseStatus.name == name).first():
            db.add(CaseStatus(name=name, order_num=i + 1))

    # 金融機関マスタ (テスト用)
    inst_names = ["みずほ銀行", "三井住友信託銀行", "野村證券", "ゆうちょ銀行"]
    for name in inst_names:
        if (
            not db.query(FinancialInstitution)
            .filter(FinancialInstitution.name == name)
            .first()
        ):
            db.add(FinancialInstitution(name=name))

    db.commit()


if __name__ == "__main__":
    # 最初にデータベース構造を作成し、初期データを投入します
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        # DBにマスタやダミー案件がない場合のみ実行
        if not db.query(User).first():
            seed_database(db)

    ft.app(target=main)
