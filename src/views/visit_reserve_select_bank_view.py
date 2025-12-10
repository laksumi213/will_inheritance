# src/views/visit_reserve_select_bank_view.py
from flet import (
    Column,
    Divider,
    ElevatedButton,
    Page,
    Text,
    FontWeight,
    ListTile,
    Icon,
    Icons,
    RoundedRectangleBorder,
    Container,
    Colors
)

from src.services.deceased_service import get_financial_asset_by_case


class VisitReserveSelectBankView(Column):
    def __init__(self, page: Page, case_id: int):
        super().__init__(expand=True, scroll="auto", spacing=20)
        self.page = page
        self.case_id = case_id

        # 資産データの取得
        assets = get_financial_asset_by_case(case_id)
        unique = {}
        for a in assets:
            if a.get("bank_code"):
                unique[a["bank_code"]] = a.get("bank_name")

        # 銀行リストの生成
        btn_col = Column(spacing=10)
        if unique:
            for code, name in unique.items():
                btn_col.controls.append(
                    ListTile(
                        leading=Icon(Icons.ACCOUNT_BALANCE, color="primary"),
                        title=Text(
                            f"{name}", 
                            color="onSurface",
                            weight=FontWeight.W_500
                        ),
                        subtitle=Text(f"銀行コード: {code}", size=12),
                        trailing=ElevatedButton(
                            "予約へ",
                            width=140, # 押しやすさを考慮して幅を維持
                            bgcolor="primaryContainer",
                            color="onPrimaryContainer",
                            on_click=lambda e, c=code: self._go_reserve(c)
                        ),
                        bgcolor="surfaceVariant",
                        shape=RoundedRectangleBorder(radius=5),
                    )
                )
        else:
            btn_col.controls.append(
                Container(
                    Text("銀行が見つかりません", color=Colors.ERROR),
                    padding=20
                )
            )

        self.controls = [
            Text(
                "📅 来店予約 - 銀行選択", 
                size=24, 
                weight=FontWeight.BOLD, 
                color="onSurface"
            ), 
            Divider(), 
            btn_col
        ]

    def _go_reserve(self, code):
        if code == "0001":
            self.page.go(f"/case/{self.case_id}/reserve/mizuho")
        else:
            self.page.go(f"/case/{self.case_id}/reserve/standard/{code}")