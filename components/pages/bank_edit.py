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
    AlertDialog, 
    TextButton,
    Dropdown,
    dropdown,
    Stack,
)
from services.db_setup import (
    Engine,
    Session,
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
    get_bank_masters,
    get_branch_masters_by_bank_id,
    get_account_type_masters,
    add_or_update_bank_master, # 新規/編集モーダルのための関数
    get_bank_master_by_id,
)

# 銀行名フィールド (Dropdownとして再定義)
bank_name_field = Dropdown(
    label="銀行名 *",
    width=250,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
    # 💡 on_change で支店リストをリロードするハンドラを設定
    # on_change=load_branch_options のように設定する (後述)
)

# 支店名フィールド (Dropdownとして再定義)
branch_name_field = Dropdown(
    label="支店名 *",
    width=250,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
    # 💡 on_focus で銀行名が選択されているかチェックする
)

# 💡 口座種類フィールド (Dropdownとして再定義)
account_type_field = Dropdown(
    label="口座種類 *",
    width=150,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)

# 銀行コードは銀行名から自動設定されるため、読み取り専用のTextFieldのまま
bank_code_field = TextField(
    label="銀行コード",
    width=100,
    # read_only=True, 
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)
# 支店コードも同様
branch_code_field = TextField(
    label="支店コード",
    width=100,
    # read_only=True, 
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)

# bank_name_field = TextField(
#     label="金融機関名 *",
#     width=250,
#     color=Colors.BLACK,
#     label_style=TextStyle(color=Colors.BLACK),
# )

# bank_code_field = TextField(
#     # label="銀行コード *",
#     label="銀行コード",
#     width=150,
#     max_length=4,
#     color=Colors.BLACK,
#     label_style=TextStyle(color=Colors.BLACK),
# )
# branch_name_field = TextField(
#     # label="支店名 *",
#     label="支店名",
#     width=250,
#     color=Colors.BLACK,
#     label_style=TextStyle(color=Colors.BLACK),
# )
# branch_code_field = TextField(
#     # label="支店コード *",
#     label="支店コード",
#     width=150,
#     max_length=3,
#     color=Colors.BLACK,
#     label_style=TextStyle(color=Colors.BLACK),
# )
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

# ---------------------------------------------
# 💡 銀行マスタ編集/新規登録用モーダル UI の定義
# ---------------------------------------------

dialog_bank_name_field = TextField(label="銀行名", width=300)
dialog_bank_code_field = TextField(label="銀行コード", width=150)
current_editing_bank_id: int | None = None # 編集対象の銀行IDを保持

# 銀行マスタ新規/編集モーダル
bank_master_edit_dialog = AlertDialog(
    title=Text("銀行マスタの登録/編集"),
    content=Column(
        [
            dialog_bank_name_field,
            dialog_bank_code_field,
        ],
        tight=True,
    ),
    actions=[], # 後で定義
    modal=True,
)

# ---------------------------------------------
# 💡 マスターデータ関連のロジック
# ---------------------------------------------

def open_bank_master_dialog(e, page: Page, bank_id: int | None = None):
    """銀行マスタの登録/編集モーダルを開く"""
    global current_editing_bank_id
    current_editing_bank_id = bank_id
    
    # 既存編集モードの場合
    if bank_id is not None:
        with Session(bind=Engine) as db:
            bank = get_bank_master_by_id(db, bank_id)
            if bank:
                dialog_bank_name_field.value = bank.bank_name
                dialog_bank_code_field.value = bank.bank_code
                bank_master_edit_dialog.title.value = "銀行マスタの編集"
            else:
                return # 銀行が見つからない場合は処理を中止
    else:
        # 新規登録モードの場合
        dialog_bank_name_field.value = ""
        dialog_bank_code_field.value = ""
        bank_master_edit_dialog.title.value = "新しい銀行を登録"

    bank_master_edit_dialog.actions = [
        TextButton("キャンセル", on_click=lambda e: close_bank_master_dialog(e, page)),
        ElevatedButton("保存", on_click=lambda e: save_bank_master(e, page)),
    ]
    
    page.dialog = bank_master_edit_dialog
    bank_master_edit_dialog.open = True
    page.update()

