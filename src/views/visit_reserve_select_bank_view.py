# src/views/visit_reserve_select_bank_view.py
from flet import (
    Colors,
    Column,
    Container,
    Divider,
    ElevatedButton,
    MainAxisAlignment,
    Page,
    Row,
    Text,
    border,
)

from src.services.deceased_service import get_financial_asset_by_case


class VisitReserveSelectBankView(Column):
    def __init__(self, page: Page, case_id: int):
        super().__init__(expand=True, scroll="auto", spacing=20)
        self.page = page
        self.case_id = case_id

        assets = get_financial_asset_by_case(case_id)
        unique = {}
        for a in assets:
            if a.get("bank_code"):
                unique[a["bank_code"]] = a.get("bank_name")

        btn_col = Column(spacing=10)
        if unique:
            for code, name in unique.items():
                btn_col.controls.append(
                    Container(
                        content=Row(
                            [
                                Text(f"🏦 {name}", weight="bold"),
                                ElevatedButton(
                                    "予約へ", on_click=lambda e, c=code: self._go_reserve(c)
                                ),
                            ],
                            alignment=MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=15,
                        bgcolor=Colors.WHITE,
                        border=border.all(1, Colors.GREY_300),
                    )
                )
        else:
            btn_col.controls.append(Text("銀行が見つかりません"))

        self.controls = [Text("📅 来店予約 - 銀行選択", size=24, weight="bold"), Divider(), btn_col]

    def _go_reserve(self, code):
        if code == "0001":
            self.page.go(f"/case/{self.case_id}/reserve/mizuho")
        else:
            self.page.go(f"/case/{self.case_id}/reserve/standard/{code}")
