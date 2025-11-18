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
from components.pages.mizuho_balance_doc_view import MizuhoBalanceDocView
from components.pages.smbc_balance_doc_view import SmbcBalanceDocView
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
        elif route.endswith("/bank/add"):
            return BankEditView(self.page, self.case_id)

        # --- 3. 残高証明申請書類（選択画面） (balance_cert_doc.py) ---
        elif route.endswith("/doc/balance_cert"):
            return BalanceCertDocView(self.page, self.case_id)

        # --- 4. 残高証明申請書類（編集画面 - 銀行別フォーム） ---

        # URLの最後のセグメント（銀行コード）を取得するための共通処理
        route_parts = route.split("/")
        bank_code = route_parts[-1]

        # 4-1. みずほ銀行 (コード: 0001) 専用ルート
        if route.startswith(f"/case/{self.case_id}/doc/balance_cert/mizuho/"):
            return MizuhoBalanceDocView(self.page, self.case_id, bank_code)
            # return PlaceholderView(
            #     self.page,
            #     "みずほ銀行 (0001) 専用フォーム",
            #     f"案件ID: {self.case_id} / 銀行コード: {bank_code}",
            # )

        # 4-2. 三井住友銀行 (コード: 0009) 専用ルート
        elif route.startswith(f"/case/{self.case_id}/doc/balance_cert/smbc/"):
            return SmbcBalanceDocView(self.page, self.case_id, bank_code)
            # return PlaceholderView(
            #     self.page,
            #     "三井住友銀行 (0009) 専用フォーム",
            #     f"案件ID: {self.case_id} / 銀行コード: {bank_code}",
            # )

        # 4-3. 標準フォーム（上記以外の銀行）ルート
        elif route.startswith(f"/case/{self.case_id}/doc/balance_cert/standard/"):
            # 💡 銀行コードを引数として渡し、BankBalanceDocEditView を標準フォームとして利用
            return BankBalanceDocEditView(self.page, self.case_id, bank_code)

        # --- 5. その他のプレースホルダー/フォールバック ---
        # (ここでは、元のコードになかったタスクや資料のルーティングは省略し、デフォルトを返します)

        # 💡 デフォルト / ルートエラー
        return PlaceholderView(self.page, "ページが見つかりません", f"ルート: {route}")

    # def _get_main_content_for_route(self, route):
    #     """ルーティングパスに基づいてメインコンテンツを切り替える"""
    #     if route.startswith(f"/detail/{self.case_id}"):
    #         return DeceasedDetailView(self.page, self.case_id)

    #     elif route.endswith("/bank/add"):
    #         return BankEditView(self.page, self.case_id)

    #     elif route.endswith("/securities/add"):
    #         return PlaceholderView(self.page, "📈 証券登録", "新しい証券口座を登録します。")

    #     elif route.endswith("/proc/freeze"):
    #         return PlaceholderView(
    #             self.page,
    #             "🔒 凍結手続き",
    #             "口座凍結の進捗を管理します。",
    #         )
    #     elif route.endswith("/doc/balance_cert"):
    #         return BalanceCertDocView(self.page, self.case_id)

    #     # 💡 残証申請書類編集 (特定の銀行IDを含む場合)
    #     # ルート例: /case/1/doc/balance_cert/101
    #     elif (
    #         route.startswith(f"/case/{self.case_id}/doc/balance_cert/")
    #         and len(route.split("/")) == 6
    #     ):
    #         try:
    #             # bank_id をルートの末尾から抽出
    #             bank_id = int(route.split("/")[-1])
    #             return BankBalanceDocEditView(self.page, self.case_id, bank_id)
    #         except ValueError:
    #             # bank_id が数値でない場合はエラーとして銀行選択画面に戻る
    #             return BalanceCertDocView(self.page, self.case_id)

    #     elif route.endswith("/reserve/visit"):
    #         return PlaceholderView(
    #             self.page,
    #             "📅 来店予約",
    #             "金融機関や関係者との来店・訪問予約を管理します。",
    #         )
    #     elif route.endswith("/asset/register"):
    #         return PlaceholderView(
    #             self.page,
    #             "💰 財産登録/目録作成",
    #             "不動産やその他財産の登録、目録作成を行います。",
    #         )
    #     elif route.endswith("/inheritance/doc"):
    #         return PlaceholderView(
    #             self.page, "📝 遺産分割協議書作成", "遺産分割の決定と文書化を行います。"
    #         )
    #     elif route.endswith("/proc/unfreeze"):
    #         return PlaceholderView(
    #             self.page,
    #             "🔑 銀行解約手続き",
    #             "凍結解除後の銀行口座解約手続きの進捗を管理します。",
    #         )
    #     elif route.endswith("/proc/transfer"):
    #         return PlaceholderView(
    #             self.page,
    #             "➡️ 証券移管手続き",
    #             "証券口座の有価証券移管手続きの進捗を管理します。",
    #         )
    #     else:
    #         # デフォルトで概要ページを返す
    #         return DeceasedDetailView(self.page, self.case_id)

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