def close_bank_master_dialog(e, page: Page):
    """銀行マスタの登録/編集モーダルを閉じる"""
    bank_master_edit_dialog.open = False
    page.update()

def save_bank_master(e, page: Page):
    """銀行マスタを保存し、ドロップダウンを更新する"""
    bank_name = dialog_bank_name_field.value
    bank_code = dialog_bank_code_field.value
    
    if not bank_name or not bank_code:
        page.snack_bar = SnackBar(Text("銀行名と銀行コードは必須です。"), bgcolor=Colors.RED_500)
        page.snack_bar.open = True
        page.update()
        return

    with Session(bind=Engine) as db:
        new_bank = add_or_update_bank_master(db, current_editing_bank_id, bank_name, bank_code)

    if new_bank:
        # 成功したらドロップダウンを更新し、新しい銀行を選択状態にする
        load_bank_options(page)
        bank_name_field.value = str(new_bank.id)
        
        # 支店と銀行コードも更新
        update_bank_details(page)

        close_bank_master_dialog(None, page)
        page.snack_bar = SnackBar(Text("銀行情報が正常に保存されました。"), bgcolor=Colors.GREEN_500)
        page.snack_bar.open = True
    else:
        page.snack_bar = SnackBar(Text("銀行情報の保存に失敗しました。重複している可能性があります。"), bgcolor=Colors.RED_500)
        page.snack_bar.open = True
    
    page.update()


def load_bank_options(page: Page):
    """銀行マスタをロードし、ドロップダウンの選択肢を更新する"""
    with Session(bind=Engine) as db:
        banks = get_bank_masters(db)
        bank_name_field.options = [
            dropdown.Option(str(bank.id), text=f"{bank.bank_name} ({bank.bank_code})")
            for bank in banks
        ]
        # 💡 新規登録への導線を追加
        bank_name_field.options.append(
            dropdown.Option(None, text="[ ➕ 新しい銀行を登録 ]", key="add_new_bank")
        )

def update_bank_details(page: Page):
    """銀行名選択時に銀行コードを更新し、支店リストをロードする"""
    selected_bank_id_str = bank_name_field.value
    
    # 💡 新規登録の選択肢が選ばれた場合
    if selected_bank_id_str == "add_new_bank":
        bank_name_field.value = None # 選択をリセット
        open_bank_master_dialog(None, page, None) # 新規登録モーダルを開く
        return

    if selected_bank_id_str:
        try:
            bank_id = int(selected_bank_id_str)
            with Session(bind=Engine) as db:
                bank = get_bank_master_by_id(db, bank_id)
                if bank:
                    bank_code_field.value = bank.bank_code
                    # 支店リストをロード
                    load_branch_options(page, bank_id)
                    page.update()
                    return
        except ValueError:
            pass
            
    # 選択がリセットされた場合
    bank_code_field.value = ""
    branch_name_field.options = []
    branch_code_field.value = ""
    page.update()


def load_branch_options(page: Page, bank_id: int):
    """選択された銀行に基づいて支店マスタをロードする"""
    branch_name_field.value = None # 支店をリセット
    branch_code_field.value = ""
    
    with Session(bind=Engine) as db:
        branches = get_branch_masters_by_bank_id(db, bank_id)
        branch_name_field.options = [
            dropdown.Option(str(branch.id), text=f"{branch.branch_name} ({branch.branch_code})")
            for branch in branches
        ]
        # 💡 新しい支店登録への導線も追加可能だが、ここでは簡略化のため省略
    
    # 💡 口座種類も初期ロードしておく
    load_account_type_options(page)
    page.update()

def load_account_type_options(page: Page):
    """口座種類マスタをロードする"""
    with Session(bind=Engine) as db:
        types = get_account_type_masters(db)
        account_type_field.options = [
            dropdown.Option(str(t.id), text=t.type_name)
            for t in types
        ]
    page.update()

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

