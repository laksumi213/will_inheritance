# /components/pages/bank_edit.py
from flet import (
    Colors,
    Column,
    Container,
    Divider,
    ElevatedButton,
    FontWeight,
    IconButton,
    Icons,
    ListView,
    MainAxisAlignment,
    Page,
    Row,
    SnackBar,
    Text,
    TextField,
)

from services.deceased_service import add_financial_asset, get_financial_asset_by_case

# フォームコントロールは View の外で定義して状態を持たせます (簡易的な方法)
bank_name_field = TextField(label="金融機関名 *", width=250)
account_number_field = TextField(label="口座番号 *", width=250)
balance_field = TextField(label="残高 (調査時点)", width=200)
status_field = TextField(label="ステータス", value="調査中", width=150)

# 資産リストを表示するためのコンテナ
assets_list_view = ListView(spacing=10, expand=True)


def BankEditView(page: Page, case_id: int):
    """
    案件の銀行口座資産を登録・管理する View
    :param case_id: 編集対象の Case ID
    """

    # ----------------------------------------------------
    # UI 更新ロジック
    # ----------------------------------------------------

    def update_assets_list():
        """DBから最新の資産リストを取得し、ListViewを更新する"""
        assets = get_financial_asset_by_case(case_id)

        assets_list_view.controls.clear()

        if not assets:
            assets_list_view.controls.append(
                Text(
                    "現在、登録された銀行口座情報はありません。", color=Colors.GREY_600
                )
            )
        else:
            for asset in assets:
                balance_str = (
                    f"¥{asset['balance']:,.0f}"
                    if asset["balance"] is not None
                    else "残高不明"
                )

                assets_list_view.controls.append(
                    Row(
                        [
                            Text(
                                f"🏦 {asset['bank_name']}",
                                size=14,
                                weight=FontWeight.W_600,
                                width=200,
                            ),
                            Text(
                                f"口座: {asset['account_number']}", size=14, width=200
                            ),
                            Text(f"残高: {balance_str}", size=14, width=150),
                            Text(
                                f"状態: {asset['status']}",
                                size=14,
                                color=Colors.BLUE_GREY_600,
                            ),
                            # 削除ボタン（未実装だが、UIとして配置）
                            IconButton(
                                Icons.DELETE,
                                icon_color=Colors.RED_400,
                                tooltip="削除",
                                data=asset["id"],
                            ),
                        ],
                        alignment=MainAxisAlignment.START,
                    )
                )
        page.update()

    # ----------------------------------------------------
    # 保存ロジック
    # ----------------------------------------------------

    def save_new_asset(e):
        """新しい資産をデータベースに登録する"""
        bank_name = bank_name_field.value.strip()
        account_number = account_number_field.value.strip()
        balance_str = balance_field.value.strip().replace(",", "")
        status = status_field.value.strip()

        if not bank_name or not account_number:
            page.open(
                SnackBar(
                    content=Text(
                        "金融機関名と口座番号は必須です。", color=Colors.WHITE
                    ),
                    bgcolor=Colors.RED_700,
                )
            )
            page.update()
            return

        try:
            balance_value = float(balance_str) if balance_str else 0.0
        except ValueError:
            page.open(
                SnackBar(
                    content=Text(
                        "残高は有効な数値で入力してください。", color=Colors.WHITE
                    ),
                    bgcolor=Colors.RED_700,
                )
            )
            page.update()
            return

        try:
            add_financial_asset(
                case_id=case_id,
                bank_name=bank_name,
                account_number=account_number,
                balance=balance_value,
                status=status,
            )

            # フォームをクリア
            bank_name_field.value = ""
            account_number_field.value = ""
            balance_field.value = ""
            status_field.value = "調査中"

            # リストを更新
            update_assets_list()

            page.open(
                SnackBar(
                    content=Text("銀行口座情報を登録しました。", color=Colors.WHITE),
                    bgcolor=Colors.GREEN_700,
                )
            )
            bank_name_field.focus()

        except Exception as ex:
            print(f"保存エラー: {ex}")
            page.open(
                SnackBar(
                    content=Text(
                        f"保存中にエラーが発生しました: {ex}", color=Colors.WHITE
                    ),
                    bgcolor=Colors.RED_700,
                )
            )
            page.update()

    # 初期データロード
    update_assets_list()

    # --- UI レイアウト構築 ---

    view_content = Column(
        controls=[
            Text(
                f"🏦 銀行口座登録 (案件ID: {case_id})", size=24, weight=FontWeight.BOLD
            ),
            Divider(),
            # 登録フォーム
            Container(
                content=Column(
                    [
                        Text("新規口座情報入力", weight=FontWeight.W_600),
                        Row([bank_name_field, account_number_field]),
                        Row([balance_field, status_field]),
                        Row(
                            [
                                ElevatedButton(
                                    "新規口座を登録",
                                    icon=Icons.ADD_CARD,
                                    on_click=save_new_asset,
                                    bgcolor=Colors.BLUE_600,
                                )
                            ],
                            alignment=MainAxisAlignment.END,
                        ),
                    ],
                    spacing=15,
                ),
                padding=20,
                border_radius=10,
                bgcolor=Colors.BLUE_GREY_50,
            ),
            Divider(),
            # 登録済み資産リスト
            Text("登録済み銀行口座一覧", size=18, weight=FontWeight.BOLD),
            Container(
                content=assets_list_view,
                padding=10,
                height=300,
                border_radius=5,
                bgcolor=Colors.WHITE,
            ),
        ],
        spacing=20,
        expand=True,
    )

    return view_content
