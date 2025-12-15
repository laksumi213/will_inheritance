# src/views/case_hub.py
import time
import traceback
from typing import Dict

from flet import (
    ButtonStyle,
    Colors,
    Column,
    Container,
    Control,
    CrossAxisAlignment,
    Divider,
    ElevatedButton,
    FontWeight,
    Icon,  # 💡 ここに追加しました
    Icons,
    NavigationRail,
    NavigationRailDestination,
    Page,
    Row,
    SnackBar,
    Text,
    VerticalDivider,
    View,
    alignment,
    padding,
)

# サービス・ユーティリティ
from src.services.deceased_service import get_case_folder_path, get_contracting_party_name
from src.utils.file_system import open_case_folder
from src.views.any_view import AnyView
from src.views.balance_cert_doc import BalanceCertDocView
from src.views.bank_edit import BankEditView

# 各種ビューのインポート
from src.views.detail import DeceasedDetailView
from src.views.freeze_proc_view import FreezeProcView

# 遺産分割協議書画面のインポート
from src.views.inheritance_division_view import InheritanceDivisionView
from src.views.inheritance_doc_view import InheritanceDocView
from src.views.mizuho_balance_doc_view import MizuhoBalanceDocView
from src.views.real_estate_edit import RealEstateEditView
from src.views.securities_edit import SecuritiesEditView
from src.views.smbc_balance_doc_view import SmbcBalanceDocView
from src.views.task_management_view import TaskManagementView
from src.views.visit_reserve_select_bank_view import VisitReserveSelectBankView


# 未実装機能用のプレースホルダー
def PlaceholderView(page: Page, title: str, content: str) -> Control:
    return Column(
        controls=[
            Text(title, size=24, weight=FontWeight.BOLD, color="onSurface"),
            Divider(),
            Text(content, size=16, color="onSurface"),
        ],
        spacing=20,
        expand=True,
    )