def save_data(e, case_id: int):
    """
    IDベースでデータを保存/更新する。
    """
    page = e.page

    # ----------------------------------------------------
    # 1. データの取得と変換
    # ----------------------------------------------------
    
    # 💡 値をIDとして取得 (Dropdownのvalueは文字列ID)
    bank_id_str = bank_name_field.value
    branch_id_str = branch_name_field.value
    account_type_id_str = account_type_field.value
    
    # 残高の値の処理
    balance_str = balance_field.value.strip().replace(",", "")
    
    # ----------------------------------------------------
    # 2. 必須チェックと型変換
    # ----------------------------------------------------

    # 必須入力チェック: 銀行IDは必須
    if not bank_id_str:
        page.snack_bar = SnackBar(Text("銀行は必須です。", color=Colors.WHITE), bgcolor=Colors.RED_700)
        page.snack_bar.open = True
        page.update()
        return

    try:
        # 💡 ローカル変数として ID を定義
        bank_id = int(bank_id_str)
        # 支店と口座種類は任意の場合があるため、値がない場合は None または 0 を設定
        branch_id = int(branch_id_str) if branch_id_str else None
        account_type_id = int(account_type_id_str) if account_type_id_str else None
        
        balance_value = float(balance_str) if balance_str else 0.0
        
    except ValueError:
        page.snack_bar = SnackBar(Text("IDまたは残高の値が無効です。", color=Colors.WHITE), bgcolor=Colors.RED_700)
        page.snack_bar.open = True
        page.update()
        return

    # ----------------------------------------------------
    # 3. サービス層への呼び出し
    # ----------------------------------------------------
    
    try:
        # 編集モード (editing_asset_id は BankEditView のローカル変数と仮定)
        if editing_asset_id:
            # サービス関数を呼び出して更新
            success = update_financial_asset(
                asset_id=editing_asset_id,
                bank_id=bank_id,
                branch_id=branch_id,
                account_type_id=account_type_id,
                account_number=account_number_field.value,
                balance=balance_value,
                status=status_field.value,
            )
            print(f"DEBUG: 資産ID {editing_asset_id} を修正しました。")
            success_message = "銀行口座情報を修正しました。"

        # 新規登録モード
        else:
            # サービス関数を呼び出して新規登録
            success = add_financial_asset(
                case_id=case_id,
                bank_id=bank_id,
                branch_id=branch_id,
                account_type_id=account_type_id,
                account_number=account_number_field.value,
                balance=balance_value,
                status=status_field.value,
            )
            print("DEBUG: 新しい資産を登録しました。")

    except Exception as ex:
        # サービス関数内で発生したエラーをキャッチ
        print(f"保存/修正エラー: {ex}")
        page.open(
            SnackBar(
                content=Text(f"操作中にエラーが発生しました: {ex}", color=Colors.WHITE),
                bgcolor=Colors.RED_700,
            )
        )
        page.update()

    page.update()
    
    if success:
        page.snack_bar = SnackBar(Text("口座情報を正常に保存しました。", color=Colors.WHITE), bgcolor=Colors.GREEN_700)
        # 保存後、一覧画面に遷移またはモーダルを閉じる
        page.go(f"/case/{case_id}/bank/add") 
    else:
        page.snack_bar = SnackBar(Text("口座情報の保存に失敗しました。", color=Colors.WHITE), bgcolor=Colors.RED_700)

    page.snack_bar.open = True
    page.update()
    
