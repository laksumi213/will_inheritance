# src/views/freeze_proc_view.py
from flet import (
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    ElevatedButton,
    FontWeight,
    Icon,
    Icons,
    Page,
    Text,
    ListTile,
    RoundedRectangleBorder,
    Colors,
    padding
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
            Text(
                "🔒 口座凍結のご連絡", 
                size=24, 
                weight=FontWeight.BOLD, 
                color="onSurface"
            ),
            Divider(),
            Text(
                "登録済み金融機関一覧（凍結連絡用）", 
                size=16,
                color="onSurface"
            ),
            self._create_list(),
        ]

    def _create_list(self):
        assets = get_financial_asset_by_case(self.case_id)
        unique = {}
        for a in assets:
            if a.get("bank_code"):
                unique[a["bank_code"]] = a.get("bank_name")

        if not unique:
            return Container(
                Text("金融資産が登録されていません", color=Colors.ERROR), 
                padding=padding.all(20)
            )

        col = Column(spacing=10)
        for code, name in unique.items():
            col.controls.append(
                ListTile(
                    leading=Icon(Icons.ACCOUNT_BALANCE, color="primary"),
                    title=Text(
                        f"{name}", 
                        color="onSurface", 
                        weight=FontWeight.W_500
                    ),
                    subtitle=Text(f"Code: {code}", size=12),
                    trailing=ElevatedButton(
                        "詳細",
                        icon=Icons.ARROW_FORWARD,
                        width=140, # 押しやすさを考慮して幅を維持
                        bgcolor="primaryContainer",
                        color="onPrimaryContainer",
                        on_click=lambda e, c=code: self.page.go(
                            f"/case/{self.case_id}/proc/freeze/{c}"
                        ),
                    ),
                    bgcolor="surfaceVariant",
                    shape=RoundedRectangleBorder(radius=5),
                )
            )
        return col