class CaseHubView(Row):
    """
    案件詳細画面のハブ。
    左側にサイドバー(NavigationRail)、右側にコンテンツを表示する。
    URLルーティングに基づいてコンテンツを動的に切り替える。
    """

    def __init__(self, page: Page, case_id: int):
        super().__init__(expand=True, spacing=0, vertical_alignment=CrossAxisAlignment.START)
        self.page = page
        self.case_id = case_id

        try:
            self.client_name = get_contracting_party_name(case_id)
        except Exception:
            self.client_name = ""

        self._last_click_time = 0

        # --- 画面インスタンスのキャッシュ ---
        self.views_cache: Dict[str, Control] = {}

        # --- サイドバーの定義 ---
        self.destinations = {
            "overview": {
                "icon": Icons.INFO_OUTLINE,
                "label": "案件概要/相続人",
                "route_suffix": "overview",
                "view_func": lambda: DeceasedDetailView(self.page, self.case_id),
            },
            "tasks": {
                "icon": Icons.TASK_ALT,
                "label": "タスク管理",
                "route_suffix": "tasks",
                "view_func": lambda: TaskManagementView(self.page, self.case_id),
            },
            "bank_reg": {
                "icon": Icons.ACCOUNT_BALANCE,
                "label": "銀行登録",
                "route_suffix": "bank/add",
                "view_func": lambda: BankEditView(self.page, self.case_id),
            },
            "securities_reg": {
                "icon": Icons.ACCOUNT_BALANCE_WALLET,
                "label": "証券登録",
                "route_suffix": "securities/add",
                "view_func": lambda: SecuritiesEditView(self.page, self.case_id),
            },
            "asset_reg": {
                "icon": Icons.HOME_WORK_OUTLINED,
                "label": "不動産登録",
                "route_suffix": "asset/register",
                "view_func": lambda: RealEstateEditView(self.page, self.case_id),
            },
            "freeze_proc": {
                "icon": Icons.LOCK_OUTLINED,
                "label": "凍結手続き",
                "route_suffix": "proc/freeze",
                "view_func": lambda: FreezeProcView(self.page, self.case_id),
            },
            "balance_cert_doc": {
                "icon": Icons.DESCRIPTION_OUTLINED,
                "label": "残証申請書類",
                "route_suffix": "doc/balance_cert",
                "view_func": lambda: BalanceCertDocView(self.page, self.case_id),
            },
            "visit_reserve": {
                "icon": Icons.CALENDAR_MONTH_OUTLINED,
                "label": "来店予約",
                "route_suffix": "reserve/visit",
                "view_func": lambda: VisitReserveSelectBankView(self.page, self.case_id),
            },
            "division_agreement": {
                "icon": Icons.HANDSHAKE,
                "label": "遺産分割協議書",
                "route_suffix": "inheritance/division",
                "view_func": lambda: InheritanceDivisionView(self.page, self.case_id),
            },
            "inheritance_doc": {
                "icon": Icons.GAVEL_OUTLINED,
                "label": "相続届作成",
                "route_suffix": "inheritance/doc",
                "view_func": lambda: InheritanceDocView(self.page, self.case_id),
            },
            "debug_pdf": {
                "icon": Icons.BUG_REPORT,
                "label": "PDF作成テスト",
                "route_suffix": "debug/pdf",
                "view_func": lambda: AnyView(self.page, self.case_id),
            },
        }

        # 初期表示の決定
        current_route = page.route
        initial_key = "overview"

        # URLから初期キーを判定
        for key, dest in self.destinations.items():
            if f"/case/{case_id}/{dest['route_suffix']}" in current_route:
                initial_key = key
                break

        self.selected_key = initial_key
        self.destination_keys = list(self.destinations.keys())
        self.selected_index = self.destination_keys.index(initial_key)

        # --- コンテンツエリアの初期化 ---
        self.main_content_container = Container(
            content=Text("Loading...", color="onSurface"),
            padding=padding.all(20),
            expand=True,
            alignment=alignment.top_left,
        )

        # --- ナビゲーションレールの構築 ---
        self.nav_rail = NavigationRail(
            selected_index=self.selected_index,
            label_type="all",
            on_change=self.on_nav_change,
            min_extended_width=180,
            bgcolor="surfaceVariant",
            destinations=[
                NavigationRailDestination(
                    icon=dest["icon"],
                    label=dest["label"],
                )
                for dest in self.destinations.values()
            ],
        )

        # --- レイアウト構築 ---
        self.controls = [
            self.nav_rail,
            VerticalDivider(width=1, color="outlineVariant"),
            self.main_content_container,
        ]

        # 初期コンテンツのロード（ルート情報を渡す）
        self.route_to_content(current_route, update_ui=False)

    def on_nav_change(self, e):
        """サイドバークリック時の処理"""
        current_time = time.time()
        if current_time - self._last_click_time < 0.2:
            return
        self._last_click_time = current_time

        selected_index = e.control.selected_index
        self.selected_index = selected_index

        key = self.destination_keys[selected_index]
        self.selected_key = key

        # メニュークリック時はサブルートなしでベース画面を表示
        self._update_main_content(key)

        self.page.update()

    def _update_main_content(self, key: str, specific_route: str = None):
        """
        指定されたキーに対応するコンテンツを表示する。
        """
        content_control = None

        # 1. 書類作成画面かつ、特定の銀行ルートが指定されている場合
        if key == "balance_cert_doc" and specific_route:
            smbc_route_suffix = "/smbc"
            mizuho_route_suffix = "/mizuho"

            if specific_route.endswith(smbc_route_suffix):
                content_control = SmbcBalanceDocView(self.page, self.case_id, "0009")
            elif specific_route.endswith(mizuho_route_suffix):
                content_control = MizuhoBalanceDocView(self.page, self.case_id, "0001")

            if content_control is not None:
                self._replace_main_content(content_control)
                return

        # 2. コンテンツの生成またはキャッシュからの取得
        if key != "overview" and key in self.views_cache:
            content_control = self.views_cache[key]
        else:
            try:
                # 💡 エラーハンドリング追加: 画面生成時のエラーをキャッチする
                view_func = self.destinations[key]["view_func"]
                raw_content = view_func()

                if isinstance(raw_content, View):
                    content_control = Column(
                        controls=raw_content.controls, expand=True, scroll="auto"
                    )
                elif isinstance(raw_content, list):
                    content_control = Column(
                        controls=raw_content.controls, expand=True, scroll="auto"
                    )
                else:
                    content_control = raw_content

                if key != "overview":
                    self.views_cache[key] = content_control

            except Exception as e:
                # エラー内容をコンソールとUIに出力
                print(f"❌ Error loading view '{key}': {e}")
                traceback.print_exc()

                content_control = Container(
                    content=Column(
                        [
                            Icon(Icons.ERROR_OUTLINE, size=40, color=Colors.RED),
                            Text(
                                f"画面の読み込み中にエラーが発生しました。\n{str(e)}",
                                color=Colors.RED,
                                size=16,
                            ),
                            Text("コンソールのログを確認してください。", color=Colors.GREY),
                        ],
                        horizontal_alignment="center",
                        alignment="center",
                    ),
                    padding=20,
                    alignment=alignment.center,
                )
                self.page.open(
                    SnackBar(Text(f"エラー: {e}", color=Colors.WHITE), bgcolor=Colors.RED)
                )

        # コンテンツの差し替え
        self._replace_main_content(content_control)

    def _replace_main_content(self, content_control: Control):
        """ヘッダーとコントロールをラップしてメインコンテナを更新するヘルパー"""
        self.main_content_container.content = Column(
            controls=[
                self._create_common_header(),
                Divider(height=10, color=Colors.TRANSPARENT),
                content_control,
            ],
            expand=True,
        )
        self.page.update()

    def _create_common_header(self):
        """共通ヘッダー"""
        return Row(
            [
                ElevatedButton(
                    "📂 案件フォルダを開く",
                    on_click=lambda e: open_case_folder(
                        self.page, self.case_id, get_case_folder_path
                    ),
                    style=ButtonStyle(bgcolor="tertiaryContainer", color="onTertiaryContainer"),
                )
            ]
        )

    def route_to_content(self, route: str, update_ui=True):
        """
        外部からのルート変更指示を受け取り、適切なタブとコンテンツを表示する
        """
        target_key = "overview"

        for key, dest in self.destinations.items():
            route_prefix = f"/case/{self.case_id}/{dest['route_suffix']}"
            if route.startswith(route_prefix):
                target_key = key
                break

        self.selected_key = target_key
        if target_key in self.destination_keys:
            self.selected_index = self.destination_keys.index(target_key)
            self.nav_rail.selected_index = self.selected_index

        self._update_main_content(target_key, specific_route=route)

        if update_ui:
            self.page.update()
