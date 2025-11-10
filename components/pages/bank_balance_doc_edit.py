# /components/pages/bank_balance_doc_edit.py
from flet import (
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    ElevatedButton,
    FontWeight,
    Page,
    Row,
    Text,
)

# from services import bank_service # 必要に応じて銀行詳細情報を取得するサービスをインポート


def BankBalanceDocEditView(page: Page, case_id: int, bank_id: int):
    """
    特定の銀行 (bank_id) の残高証明申請書類を編集する画面ビュー。
    """

    # 💡 ここで bank_id を使って銀行名などの詳細情報を取得する（ここでは省略）
    bank_name = f"銀行ID: {bank_id}"

    view_controls = [
        # AppBarはCaseHubView側で提供されるため、ここではメインコンテンツのColumnのみを返す
        Column(
            controls=[
                Text(
                    f"📝 {bank_name} の残高証明申請書類 編集",
                    size=24,
                    weight=FontWeight.BOLD,
                    color=Colors.BLACK,
                ),
                Divider(),
                Text(f"案件ID: {case_id} / 銀行ID: {bank_id}", size=16, color=Colors.BLUE_GREY_600),
                Container(height=10),
                Text(
                    "ここに残高証明申請に必要な情報（申請日、支店名、口座情報など）を入力するフォームを実装します。",
                    size=14,
                    color=Colors.BLACK87,
                ),
                Container(height=20),
                Row(
                    [
                        ElevatedButton(
                            "戻る",
                            on_click=lambda e: page.go(f"/case/{case_id}/doc/balance_cert"),
                            bgcolor=Colors.GREY_600,
                        ),
                        ElevatedButton(
                            "申請書類を保存・印刷",
                            on_click=lambda e: page.go(f"/case/{case_id}/doc/balance_cert"),
                            bgcolor=Colors.GREEN_700,
                        ),
                    ],
                    spacing=10,
                ),
            ],
            spacing=20,
            expand=True,
            horizontal_alignment=CrossAxisAlignment.START,
        ),
    ]

    # CaseHubViewにロードされるため、Viewとしてではなく直接Columnを返すことが多いため、ここではColumnを返します。
    return view_controls[0]  # Columnコントロールを直接返す
