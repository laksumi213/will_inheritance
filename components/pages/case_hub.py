# /components/pages/case_hub.py

from flet import (
    AppBar,
    ButtonStyle,
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    ElevatedButton,
    IconButton,
    Icons,
    NavigationRail,
    NavigationRailDestination,
    Page,
    Row,
    Text,
    VerticalDivider,
    View,
)

from components.pages.aeon_visit_reserve_view import AeonVisitReserveView
from components.pages.balance_cert_doc import BalanceCertDocView
from components.pages.bank_balance_doc_edit import BankBalanceDocEditView
from components.pages.bank_edit import BankEditView
from components.pages.detail import DeceasedDetailView
from components.pages.freeze_proc_view import FreezeProcView
from components.pages.mizuho_balance_doc_view import MizuhoBalanceDocView
from components.pages.securities_edit import SecuritiesEditView
from components.pages.sbi_shinsei_visit_reserve_view import SbiShinseiVisitReserveView # 💡 追加
from components.pages.smbc_balance_doc_view import SmbcBalanceDocView
from components.pages.task_management_view import TaskManagementView
from components.pages.visit_reserve_select_bank_view import VisitReserveSelectBankView
from components.utils.file_system import open_case_folder
from services.deceased_service import get_contracting_party_name, get_case_folder_path_service


# 💡 メインコンテンツのダミービュー（後で実装）
def PlaceholderView(page: Page, title: str, content: str):
    """機能ごとのプレースホルダービュー"""
    return Column(
        controls=[
            Text(title, size=24, weight="bold"),
            Divider(),
            Text(content, size=16),
            Text(f"現在の案件ID: {page.route.split('/')[-1]}", color=Colors.BLUE_GREY_600),
        ],
        spacing=20,
        expand=True,
    )


