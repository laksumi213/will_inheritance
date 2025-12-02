# src/views/visit_reserve_mizuho_view.py
from flet import Colors, Column, Divider, Dropdown, ElevatedButton, Page, Row, Text, dropdown
from src.views.mizuho_visit_reserve_process import (
    continue_mizuho_reservation,
    start_mizuho_reservation,
)


class VisitReserveMizuhoView(Column):
    def __init__(self, page: Page, case_id: int):
        super().__init__(expand=True, scroll="auto", spacing=20)
        self.page = page
        self.case_id = case_id

        self.branch_dd = Dropdown(
            label="支店",
            options=[dropdown.Option("京橋支店"), dropdown.Option("東京中央支店")],
            value="京橋支店",
        )
        self.proc_dd = Dropdown(
            label="手続き",
            options=[dropdown.Option("残高証明書"), dropdown.Option("取引明細")],
            value="残高証明書",
        )

        self.controls = [
            Text("🏦 みずほ銀行 来店予約", size=24, weight="bold"),
            Divider(),
            self.branch_dd,
            self.proc_dd,
            Row(
                [
                    ElevatedButton(
                        "日時選択へ (Step1)",
                        icon="CALENDAR_MONTH",
                        on_click=self._step1,
                        bgcolor=Colors.BLUE_700,
                        color=Colors.WHITE,
                    ),
                    ElevatedButton(
                        "入力再開 (Step2)",
                        icon="CHECK",
                        on_click=self._step2,
                        bgcolor=Colors.GREEN_700,
                        color=Colors.WHITE,
                    ),
                ],
                spacing=20,
            ),
        ]

    def _step1(self, e):
        start_mizuho_reservation(self.page, self.case_id, self.branch_dd.value, self.proc_dd.value)

    def _step2(self, e):
        continue_mizuho_reservation(self.page, self.case_id)
