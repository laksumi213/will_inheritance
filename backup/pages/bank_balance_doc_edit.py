# /components/pages/bank_balance_doc_edit.py
from flet import (
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    ElevatedButton,
    FontWeight,
    MainAxisAlignment,  # Rowのalignmentで使用
    Page,
    Row,
    Text,
    TextField,
    border,
)

# 💡 銀行コードで全口座情報を取得する関数をインポート
from services.deceased_service import get_financial_assets_by_bank_code

# 💡 TextFieldのグローバル定義（フォーム部品）
date_of_application_field = TextField(label="申請基準日", width=200, value="死亡日", read_only=True)
branch_name_for_doc_field = TextField(label="申請先支店名 (任意)", width=300)
notes_field = TextField(
    label="申請に関する特記事項", multiline=True, min_lines=3, max_lines=5, width=600
)


def BankBalanceDocEditView(page: Page, case_id: int, bank_id_or_code: str):
    """
    特定の銀行コードに紐づく全ての口座の残高証明申請書類を編集する画面ビュー。
    """

    # 💡 銀行コードを取得し、該当する全口座情報を取得する
    route_parts = page.route.split("/")

    if route_parts[-2] == "bank_code":
        bank_code = route_parts[-1]

        # サービス層から同じ銀行コードを持つ全ての口座情報を取得
        assets = get_financial_assets_by_bank_code(case_id, bank_code)

        if assets:
            first_asset = assets[0]
            bank_name_display = first_asset.get("bank_name", f"コード: {bank_code}")

            # 口座情報のサマリーを作成
            account_list_controls = Column(spacing=5, horizontal_alignment=CrossAxisAlignment.START)
            for asset in assets:
                branch = asset.get("branch_name", "N/A") or "支店名なし"
                account_num = asset.get("account_number", "N/A")
                balance = (
                    f"¥{asset.get('balance', 0.0):,.0f}"
                    if asset.get("balance") is not None
                    else "残高不明"
                )

                account_list_controls.controls.append(
                    Text(
                        f"・[ID:{asset['id']}] {branch}支店 / 口座番号: {account_num} / 残高: {balance}",
                        size=12,
                        color=Colors.BLACK87,
                    )
                )

        else:
            bank_name_display = f"銀行コード: {bank_code} (口座情報なし)"
            account_list_controls = Text(
                "この銀行コードに紐づく口座は現在登録されていません。", color=Colors.RED_600
            )

    else:
        # 旧ルートや不明なルートの場合のフォールバック
        bank_name_display = f"ID/コード: {bank_id_or_code} (不明なルート)"
        account_list_controls = Text(
            "ルーティングエラー、または旧IDによるアクセスです。", color=Colors.RED_600
        )
        bank_code = ""  # 銀行コードが特定できない場合は空に設定

    # --- メインコンテンツの定義 ---
    return Column(
        controls=[
            Text(
                f"📝 {bank_name_display} の残高証明申請書類 編集",
                size=24,
                weight=FontWeight.BOLD,
                color=Colors.BLACK,
            ),
            Divider(),
            # 1. 案件情報サマリー
            Text(
                f"案件ID: {case_id} / 銀行コード: {bank_code}",
                size=16,
                weight=FontWeight.W_500,
                color=Colors.BLUE_GREY_600,
            ),
            Container(height=10),
            # 2. 影響口座一覧
            Text("対象口座一覧", size=18, weight=FontWeight.BOLD, color=Colors.BLACK),
            Container(
                content=account_list_controls,
                padding=10,
                border=border.all(1, Colors.GREY_300),
                border_radius=5,
                bgcolor=Colors.WHITE,
                width=650,
            ),
            Divider(),
            # 3. 申請フォーム
            Text("申請情報入力", size=18, weight=FontWeight.BOLD, color=Colors.BLACK),
            Container(
                content=Column(
                    [
                        Row([date_of_application_field]),
                        Row([branch_name_for_doc_field]),
                        Row([notes_field]),
                    ],
                    spacing=15,
                ),
                padding=20,
                border_radius=5,
                bgcolor=Colors.WHITE,
                width=650,
            ),
            Divider(),
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
                alignment=MainAxisAlignment.END,
            ),
        ],
        spacing=20,
        expand=True,
        horizontal_alignment=CrossAxisAlignment.START,
    )