class CaseHubView:
    def __init__(self, page: Page, case_id: int):
        self.page = page
        self.case_id = case_id

        self.client_name = get_contracting_party_name(case_id)

        # 💡 各機能のルーティングと表示名
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
                "label": "残証申請書類作成",
                "route": f"/case/{case_id}/doc/balance_cert",
            },
            "visit_reserve": {
                "icon": Icons.CALENDAR_MONTH_OUTLINED,
                "label": "来店予約",
                "route": f"/case/{case_id}/reserve/visit",
            },
            "asset_reg": {
                "icon": Icons.HOME_WORK_OUTLINED,
                "label": "財産登録/目録作成",
                "route": f"/case/{case_id}/asset/register",
            },
            "inheritance_doc": {
                "icon": Icons.GAVEL_OUTLINED,  # 遺産分割協議書
                "label": "遺産分割協議書作成",
                "route": f"/case/{case_id}/inheritance/doc",
            },
            "bank_unfreeze": {
                "icon": Icons.KEY_OUTLINED,
                "label": "銀行解約手続き",
                "route": f"/case/{case_id}/proc/unfreeze",
            },
            "securities_transfer": {
                "icon": Icons.TRANSFER_WITHIN_A_STATION_OUTLINED,
                "label": "証券移管手続き",
                "route": f"/case/{case_id}/proc/transfer",
            },
        }

        # 最初の画面をデフォルトとして設定
        self.current_route = page.route or self.destinations["overview"]["route"]
        self.selected_index = self._get_index_from_route(self.current_route)
        self.main_content = self._get_main_content_for_route(
            self.current_route
        )  # 初期コンテンツをルートに基づいてロード

        # 💡 NavigationRail のインスタンスを保持するための変数
        self.nav_rail = None

    def _get_main_content_for_route(self, route):
        """
        現在のルートに基づいて、表示すべきメインコンテンツのFletコントロールを返す。
        """

        # --- 1. 案件概要 / 相続人 ---
        if (
            route.endswith(f"/case/{self.case_id}")
            or route.endswith(f"/case/{self.case_id}/overview")
            or route.startswith(f"/detail/{self.case_id}")
        ):
            return DeceasedDetailView(self.page, self.case_id)

        # --- 💡 タスク管理 ---
        elif route.endswith("/tasks"):
            return TaskManagementView(self.page, self.case_id)

        # --- 2. 銀行口座登録・編集 ---
        elif route.endswith("/bank/add"):
            return BankEditView(self.page, self.case_id)

        # --- 凍結手続き ---
        elif route.endswith("/proc/freeze"):
            return FreezeProcView(self.page, self.case_id)

        elif route.startswith(f"/case/{self.case_id}/proc/freeze/"):
            bank_code = route.split("/")[-1]
            return PlaceholderView(
                self.page,
                f"凍結連絡詳細 (コード: {bank_code})",
                "ここに電話番号、連絡メモ、TODOなどが表示されます（未実装）",
            )

        elif route.endswith("/securities/add"):
            return SecuritiesEditView(self.page, self.case_id)

        # --- 残高証明申請書類 ---
        elif route.endswith("/doc/balance_cert"):
            return BalanceCertDocView(self.page, self.case_id)

        # --- 来店予約 ---
        elif route.endswith("/reserve/visit"):
            return VisitReserveSelectBankView(self.page, self.case_id)

        # --- 銀行コードに基づく専用フォーム ---
        route_parts = route.split("/")
        bank_code = route_parts[-1]

        if route.startswith(f"/case/{self.case_id}/doc/balance_cert/"):
            if route.startswith(f"/case/{self.case_id}/doc/balance_cert/mizuho/"):
                return MizuhoBalanceDocView(self.page, self.case_id, bank_code)
            elif route.startswith(f"/case/{self.case_id}/doc/balance_cert/smbc/"):
                return SmbcBalanceDocView(self.page, self.case_id, bank_code)
            elif route.startswith(f"/case/{self.case_id}/doc/balance_cert/standard/"):
                return BankBalanceDocEditView(self.page, self.case_id, bank_code)

        elif route.startswith(f"/case/{self.case_id}/reserve/"):
            if route.startswith(f"/case/{self.case_id}/reserve/mizuho"):
                return PlaceholderView(self.page, "みずほ予約フォーム", f"案件ID: {self.case_id}")
            elif route.startswith(f"/case/{self.case_id}/reserve/smbc"):
                return PlaceholderView(self.page, "三井住友予約フォーム", f"案件ID: {self.case_id}")
            elif route.startswith(f"/case/{self.case_id}/reserve/aeon"):
                return AeonVisitReserveView(self.page, self.case_id, "0040")
            elif route.startswith(f"/case/{self.case_id}/reserve/sbi_shinsei"):
                # 💡 SBI新生銀行専用ルート
                return SbiShinseiVisitReserveView(self.page, self.case_id, "0397")
            elif route.startswith(f"/case/{self.case_id}/reserve/standard/"):
                return PlaceholderView(
                    self.page,
                    f"標準フォーム ({bank_code}) 来店予約",
                    f"案件ID: {self.case_id} / 銀行コード: {bank_code} の予約資料を作成。",
                )

        # --- 99. デフォルト ---
        return PlaceholderView(self.page, "ページが見つかりません", f"ルート: {route}")

    def _get_index_from_route(self, route):
        for index, dest in enumerate(self.destinations.values()):
            if route.startswith(dest["route"]):
                return index
        return 0

    def route_to_content(self, route):
        self.current_route = route
        self.selected_index = self._get_index_from_route(route)
        new_content_candidate = self._get_main_content_for_route(route)

        if new_content_candidate is None:
            new_content_candidate = PlaceholderView(
                self.page, "エラー", f"無効なルートが指定されました: {route}"
            )

        # --- 💡 「案件フォルダを開く」ボタンを常に上部に配置するロジック ---

        # 1. コンテンツのリストをクリア
        self.main_content.controls.clear()

        # 2. 共通ヘッダー（フォルダボタン）を作成
        folder_button_row = Row(
            [
                ElevatedButton(
                    "📂 案件フォルダを開く",
                    on_click=lambda e: open_case_folder(
                        page=self.page,
                        case_id=self.case_id,
                        get_path_service=get_case_folder_path_service,
                    ),
                    style=ButtonStyle(
                        bgcolor=Colors.BLUE_50,
                        color=Colors.BLUE_800,
                        elevation=0,
                    ),
                )
            ],
            alignment="start",
        )

        # 3. ヘッダーを追加
        self.main_content.controls.append(folder_button_row)
        self.main_content.controls.append(Divider(height=10, color=Colors.TRANSPARENT))

        # 4. メインコンテンツを展開して追加
        if isinstance(new_content_candidate, View):
            # Viewの場合は内部のコントロールを取り出す（AppBarなどは無視されることに注意）
            # DeceasedDetailViewなどの完全なView構造を持つものは、内部構造に合わせて調整が必要
            # ここでは簡易的に controls を展開する
            if len(new_content_candidate.controls) > 1 and hasattr(
                new_content_candidate.controls[1], "content"
            ):
                # Scaffold構造 (AppBar, Container(content=Column)) の場合
                content_controls = new_content_candidate.controls[1].content.controls
            else:
                content_controls = (
                    new_content_candidate.controls[0].controls
                    if new_content_candidate.controls
                    else []
                )
        else:
            # Column などのコントロールの場合
            content_controls = new_content_candidate.controls

        self.main_content.controls.extend(content_controls)

        if self.nav_rail:
            self.nav_rail.selected_index = self.selected_index

        self.main_content.update()

    def go_to_sub_route(self, e):
        selected_index = e.control.selected_index
        self.selected_index = selected_index
        route = e.control.destinations[selected_index].data
        self.page.go(route)
        if self.nav_rail:
            self.nav_rail.selected_index = selected_index
        self.page.update()

    def build(self):
        initial_content_controls = []
        # 初期表示時も同様のロジックでコンテンツを取得
        temp_content = self.main_content

        # 💡 初期化時もフォルダボタンを追加する
        folder_button_row = Row(
            [
                ElevatedButton(
                    "📂 案件フォルダを開く",
                    on_click=lambda e: open_case_folder(
                        page=self.page,
                        case_id=self.case_id,
                        get_path_service=get_case_folder_path_service,
                    ),
                    style=ButtonStyle(
                        bgcolor=Colors.BLUE_50,
                        color=Colors.BLUE_800,
                        elevation=0,
                    ),
                )
            ],
            alignment="end",
        )
        initial_content_controls.append(folder_button_row)
        initial_content_controls.append(Divider(height=10, color=Colors.TRANSPARENT))

        if isinstance(temp_content, View):
            if len(temp_content.controls) > 1 and hasattr(temp_content.controls[1], "content"):
                initial_content_controls.extend(temp_content.controls[1].content.controls)
            else:
                initial_content_controls.extend(temp_content.controls)
        else:
            initial_content_controls.extend(temp_content.controls)

        self.main_content_container = Container(
            content=Column(
                controls=initial_content_controls,
                expand=True,
                scroll="auto",
                horizontal_alignment=CrossAxisAlignment.START,
                spacing=20,
            ),
            padding=20,
            expand=True,
        )

        self.main_content = self.main_content_container.content

        nav_rail = NavigationRail(
            selected_index=self.selected_index,
            label_type="all",
            on_change=lambda e: self.go_to_sub_route(e),
            min_extended_width=180,
            destinations=[
                NavigationRailDestination(
                    icon=dest["icon"],
                    label=dest["label"],
                    data=dest["route"],
                )
                for dest in self.destinations.values()
            ],
        )
        self.nav_rail = nav_rail

        view_controls = [
            AppBar(
                title=Text(f"{self.client_name}の詳細画面"),
                bgcolor=Colors.BLUE_GREY_700,
                leading=IconButton(Icons.ARROW_BACK, on_click=lambda e: self.page.go("/")),
            ),
            Row(
                [
                    self.nav_rail,
                    VerticalDivider(width=1),
                    self.main_content_container,
                ],
                vertical_alignment=CrossAxisAlignment.START,
                expand=True,
            ),
        ]

        app_view = View(
            f"/case/{self.case_id}/.*|/detail/{self.case_id}",
            view_controls,
        )

        setattr(app_view, "_hub_instance", self)
        return app_view