# src/views/case_hub.py
import time

from flet import (
    ButtonStyle,
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    ElevatedButton,
    Icons,
    NavigationRail,
    NavigationRailDestination,
    Page,
    Row,
    Text,
    VerticalDivider,
    View,
    alignment,
    padding,
)

# 各種ビューのインポート
from src.views.detail import DeceasedDetailView
from src.views.freeze_proc_view import FreezeProcView
from src.views.mizuho_balance_doc_view import MizuhoBalanceDocView
from src.views.securities_edit import SecuritiesEditView
from src.views.smbc_balance_doc_view import SmbcBalanceDocView
from src.views.task_management_view import TaskManagementView
from src.views.visit_reserve_mizuho_view import VisitReserveMizuhoView
from src.views.visit_reserve_select_bank_view import VisitReserveSelectBankView

# サービス・ユーティリティ
from src.services.deceased_service import get_case_folder_path, get_contracting_party_name
from src.utils.file_system import open_case_folder


# 未実装機能用のプレースホルダー
def PlaceholderView(page: Page, title: str, content: str):
    return Column(
        controls=[
            Text(title, size=24, weight="bold"),
            Divider(),
            Text(content, size=16),
            Text(f"Current Route: {page.route}", color=Colors.GREY),
        ],
        spacing=20,
        expand=True,
    )


# ダミー定義（実装ファイルがないもの）
def BalanceCertDocView(page, case_id):
    return PlaceholderView(page, "残高証明書作成", "銀行を選択してください")


def BankEditView(page, case_id):
    return PlaceholderView(page, "銀行口座登録", "銀行口座の登録・編集画面")


def AeonVisitReserveView(page, case_id, code):
    return PlaceholderView(page, "イオン銀行予約", "自動化ロジック")


def SbiShinseiVisitReserveView(page, case_id, code):
    return PlaceholderView(page, "SBI新生銀行予約", "自動化ロジック")


def BankBalanceDocEditView(page, case_id, code):
    return PlaceholderView(page, "標準書類作成", "汎用フォーム")


