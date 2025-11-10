# /components/pages/balance_cert_doc.py
from flet import (
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    ElevatedButton,
    FontWeight,
    Icons,
    Page,
    Text,
    border,
)

from services import bank_service  # 銀行リストを取得するサービスをインポート


def BalanceCertDocView(page: Page, case_id: int):
    """
    残高証明申請書類作成の選択画面ビュー。
    案件に紐づく銀行リストを表示し、銀行ごとの詳細編集画面へ遷移させる。
    """

    # --- サービス層から銀行リストを取得 ---
    # 仮の関数名: get_banks_by_case_id (実サービス層に依存)
    banks = bank_service.get_banks_by_case_id(case_id)

    # 案件に銀行が登録されていない場合のコントロール
    no_banks_content = Container(
        content=Column(
            [
                Text("⚠️ 銀行情報が登録されていません。", size=18, color=Colors.RED_700),
                Text(
                    "先に「銀行登録」画面で銀行口座情報を登録してください。",
                    size=14,
                    color=Colors.BLACK54,
                ),
            ],
            horizontal_alignment=CrossAxisAlignment.START,
        ),
        padding=20,
        border=border.all(1, Colors.RED_100),
        bgcolor=Colors.RED_50,
        width=500,
    )

    # 銀行リスト表示用のコントロールを生成
    bank_list_controls = Column(spacing=10)

    # 銀行ごとの編集ボタンを作成する関数
    def create_bank_button(bank_name: str, bank_id: int):
        # 💡 銀行ごとの残証申請書類編集画面への遷移関数
        # ルート例: /case/{case_id}/doc/balance_cert/{bank_id}
        def go_to_edit_page(e):
            page.go(f"/case/{case_id}/doc/balance_cert/{bank_id}")

        return Container(
            content=ElevatedButton(
                f"📄 {bank_name} の残高証明書 申請書類を作成・編集",
                icon=Icons.EDIT_DOCUMENT,
                on_click=go_to_edit_page,
                style=ElevatedButton.style_from(
                    bgcolor=Colors.BLUE_500,
                    padding={"vertical": 15, "horizontal": 20},
                    shape={"borderRadius": 8},
                ),
            ),
            width=500,
        )

    if banks:
        # 銀行リストが存在する場合、ボタンを生成
        for bank in banks:
            # bankオブジェクトが name と id を持つと仮定
            bank_name = bank.name
            bank_id = bank.id
            bank_list_controls.controls.append(create_bank_button(bank_name, bank_id))
    else:
        # 銀行リストがない場合は、警告メッセージを表示
        bank_list_controls.controls.append(no_banks_content)

    # --- メインコンテンツの定義 ---
    return Column(
        controls=[
            Text("📄 残証申請書類作成", size=24, weight=FontWeight.BOLD, color=Colors.BLACK),
            Divider(),
            Text("残高証明書の申請を行う銀行を選択してください。", size=16, color=Colors.BLACK87),
            Container(height=10),  # スペーサー
            bank_list_controls,  # 銀行ボタンリスト/警告メッセージ
        ],
        spacing=20,
        expand=True,
        horizontal_alignment=CrossAxisAlignment.START,
    )