def BankEditView(page: Page, case_id: int):
    # 💡 編集モードの判定に利用するローカル変数
    editing_asset_id = None

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

        # フォームフィールドをクリア
        bank_name_field.value = ""
        bank_code_field.value = ""
        branch_name_field.value = ""
        branch_code_field.value = ""

        account_number_field.value = ""
        balance_field.value = ""
        status_field.value = "調査中"

        # UIモードを「新規登録」に戻す
        main_action_button.text = "新規口座を登録"
        main_action_button.icon = Icons.ADD_CARD
        cancel_edit_button.visible = False

        page.update()
        bank_name_field.focus()

    def delete_asset(e):
        """資産をデータベースから削除する"""
        asset_id = e.control.data
        try:
            # データベース削除関数の呼び出しを仮定
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

        # サービス関数を呼び出して、現在の案件IDに紐づく資産リスト全体を取得
        assets = get_financial_asset_by_case(case_id)
        asset_to_edit = next((a for a in assets if a["id"] == asset_id), None)

        if not asset_to_edit:
            return

        # 編集モードに切り替え
        editing_asset_id = asset_id
        
        # フォームにデータをロード
        bank_name_field.value = asset_to_edit["bank_name"]
        bank_code_field.value = asset_to_edit["bank_code"]
        branch_name_field.value = asset_to_edit["branch_name"]
        branch_code_field.value = asset_to_edit["branch_code"]

        account_number_field.value = asset_to_edit["account_number"]
        balance_field.value = (
            f"{asset_to_edit['balance']:,.0f}" if asset_to_edit["balance"] is not None else ""
        )
        status_field.value = asset_to_edit["status"]

        # UIモードを「修正」に切り替え
        main_action_button.text = "口座情報を修正"
        main_action_button.icon = Icons.SAVE
        cancel_edit_button.visible = True

        page.update()
        bank_name_field.focus()

    def update_assets_list():
        """DBから最新の資産リストを取得し、ListViewを更新する"""
        # サービス関数を呼び出して資産リストを取得
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

        # フォームからの値を取得
        bank_name = bank_name_field.value.strip()
        bank_code = bank_code_field.value.strip()
        branch_name = branch_name_field.value.strip()
        branch_code = branch_code_field.value.strip()

        account_number = account_number_field.value.strip()
        balance_str = balance_field.value.strip().replace(",", "")
        status = status_field.value.strip()

        # 必須項目チェック (ここでは bank_name のみ)
        if not bank_name:
            page.open(
                SnackBar(
                    content=Text(
                        "金融機関名は必須です。",
                        color=Colors.WHITE,
                    ),
                    bgcolor=Colors.RED_700,
                )
            )
            page.update()
            return

        # 残高の数値チェック
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
            # 編集モード
            if editing_asset_id:
                # サービス関数を呼び出して更新
                # 💡 修正: IDベースの引数に置き換え
                success = update_financial_asset(
                    asset_id=editing_asset_id,
                    # case_idはサービス関数が不要と判断されたため削除 (必要なら残す)
                    bank_id=bank_id,
                    branch_id=branch_id,
                    account_type_id=account_type_id,
                    account_number=account_number_field.value,
                    balance=balance_value,
                    status=status_field.value,
                )
                print(f"DEBUG: 資産ID {editing_asset_id} を修正しました。")
                success_message = "銀行口座情報を修正しました。"

            # 新規登録モード
            else:
                # サービス関数を呼び出して新規登録
                # 💡 修正: IDベースの引数に置き換え
                success = add_financial_asset(
                    case_id=case_id,
                    bank_id=bank_id,
                    branch_id=branch_id,
                    account_type_id=account_type_id,
                    account_number=account_number_field.value,
                    balance=balance_value,
                    status=status_field.value,
                )
                print("DEBUG: 新しい資産を登録しました。")
                success_message = "銀行口座情報を登録しました。"

            # 成功後の処理
            if success:
                reset_form_and_mode()
                update_assets_list()

                page.open(
                    SnackBar(
                        content=Text(success_message, color=Colors.WHITE),
                        bgcolor=Colors.GREEN_700,
                    )
                )
            else:
                raise Exception("DB操作に失敗しました。")


        except Exception as ex:
            print(f"保存/修正エラー: {ex}")
            page.open(
                SnackBar(
                    content=Text(f"操作中にエラーが発生しました: {ex}", color=Colors.WHITE),
                    bgcolor=Colors.RED_700,
                )
            )
            page.update()

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
            ),
            Divider(),
            Container(
                content=Column(
                    [
                        Text("口座情報入力", weight=FontWeight.W_600, color=Colors.BLACK),
                        # 銀行名/コードの入力行
                        Row([bank_name_field, bank_code_field]),
                        # 支店名/コードの入力行
                        Row([branch_name_field, branch_code_field]),
                        # 口座番号/残高/ステータスの入力行
                        Row([account_number_field, balance_field, status_field]),
                        # アクションボタンの行
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