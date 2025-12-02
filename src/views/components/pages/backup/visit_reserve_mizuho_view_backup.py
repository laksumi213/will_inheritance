# /components/pages/visit_reserve_mizuho_view.py

from flet import (
    Colors,
    Column,
    Container,
    Divider,
    Dropdown,
    ElevatedButton,
    FontWeight,
    Page,
    Row,
    SnackBar,
    Text,
    dropdown,
)


class VisitReserveMizuhoView(Column):
    """
    みずほ銀行専用の来店予約ビュー。
    支店と手続きの種類を選択する。
    """

    def __init__(self, page: Page, case_id: int):
        super().__init__(
            expand=True,
            scroll="auto",
            spacing=20,
        )
        self.page = page
        self.case_id = case_id

        # 予約に必要な選択フィールドを初期化
        self.branch_dropdown = self._create_branch_dropdown()
        self.procedure_dropdown = self._create_procedure_dropdown()

        self.controls = [
            Text(
                "🏦 来店予約 - みずほ銀行",
                size=24,
                weight=FontWeight.BOLD,
            ),
            Divider(),
            Text(
                f"案件ID: {self.case_id} の来店予約（みずほ銀行）を行います。",
                size=16,
            ),
            # --- 支店選択コンポーネント ---
            Container(
                content=Column(
                    controls=[
                        Text("1. 予約を行う支店を選択してください:", weight=FontWeight.W_600),
                        self.branch_dropdown,
                    ]
                ),
                padding=15,
                border_radius=10,
                bgcolor=Colors.BLUE_GREY_50,
            ),
            # --- 手続き種類選択コンポーネント ---
            Container(
                content=Column(
                    controls=[
                        Text("2. 行う手続きの種類を選択してください:", weight=FontWeight.W_600),
                        self.procedure_dropdown,
                    ]
                ),
                padding=15,
                border_radius=10,
                bgcolor=Colors.BLUE_GREY_50,
            ),
            Divider(),
            # --- 予約確認ボタン ---
            Row(
                alignment="end",
                controls=[
                    ElevatedButton(
                        "予約日時選択へ進む ➡️",
                        icon="CALENDAR_MONTH",
                        on_click=self._go_to_date_selection,
                        bgcolor=Colors.BLUE_700,
                        color=Colors.WHITE,
                        padding=20,
                    )
                ],
            ),
        ]

    def _create_branch_dropdown(self) -> Dropdown:
        """予約を行う支店を選択するドロップダウンを生成する"""
        return Dropdown(
            label="みずほ銀行 支店名",
            options=[
                dropdown.Option("京橋支店"),
                dropdown.Option("八重洲口支店"),
                dropdown.Option("東京中央支店"),
            ],
            value="京橋支店",  # 初期値
            width=300,
            filled=True,
        )

    def _create_procedure_dropdown(self) -> Dropdown:
        """手続きの種類を選択するドロップダウンを生成する"""
        return Dropdown(
            label="手続きの種類",
            options=[
                dropdown.Option("残高証明書の発行依頼"),  # 初期値
                dropdown.Option("取引明細の発行依頼"),
            ],
            value="残高証明書の発行依頼",  # 初期値
            width=400,
            filled=True,
        )

    def _go_to_date_selection(self, e):
        """
        選択された支店と手続きの種類を引数に、次の日時選択画面へ遷移する。
        """
        selected_branch = self.branch_dropdown.value
        selected_procedure = self.procedure_dropdown.value
        print(f"選択された支店: {selected_branch}")
        print(f"選択された手続き: {selected_procedure}")

        # 今回はデモとして、選択内容をトースト表示して、一つ前の銀行選択に戻るルートを表示します。
        # self.page.snack_bar = Text(
        #     f"次の予約日時選択に進みます。支店: {selected_branch}, 手続き: {selected_procedure}"
        # )
        self.page.open(
            SnackBar(
                content=Text(
                    f"次の予約日時選択に進みます。支店: {selected_branch}, 手続き: {selected_procedure}",
                    color=Colors.WHITE,
                ),
                bgcolor=Colors.GREEN_700,
                duration=2000,
            )
        )
        self.page.update()

        # 画面遷移の例
        # self.page.go(f"/case/{self.case_id}/reserve/mizuho/date_time")
