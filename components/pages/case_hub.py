# /components/pages/case_hub.py

from flet import (
    AppBar,
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
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

from components.pages.balance_cert_doc import BalanceCertDocView
from components.pages.bank_balance_doc_edit import BankBalanceDocEditView
from components.pages.bank_edit import BankEditView
from components.pages.detail import DeceasedDetailView
from components.pages.freeze_proc_view import FreezeProcView
from components.pages.mizuho_balance_doc_view import MizuhoBalanceDocView
from components.pages.securities_edit import SecuritiesEditView
from components.pages.smbc_balance_doc_view import SmbcBalanceDocView
from components.pages.visit_reserve_select_bank_view import VisitReserveSelectBankView
from services.deceased_service import get_contracting_party_name


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

        # --- 1. 案件概要 / 相続人 (detail.py) ---
        if (
            route.endswith(f"/case/{self.case_id}")
            or route.endswith(f"/case/{self.case_id}/overview")
            or route.startswith(f"/detail/{self.case_id}")
        ):
            return DeceasedDetailView(self.page, self.case_id)

        # --- 2. 銀行口座登録・編集 (bank_edit.py) ---
        # 💡 修正: /bank/add のルートを上部に配置し、他のルートと競合させない
        elif route.endswith("/bank/add"):
            return BankEditView(self.page, self.case_id)

        # --- 💡 凍結手続き (一覧画面) ---
        elif route.endswith("/proc/freeze"):
            return FreezeProcView(self.page, self.case_id)

        # --- 💡 凍結手続き (詳細画面 - 各銀行ごと) ---
        elif route.startswith(f"/case/{self.case_id}/proc/freeze/"):
            # 銀行コードを取得
            bank_code = route.split("/")[-1]
            return PlaceholderView(
                self.page,
                f"凍結連絡詳細 (コード: {bank_code})",
                "ここに電話番号、連絡メモ、TODOなどが表示されます（未実装）",
            )

        elif route.endswith("/securities/add"):
            return SecuritiesEditView(self.page, self.case_id)

        # --- 3. 残高証明申請書類（選択画面） (balance_cert_doc.py) ---
        elif route.endswith("/doc/balance_cert"):
            return BalanceCertDocView(self.page, self.case_id)

        # --- 4. 来店予約（銀行選択画面） ---
        elif route.endswith("/reserve/visit"):
            return VisitReserveSelectBankView(self.page, self.case_id)

        # --- 5. 銀行コードに基づく専用フォーム (残証申請 / 来店予約) ---

        route_parts = route.split("/")
        bank_code = route_parts[-1]  # 最後のセグメントを抽出

        # 5-1. 残証申請書類（編集画面 - 銀行別フォーム）
        if route.startswith(f"/case/{self.case_id}/doc/balance_cert/"):
            if route.startswith(f"/case/{self.case_id}/doc/balance_cert/mizuho/"):
                return MizuhoBalanceDocView(self.page, self.case_id, bank_code)

            elif route.startswith(f"/case/{self.case_id}/doc/balance_cert/smbc/"):
                return SmbcBalanceDocView(self.page, self.case_id, bank_code)

            elif route.startswith(f"/case/{self.case_id}/doc/balance_cert/standard/"):
                return BankBalanceDocEditView(self.page, self.case_id, bank_code)

        # 5-2. 銀行別 来店予約ページ
        elif route.startswith(f"/case/{self.case_id}/reserve/"):
            # 6-1. みずほ銀行 (コード: 0001) 専用ルート
            if route.startswith(f"/case/{self.case_id}/reserve/mizuho"):
                return PlaceholderView(self.page, "みずほ予約フォーム", f"案件ID: {self.case_id}")

            # 6-2. 三井住友銀行 (コード: 0009) 専用ルート
            elif route.startswith(f"/case/{self.case_id}/reserve/smbc"):
                return PlaceholderView(self.page, "三井住友予約フォーム", f"案件ID: {self.case_id}")

            # 6-3. 標準予約フォーム
            elif route.startswith(f"/case/{self.case_id}/reserve/standard/"):
                return PlaceholderView(
                    self.page,
                    f"標準フォーム ({bank_code}) 来店予約",
                    f"案件ID: {self.case_id} / 銀行コード: {bank_code} の予約資料を作成。",
                )

        # --- 99. デフォルト / ルートエラー ---
        return PlaceholderView(self.page, "ページが見つかりません", f"ルート: {route}")

    def _get_index_from_route(self, route):
        """ルートURLから対応するナビゲーションインデックスを計算する"""
        for index, dest in enumerate(self.destinations.values()):
            # 💡 route.startswith() で部分一致を確認
            if route.startswith(dest["route"]):
                return index
        return 0  # 見つからない場合はデフォルトで0 (概要)

    def route_to_content(self, route):
        """画面遷移に応じてメインコンテンツとサイドバーの状態を更新する"""

        # 1. 状態を更新
        self.current_route = route
        self.selected_index = self._get_index_from_route(route)

        # 2. メインコンテンツを再生成
        new_content_candidate = self._get_main_content_for_route(route)

        if new_content_candidate is None:
            new_content_candidate = PlaceholderView(
                self.page, "エラー", f"無効なルートが指定されました: {route}"
            )

        # 3. self.main_content (Columnコントロール) の controls を更新
        self.main_content.controls.clear()

        # DeceasedDetailView は View を返すため、その中身（controls[1].content.controls）を取得する
        if isinstance(new_content_candidate, View):
            if len(new_content_candidate.controls) > 1 and hasattr(
                new_content_candidate.controls[1], "content"
            ):
                content_controls = new_content_candidate.controls[1].content.controls
            else:
                content_controls = (
                    new_content_candidate.controls[0].controls
                    if new_content_candidate.controls
                    else []
                )
        else:
            # BankEditView や PlaceholderView (Column) の controls をそのまま取得
            content_controls = new_content_candidate.controls

        self.main_content.controls.extend(content_controls)

        # 4. 画面を更新（NavigationRailの状態も更新される）
        # 💡 NavigationRail の選択状態を明示的に更新
        if self.nav_rail:
            self.nav_rail.selected_index = self.selected_index

        self.main_content.update()
        # self.page.update()

    def go_to_sub_route(self, e):
        """ナビゲーションレール (サイドバー) クリック時のルーティング"""

        # 1. NavigationRail の選択状態を更新 (見た目をすぐに変えるため)
        selected_index = e.control.selected_index
        self.selected_index = selected_index

        # 2. Page.go() でルーティングを実行
        route = e.control.destinations[selected_index].data
        self.page.go(route)

        # 3. 状態の変更を UI に反映 (NavRailのハイライトを更新)
        # 🚨 HACK: Page.go() の前に update() を実行することで、NavRail の選択状態を瞬時に切り替えさせる
        # これは main.py の router が発火する前に視覚的なフィードバックを与えるために必要です。
        if self.nav_rail:
            self.nav_rail.selected_index = selected_index
        self.page.update()

    def build(self):
        """全体の View を構築"""

        # 💡 初期コンテンツを保持するコンテナを構築
        initial_content_controls = []
        if isinstance(self.main_content, View):
            if len(self.main_content.controls) > 1 and hasattr(
                self.main_content.controls[1], "content"
            ):
                initial_content_controls = self.main_content.controls[1].content.controls
            else:
                initial_content_controls = self.main_content.controls
        else:
            initial_content_controls = self.main_content.controls

        # 既存のDetailViewのコントロールを格納するコンテナ (このコンテナを route_to_content が更新する)
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

        # main_content を self.main_content_container の content にリファレンスを設定し直す
        self.main_content = self.main_content_container.content

        # サイドバー（NavigationRail）
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
        # 💡 NavigationRail インスタンスを保持
        self.nav_rail = nav_rail

        view_controls = [
            AppBar(
                title=Text(f"{self.client_name}の詳細画面"),
                bgcolor=Colors.BLUE_GREY_700,
                leading=IconButton(Icons.ARROW_BACK, on_click=lambda e: self.page.go("/")),
            ),
            Row(
                [
                    self.nav_rail,  # 💡 保持した nav_rail インスタンスを使用
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
