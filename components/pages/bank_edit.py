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
    TextStyle,
)
from zengin_code import Bank

# try:
#     from zengin_code import Bank, Branch, ZenginCodeError
# except ImportError:
#     # ライブラリがない場合のフォールバック（デバッグ用）
#     class Bank:
#         @staticmethod
#         def find(name=None, code=None):
#             return None
#     class Branch:
#         @staticmethod
#         def find(bank_code, name=None, code=None):
#             return None
#     class ZenginCodeError(Exception):
#         pass
#     print("WARNING: zengin_code library not found. Auto-completion disabled.")
from services.deceased_service import (
    add_financial_asset,
    delete_financial_asset,
    get_financial_asset_by_case,
    update_financial_asset,
)

bank_name_field = TextField(
    label="金融機関名 *",
    width=250,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)
bank_code_field = TextField(
    # label="銀行コード *",
    label="銀行コード",
    width=150,
    max_length=4,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)
branch_name_field = TextField(
    # label="支店名 *",
    label="支店名",
    width=250,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)
branch_code_field = TextField(
    # label="支店コード *",
    label="支店コード",
    width=150,
    max_length=3,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)
account_number_field = TextField(
    label="口座番号 *",
    width=250,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)
balance_field = TextField(
    label="残高 (調査時点)",
    width=250,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)
status_field = TextField(
    label="ステータス",
    value="調査中",
    width=250,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)

assets_list_view = ListView(spacing=10, expand=True)

main_action_button = ElevatedButton(
    "新規口座を登録", icon=Icons.ADD_CARD, bgcolor=Colors.BLUE_600, color=Colors.WHITE
)

cancel_edit_button = ElevatedButton(
    "キャンセル",
    icon=Icons.CANCEL,
    visible=False,
    bgcolor=Colors.GREY_600,
    color=Colors.WHITE,
)


