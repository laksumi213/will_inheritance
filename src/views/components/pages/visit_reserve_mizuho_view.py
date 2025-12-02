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
    Text,
    dropdown,
)

from components.pages.mizuho_visit_reserve_process import (
    start_mizuho_reservation,
    continue_mizuho_reservation,
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
            # --- 予約ボタン群 ---
            Row(
                alignment="spaceBetween", # ボタンを両端に配置
                controls=[
                    # 💡 【要求1】「日時選択へ進む」ボタン: Web自動化ステップ1を起動
                    ElevatedButton(
                        "予約日時選択へ進む ➡️",
                        icon="CALENDAR_MONTH",
                        on_click=self._start_reservation_process, 
                        bgcolor=Colors.BLUE_700,
                        color=Colors.WHITE,
                    ),
                    # 💡 【要求2】「日時選択後に押す」ボタン: Web自動化ステップ2を起動
                    ElevatedButton(
                        "日時選択後に押す",
                        icon="CALENDAR_CHECK",
                        on_click=self._continue_reservation_process, 
                        bgcolor=Colors.GREEN_700,
                        color=Colors.WHITE,
                    ),
                ]
            )
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
            value="京橋支店",
            width=300,
            filled=True,
        )

    def _create_procedure_dropdown(self) -> Dropdown:
        """手続きの種類を選択するドロップダウンを生成する"""
        return Dropdown(
            label="手続きの種類",
            options=[
                dropdown.Option("残高証明書の発行依頼"),
                dropdown.Option("取引明細の発行依頼"),
            ],
            value="残高証明書の発行依頼",
            width=400,
            filled=True,
        )

    def _start_reservation_process(self, e):
        """
        選択内容を取得し、みずほ銀行予約の日程選択画面を表示する自動化処理を開始。
        """
        selected_branch = self.branch_dropdown.value
        selected_procedure = self.procedure_dropdown.value
        
        print(f"選択された支店: {selected_branch}")
        print(f"選択された手続き: {selected_procedure}")

        # Web自動化のステップ1を起動
        start_mizuho_reservation(self.page, self.case_id, selected_branch, selected_procedure)

    def _continue_reservation_process(self, e):
        """
        日時選択後、お客さま情報入力以降の自動化処理を再開。
        """
        # Web自動化のステップ2を起動
        continue_mizuho_reservation(self.page, self.case_id)