class CaseHubView(Row):
    """
    案件詳細画面のハブ。左側にサイドバー、右側にコンテンツを表示する。
    """

    def __init__(self, page: Page, case_id: int):
        super().__init__(expand=True, spacing=0, vertical_alignment=CrossAxisAlignment.START)
        self.page = page
        self.case_id = case_id

        self.client_name = get_contracting_party_name(case_id)
        self._last_click_time = 0

        # サイドバーの定義
        self.destinations = {
            "overview": {
                "icon": Icons.INFO_OUTLINE,
                "label": "案件概要/相続人",
                "route": f"/case/{case_id}/overview",
            },
            "tasks": {
                "icon": Icons.TASK_ALT,
                "label": "タスク管理",
                "route": f"/case/{case_id}/tasks",
            },
            "bank_reg": {
                "icon": Icons.ACCOUNT_BALANCE,
                "label": "銀行登録",
                "route": f"/case/{case_id}/bank/add",
            },
            "securities_reg": {
                "icon": Icons.ACCOUNT_BALANCE_WALLET,
                "label": "証券登録",
                "route": f"/case/{case_id}/securities/add",
            },
            "freeze_proc": {
                "icon": Icons.LOCK_OUTLINED,
                "label": "凍結手続き",
                "route": f"/case/{case_id}/proc/freeze",
            },
            "balance_cert_doc": {
                "icon": Icons.DESCRIPTION_OUTLINED,
                "label": "残証申請書類",
                "route": f"/case/{case_id}/doc/balance_cert",
            },
            "visit_reserve": {
                "icon": Icons.CALENDAR_MONTH_OUTLINED,
                "label": "来店予約",
                "route": f"/case/{case_id}/reserve/visit",
            },
            "asset_reg": {
                "icon": Icons.HOME_WORK_OUTLINED,
                "label": "財産登録",
                "route": f"/case/{case_id}/asset/register",
            },
            "inheritance_doc": {
                "icon": Icons.GAVEL_OUTLINED,
                "label": "遺産分割協議書",
                "route": f"/case/{case_id}/inheritance/doc",
            },
        }

        # 現在のルート設定
        self.current_route = page.route
        if not any(self.current_route.startswith(d["route"]) for d in self.destinations.values()):
            # デフォルトへ
            self.current_route = self.destinations["overview"]["route"]

        self.selected_index = self._get_index_from_route(self.current_route)

        # コンテンツエリア
        self.main_content_column = Column(
            controls=[Text("Loading...")],
            expand=True,
            scroll="auto",
            horizontal_alignment=CrossAxisAlignment.START,
            spacing=20,
        )

        self.main_content_container = Container(
            content=self.main_content_column,
            padding=padding.all(20),
            expand=True,
            alignment=alignment.top_left,
        )

        # ナビゲーションレール
        self.nav_rail = NavigationRail(
            selected_index=self.selected_index,
            label_type="all",
            on_change=self.go_to_sub_route,
            min_extended_width=180,
            bgcolor=Colors.BLUE_GREY_50,
            destinations=[
                NavigationRailDestination(
                    icon=dest["icon"],
                    label=Text(dest["label"]),
                    data=dest["route"],
                )
                for dest in self.destinations.values()
            ],
        )

        # レイアウト構築
        self.controls = [
            self.nav_rail,
            VerticalDivider(width=1, color=Colors.GREY_300),
            self.main_content_container,
        ]

        # 初期表示
        self.route_to_content(self.current_route, update_ui=False)

    def _get_index_from_route(self, route):
        for index, dest in enumerate(self.destinations.values()):
            if route.startswith(dest["route"]):
                return index
        return 0

    def go_to_sub_route(self, e):
        """サイドバークリック時の処理"""
        current_time = time.time()
        if current_time - self._last_click_time < 0.3:
            return
        self._last_click_time = current_time

        selected_index = e.control.selected_index
        if selected_index == self.selected_index:
            return

        route = e.control.destinations[selected_index].data
        self.page.go(route)

    def route_to_content(self, route, update_ui=True):
        """ルートに基づいてコンテンツを切り替える"""
        self.current_route = route
        self.selected_index = self._get_index_from_route(route)

        if self.nav_rail:
            self.nav_rail.selected_index = self.selected_index

        # コンテンツの取得
        content_obj = self._get_main_content_for_route(route)

        # コントロールリストの抽出
        content_controls = self._extract_controls(content_obj)

        # UI構築
        self.main_content_column.controls.clear()

        # 共通ヘッダー（フォルダボタン）
        self.main_content_column.controls.append(
            Row(
                [
                    ElevatedButton(
                        "📂 案件フォルダを開く",
                        on_click=lambda e: open_case_folder(
                            self.page, self.case_id, get_case_folder_path
                        ),
                        style=ButtonStyle(bgcolor=Colors.BLUE_50, color=Colors.BLUE_800),
                    )
                ]
            )
        )
        self.main_content_column.controls.append(Divider(height=10, color=Colors.TRANSPARENT))

        # メインコンテンツ追加
        self.main_content_column.controls.extend(content_controls)

        if update_ui:
            self.page.update()

    def _extract_controls(self, content_obj):
        """ViewやControlから表示用コントロールリストを抽出する"""
        if isinstance(content_obj, View):
            # Viewの場合、AppBarを除いた中身を取得する（簡易実装）
            # 通常 View -> controls リストを持つ
            return content_obj.controls
        elif isinstance(content_obj, Column):
            return content_obj.controls
        elif isinstance(content_obj, Container):
            return [content_obj]
        elif isinstance(content_obj, list):
            return content_obj
        else:
            return [content_obj]

    def _get_main_content_for_route(self, route):
        """ルートに応じたViewオブジェクトを返す"""
        # 1. 案件概要
        if route.endswith(f"/case/{self.case_id}/overview") or route.startswith(
            f"/detail/{self.case_id}"
        ):
            return DeceasedDetailView(self.page, self.case_id)

        # 2. タスク管理
        elif route.endswith("/tasks"):
            return TaskManagementView(self.page, self.case_id)

        # 3. 銀行登録
        elif route.endswith("/bank/add"):
            return BankEditView(self.page, self.case_id)

        # 4. 証券登録
        elif route.endswith("/securities/add"):
            return SecuritiesEditView(self.page, self.case_id)

        # 5. 凍結手続き
        elif route.endswith("/proc/freeze"):
            return FreezeProcView(self.page, self.case_id)
        elif route.startswith(f"/case/{self.case_id}/proc/freeze/"):
            code = route.split("/")[-1]
            return PlaceholderView(self.page, f"凍結詳細: {code}", "詳細画面")

        # 6. 残高証明書
        elif route.endswith("/doc/balance_cert"):
            return BalanceCertDocView(self.page, self.case_id)

        elif route.startswith(f"/case/{self.case_id}/doc/balance_cert/"):
            if "mizuho" in route:
                return MizuhoBalanceDocView(self.page, self.case_id, "0001")
            elif "smbc" in route:
                return SmbcBalanceDocView(self.page, self.case_id, "0009")
            else:
                return BankBalanceDocEditView(self.page, self.case_id, "standard")

        # 7. 来店予約
        elif route.endswith("/reserve/visit"):
            return VisitReserveSelectBankView(self.page, self.case_id)

        elif route.startswith(f"/case/{self.case_id}/reserve/"):
            if "mizuho" in route:
                return VisitReserveMizuhoView(self.page, self.case_id)
            elif "aeon" in route:
                return AeonVisitReserveView(self.page, self.case_id, "0040")
            elif "sbi" in route:
                return SbiShinseiVisitReserveView(self.page, self.case_id, "0397")
            else:
                return PlaceholderView(self.page, "来店予約", "選択された銀行の予約フォーム")

        return PlaceholderView(self.page, "Not Found", f"Route: {route}")
