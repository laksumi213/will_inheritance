# src/views/freeze_proc_view.py
from flet import (
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    ElevatedButton,
    FontWeight,
    Icon,
    Icons,
    MainAxisAlignment,
    Page,
    Row,
    Text,
    border,
)

from src.services.deceased_service import get_financial_asset_by_case


class FreezeProcView(Column):
    def __init__(self, page: Page, case_id: int):
        super().__init__(
            expand=True, scroll="auto", spacing=20, horizontal_alignment=CrossAxisAlignment.START
        )
        self.page = page
        self.case_id = case_id
        self.controls = [
            Text("🔒 口座凍結のご連絡", size=24, weight=FontWeight.BOLD),
            Divider(),
            Text("登録済み金融機関一覧（凍結連絡用）", size=16),
            self._create_list(),
        ]

    def _create_list(self):
        assets = get_financial_asset_by_case(self.case_id)
        unique = {}
        for a in assets:
            if a.get("bank_code"):
                unique[a["bank_code"]] = a.get("bank_name")

        if not unique:
            return Container(Text("金融資産が登録されていません", color=Colors.RED), padding=20)

        col = Column(spacing=10)
        for code, name in unique.items():
            col.controls.append(
                Container(
                    content=Row(
                        [
                            Row(
                                [
                                    Icon(Icons.ACCOUNT_BALANCE),
                                    Column(
                                        [Text(name, weight="bold"), Text(f"Code: {code}", size=12)]
                                    ),
                                ]
                            ),
                            ElevatedButton(
                                "詳細",
                                icon=Icons.ARROW_FORWARD,
                                on_click=lambda e, c=code: self.page.go(
                                    f"/case/{self.case_id}/proc/freeze/{c}"
                                ),
                            ),
                        ],
                        alignment=MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=15,
                    bgcolor=Colors.WHITE,
                    border_radius=5,
                    border=border.all(1, Colors.GREY_300),
                )
            )
        return col