def BankEditView(page: Page, case_id: int):
    editing_asset_id = None

    # # ----------------------------------------------------
    # # 自動補完ヘルパー関数 (zengin_codeの辞書を検索)
    # # ----------------------------------------------------

    # def get_bank_code_from_name_exact(bank_name: str) -> str | None:
    #     """
    #     銀行名から銀行コードを**完全一致**で取得します。
    #     """
    #     # Bank.all をループして、銀行名が完全に一致するものを探す
    #     for code, bank in Bank.all.items():
    #         # 銀行オブジェクトの name 属性（正式名称）と入力された銀行名が完全に一致するか確認
    #         if bank.name == bank_name:
    #             # 完全に一致した場合、その銀行のコード（辞書のキー）を返す
    #             return code

    #     print(f"エラー: 銀行名 '{bank_name}' が**完全一致**で見つかりませんでした。")
    #     return None

    # def get_bank_name_from_code_exact(bank_code: str) -> str | None:
    #     """
    #     銀行コードから銀行名を**完全一致**で取得します。
    #     """
    #     # Bank.all は銀行コードをキーとする辞書なので、直接アクセスを試みる
    #     if bank_code in Bank.all:
    #         bank = Bank.all[bank_code]
    #         # 銀行オブジェクトの name 属性（正式名称）を返す
    #         return bank.name

    #     print(f"エラー: 銀行コード '{bank_code}' が見つかりませんでした。")
    #     return None

    # def get_branch_code_exact(bank_name: str, branch_name: str) -> str | None:
    #     """
    #     銀行名と支店名から支店コードを**完全一致**で取得します。
    #     検索は主に 'name' (漢字/正式名称) 属性に対して行われます。
    #     """
    #     # 1. 銀行名の完全一致検索
    #     found_bank = None
    #     for code, bank in Bank.all.items():
    #         # 銀行の正式名称が完全に一致するか確認
    #         if bank.name == bank_name:
    #             found_bank = bank
    #             break

    #     if not found_bank:
    #         print(
    #             f"エラー: 銀行名 '{bank_name}' が**完全一致**で見つかりませんでした。"
    #         )
    #         return None

    #     # 2. 支店名の完全一致検索
    #     for code, branch in found_bank.branches.items():
    #         # 支店の正式名称が完全に一致するか確認
    #         if branch.name == branch_name:
    #             # 完全に一致した支店コードを返す
    #             return code

    #     print(
    #         f"エラー: 銀行 '{found_bank.name}' の支店名 '{branch_name}' が**完全一致**で見つかりませんでした。"
    #     )
    #     return None

    # def get_branch_name_exact(bank_name: str, branch_code: str) -> str | None:
    #     """
    #     銀行名と支店コードから支店名を**完全一致**で取得します。
    #     """
    #     # 1. 銀行名の完全一致検索
    #     found_bank = None
    #     for code, bank in Bank.all.items():
    #         # 銀行の正式名称が完全に一致するか確認
    #         if bank.name == bank_name:
    #             found_bank = bank
    #             break

    #     if not found_bank:
    #         print(
    #             f"エラー: 銀行名 '{bank_name}' が**完全一致**で見つかりませんでした。"
    #         )
    #         return None

    #     # 2. 見つかった銀行の支店リストから支店コードをキーとして検索
    #     # 支店コードは branches 辞書のキーになっているため、直接アクセスできます。
    #     if branch_code in found_bank.branches:
    #         branch = found_bank.branches[branch_code]
    #         # 支店オブジェクトの name 属性（正式名称）を返す
    #         return branch.name
    #     else:
    #         print(
    #             f"エラー: 銀行 '{found_bank.name}' の支店コード '{branch_code}' が見つかりませんでした。"
    #         )
    #         return None

    # # ----------------------------------------------------
    # # 自動補完ロジック (On Change Handlers)
    # # ----------------------------------------------------

    # def handle_bank_change(e):
    #     """銀行名/コードの変更時に相互補完を行う"""

    #     bank_name = bank_name_field.value.strip()
    #     bank_code = bank_code_field.value.strip()

    #     bank = None
    #     needs_update = False

    #     if e.control == bank_name_field and bank_name:
    #         # 銀行名入力 -> コードを検索
    #         bank = find_bank(name=bank_name)
    #         if bank and bank["code"] != bank_code_field.value:
    #             bank_code_field.value = bank["code"]
    #             needs_update = True

    #     elif e.control == bank_code_field and bank_code and len(bank_code) == 4:
    #         # 銀行コード入力 -> 名前を検索
    #         bank = find_bank(code=bank_code)
    #         if bank and bank["name"] != bank_name_field.value:
    #             bank_name_field.value = bank["name"]
    #             needs_update = True

    #     if needs_update:
    #         page.update()

    #     # 支店コードの検索のために銀行コードが必須なので、支店フィールドも更新
    #     handle_branch_change(e)

    # def handle_branch_change(e):
    #     """支店名/コードの変更時に相互補完を行う"""

    #     bank_code = bank_code_field.value.strip()
    #     branch_name = branch_name_field.value.strip()
    #     branch_code = branch_code_field.value.strip()

    #     if not bank_code or len(bank_code) != 4:
    #         # 銀行コードがないと支店は特定できない
    #         return

    #     branch = None
    #     needs_update = False

    #     if e.control == branch_name_field and branch_name:
    #         # 支店名入力 -> コードを検索
    #         branch = find_branch(bank_code=bank_code, name=branch_name)
    #         if branch and branch["code"] != branch_code_field.value:
    #             branch_code_field.value = branch["code"]
    #             needs_update = True

    #     elif e.control == branch_code_field and branch_code and len(branch_code) == 3:
    #         # 支店コード入力 -> 名前を検索
    #         branch = find_branch(bank_code=bank_code, code=branch_code)
    #         if branch and branch["name"] != branch_name_field.value:
    #             branch_name_field.value = branch["name"]
    #             needs_update = True

    #     if needs_update:
    #         page.update()

    # # フォームの on_change ハンドラを設定
    # bank_name_field.on_blur = handle_bank_change
    # bank_code_field.on_blur = handle_bank_change
    # branch_name_field.on_blur = handle_branch_change
    # branch_code_field.on_blur = handle_branch_change

    # ----------------------------------------------------
    # 自動補完ヘルパー関数 (zengin_codeの Bank/Branch オブジェクトを検索)
    # ----------------------------------------------------

    def find_bank_data(name=None, code=None):
        """銀行名または銀行コードで Bank オブジェクトを検索する"""
        if code and code in Bank.all:
            return Bank.all[code]
        if name:
            # 銀行名で検索 (valueが Bank オブジェクトなので、.name 属性で比較)
            for bank_data in Bank.all.values():
                print(bank_data.name)
                if bank_data.name == name.replace("銀行", "").replace(
                    "農業協同組合", "農協"
                ).replace("信用金庫", "信金"):
                    return bank_data
        return None

    def find_branch_data(bank_code: str, name=None, code=None):
        """支店名または支店コードで Branch オブジェクトを検索する"""
        if bank_code in Bank.all:
            bank = Bank.all[bank_code]
            if code and code in bank.branches:
                return bank.branches[code]

            if name:
                # 支店名で検索 (valueが Branch オブジェクトなので、.name 属性で比較)
                for branch_data in bank.branches.values():
                    print(branch_data.name)
                    if branch_data.name == name.replace("支店", ""):
                        return branch_data
        return None

    # ----------------------------------------------------
    # 自動補完ロジック (On Blur Handlers)
    # ----------------------------------------------------

    def handle_bank_change(e):
        """銀行名/コードの変更時に相互補完を行う"""

        bank_name = bank_name_field.value.strip()
        bank_code = bank_code_field.value.strip()
        needs_update = False

        if e.control == bank_name_field and bank_name:
            # 銀行名入力 -> コードを検索
            bank = find_bank_data(name=bank_name)
            if bank and bank.code != bank_code_field.value:
                bank_code_field.value = bank.code
                needs_update = True

        elif e.control == bank_code_field and bank_code and len(bank_code) == 4:
            # 銀行コード入力 -> 名前を検索
            bank = find_bank_data(code=bank_code)
            if bank and bank.name != bank_name_field.value:
                bank_name_field.value = bank.name
                needs_update = True

        if needs_update:
            page.update()

        # 支店コードの検索のために銀行コードが必須なので、支店フィールドも更新
        handle_branch_change(e)

    def handle_branch_change(e):
        """支店名/コードの変更時に相互補完を行う"""

        bank_code = bank_code_field.value.strip()
        branch_name = branch_name_field.value.strip()
        branch_code = branch_code_field.value.strip()

        if not bank_code or len(bank_code) != 4:
            # 銀行コードがないと支店は特定できない
            return

        needs_update = False

        if e.control == branch_name_field and branch_name:
            # 支店名入力 -> コードを検索
            branch = find_branch_data(bank_code=bank_code, name=branch_name)
            if branch and branch.code != branch_code_field.value:
                branch_code_field.value = branch.code
                needs_update = True

        elif e.control == branch_code_field and branch_code and len(branch_code) == 3:
            # 支店コード入力 -> 名前を検索
            branch = find_branch_data(bank_code=bank_code, code=branch_code)
            if branch and branch.name != branch_name_field.value:
                branch_name_field.value = branch.name
                needs_update = True

        if needs_update:
            page.update()

    # フォームの on_blur ハンドラを設定 (フォーカスが外れた時に実行)
    bank_name_field.on_blur = handle_bank_change
    bank_code_field.on_blur = handle_bank_change
    branch_name_field.on_blur = handle_branch_change
    branch_code_field.on_blur = handle_branch_change

    # ----------------------------------------------------
    # UI 更新ロジック
    # ----------------------------------------------------

    def reset_form_and_mode():
        """フォームをクリアし、登録モードに戻す"""
        nonlocal editing_asset_id
        editing_asset_id = None

        bank_name_field.value = ""
        bank_code_field.value = ""
        branch_name_field.value = ""
        branch_code_field.value = ""

        account_number_field.value = ""
        balance_field.value = ""
        status_field.value = "調査中"

        main_action_button.text = "新規口座を登録"
        main_action_button.icon = Icons.ADD_CARD
        cancel_edit_button.visible = False

        page.update()
        bank_name_field.focus()

    def delete_asset(e):
        """資産をデータベースから削除する"""
        asset_id = e.control.data
        try:
            # 🎯 データベース削除関数の呼び出しを仮定
            delete_financial_asset(asset_id)
            print(f"DEBUG: 資産ID {asset_id} を削除しました。")

            update_assets_list()

            page.open(
                SnackBar(
                    content=Text("銀行口座情報を削除しました。", color=Colors.WHITE),
                    bgcolor=Colors.RED_700,
                )
            )
        except Exception as ex:
            print(f"削除エラー: {ex}")
            page.open(
                SnackBar(
                    content=Text(f"削除中にエラーが発生しました: {ex}", color=Colors.WHITE),
                    bgcolor=Colors.RED_700,
                )
            )
        page.update()

    def start_edit(e):
        """編集対象の資産情報をフォームにロードし、編集モードに切り替える"""
        nonlocal editing_asset_id
        asset_id = e.control.data

        assets = get_financial_asset_by_case(case_id)
        asset_to_edit = next((a for a in assets if a["id"] == asset_id), None)

        if not asset_to_edit:
            return

        editing_asset_id = asset_id
        bank_name_field.value = asset_to_edit["bank_name"]
        bank_code_field.value = asset_to_edit["bank_code"]
        branch_name_field.value = asset_to_edit["branch_name"]
        branch_code_field.value = asset_to_edit["branch_code"]

        account_number_field.value = asset_to_edit["account_number"]
        balance_field.value = (
            f"{asset_to_edit['balance']:,.0f}" if asset_to_edit["balance"] is not None else ""
        )
        status_field.value = asset_to_edit["status"]

        main_action_button.text = "口座情報を修正"
        main_action_button.icon = Icons.SAVE
        cancel_edit_button.visible = True

        page.update()
        bank_name_field.focus()

    def update_assets_list():
        """DBから最新の資産リストを取得し、ListViewを更新する"""
        assets = get_financial_asset_by_case(case_id)

        assets_list_view.controls.clear()

        if not assets:
            assets_list_view.controls.append(
                Text("現在、登録された銀行口座情報はありません。", color=Colors.GREY_600)
            )
        else:
            for asset in assets:
                balance_str = (
                    f"¥{asset['balance']:,.0f}" if asset["balance"] is not None else "残高不明"
                )

                bank_info = f"🏦 {asset['bank_name']} ({asset.get('bank_code', 'N/A')})"
                branch_info = (
                    f"{asset.get('branch_name', 'N/A')} 支店 ({asset.get('branch_code', 'N/A')})"
                )

                assets_list_view.controls.append(
                    Row(
                        [
                            # Text(
                            #     f"🏦 {asset['bank_name']}",
                            #     size=14,
                            #     weight=FontWeight.W_600,
                            #     width=200,
                            #     color=Colors.BLACK,
                            # ),
                            Text(
                                bank_info,
                                size=14,
                                weight=FontWeight.W_600,
                                width=250,
                                color=Colors.BLACK,
                            ),
                            Text(
                                branch_info,
                                size=14,
                                width=200,
                                color=Colors.BLACK,
                            ),
                            Text(
                                f"口座: {asset['account_number']}",
                                size=14,
                                width=200,
                                color=Colors.BLACK,
                            ),
                            Text(
                                f"残高: {balance_str}",
                                size=14,
                                width=150,
                                color=Colors.BLACK,
                            ),
                            Text(
                                f"状態: {asset['status']}",
                                size=14,
                                color=Colors.BLACK,
                            ),
                            IconButton(
                                Icons.EDIT,
                                icon_color=Colors.BLUE_400,
                                tooltip="編集",
                                data=asset["id"],
                                on_click=start_edit,
                            ),
                            IconButton(
                                Icons.DELETE,
                                icon_color=Colors.RED_400,
                                tooltip="削除",
                                data=asset["id"],
                                on_click=delete_asset,
                            ),
                        ],
                        alignment=MainAxisAlignment.START,
                    )
                )
        page.update()

    # ----------------------------------------------------
    # 保存ロジック (登録と修正を兼ねる)
    # ----------------------------------------------------

    def save_asset(e):
        """資産をデータベースに登録または修正する"""
        nonlocal editing_asset_id

        bank_name = bank_name_field.value.strip()
        bank_code = bank_code_field.value.strip()
        branch_name = branch_name_field.value.strip()
        branch_code = branch_code_field.value.strip()

        account_number = account_number_field.value.strip()
        balance_str = balance_field.value.strip().replace(",", "")
        status = status_field.value.strip()

        # if (
        #     not bank_name
        #     or not bank_code
        #     or not branch_name
        #     or not branch_code
        #     or not account_number
        # ):
        if not bank_name:
            page.open(
                SnackBar(
                    content=Text(
                        # "金融機関名、銀行コード、支店名、支店コード、口座番号は必須です。",
                        "金融機関名は必須です。",
                        color=Colors.WHITE,
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
                    content=Text("残高は有効な数値で入力してください。", color=Colors.WHITE),
                    bgcolor=Colors.RED_700,
                )
            )
            page.update()
            return

        try:
            if editing_asset_id:
                update_financial_asset(
                    asset_id=editing_asset_id,
                    case_id=case_id,
                    bank_name=bank_name,
                    bank_code=bank_code,
                    branch_name=branch_name,
                    branch_code=branch_code,
                    account_number=account_number,
                    balance=balance_value,
                    status=status,
                )
                print(f"DEBUG: 資産ID {editing_asset_id} を修正しました。")
                success_message = "銀行口座情報を修正しました。"

            else:
                add_financial_asset(
                    case_id=case_id,
                    bank_name=bank_name,
                    bank_code=bank_code,
                    branch_name=branch_name,
                    branch_code=branch_code,
                    account_number=account_number,
                    balance=balance_value,
                    status=status,
                )
                print("DEBUG: 新しい資産を登録しました。")
                success_message = "銀行口座情報を登録しました。"

            reset_form_and_mode()

            # リストを更新
            update_assets_list()

            page.open(
                SnackBar(
                    content=Text(success_message, color=Colors.WHITE),
                    bgcolor=Colors.GREEN_700,
                )
            )

        except Exception as ex:
            print(f"保存/修正エラー: {ex}")
            page.open(
                SnackBar(
                    content=Text(f"操作中にエラーが発生しました: {ex}", color=Colors.WHITE),
                    bgcolor=Colors.RED_700,
                )
            )
            page.update()

    # フォームのアクションハンドラを設定
    main_action_button.on_click = save_asset
    cancel_edit_button.on_click = lambda e: reset_form_and_mode()

    # 初期データロード
    update_assets_list()

    # --- UI レイアウト構築 ---

    view_content = Column(
        controls=[
            Text(
                f"🏦 銀行口座登録 (案件ID: {case_id})",
                size=24,
                weight=FontWeight.BOLD,
                # color=Colors.BLACK,
            ),
            Divider(),
            Container(
                content=Column(
                    [
                        Text("口座情報入力", weight=FontWeight.W_600, color=Colors.BLACK),
                        Row([bank_name_field, bank_code_field]),
                        Row([branch_name_field, branch_code_field]),
                        Row([account_number_field, balance_field, status_field]),
                        Row(
                            [
                                cancel_edit_button,
                                main_action_button,
                            ],
                            alignment=MainAxisAlignment.END,
                        ),
                    ],
                    spacing=15,
                ),
                padding=20,
                border_radius=10,
                bgcolor=Colors.WHITE,
            ),
            Divider(),
            Text(
                "登録済み銀行口座一覧",
                size=18,
                weight=FontWeight.BOLD,
                # color=Colors.BLACK,
            ),
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
