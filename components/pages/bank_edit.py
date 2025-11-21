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
    label="支店名",
    width=250,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
    # 💡 on_focus で銀行名が選択されているかチェックする
)

# 💡 口座種類フィールド (Dropdownとして再定義)
account_type_field = Dropdown(
    label="口座種類",
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

# alert_dialog = AlertDialog(
#     modal=True,
#     title=Text("確認"),
#     content=Text("操作を実行しますか？"),
#     actions=[
#         TextButton("はい", on_click=lambda e: print("はいがクリックされました")),
#         TextButton("いいえ", on_click=lambda e: print("いいえがクリックされました")),
#     ],
#     actions_alignment=MainAxisAlignment.END,
# )

# ---------------------------------------------
# 💡 マスターデータ関連のロジック
# ---------------------------------------------

# def open_bank_master_dialog(e, page: Page, bank_id: int | None = None):
def open_bank_master_dialog(page: Page, bank_id: int):
    """銀行マスタの登録/編集モーダルを開く"""
    global my_page
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
    
    my_page.open(bank_master_edit_dialog)
    # page.dialog = bank_master_edit_dialog
    # bank_master_edit_dialog.open = True
    my_page.update()

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
        options = [
            # 💡 空の選択肢を先頭に追加（value=""）
            dropdown.Option("def", text="選択してください"),
            dropdown.Option('add_new_bank', text="[ ➕ 新しい銀行を登録 ]"),
        ]

        # 既存の銀行マスタのオプションを追加
        options.extend([
            dropdown.Option(str(bank.id), text=f"{bank.bank_name} ({bank.bank_code})")
            for bank in banks
        ])

        bank_name_field.options = options
        bank_name_field.value = "def"
    page.update()

def update_bank_details(page: Page):
    """銀行名選択時に銀行コードを更新し、支店リストをロードする"""
    selected_bank_id_str = bank_name_field.value
    
    # 💡 新規登録の選択肢が選ばれた場合
    if selected_bank_id_str == "add_new_bank":
        bank_name_field.value = "" # 選択をリセット（空のオプション value="" に合わせる）
        # open_bank_master_dialog(None, page, None) # 新規登録モーダルを開く
        open_bank_master_dialog(page, None) # 新規登録モーダルを開く
        bank_name_field.update()
        return

    if selected_bank_id_str:
        try:
            bank_id = int(selected_bank_id_str)
            with Session(bind=Engine) as db:
                bank = get_bank_master_by_id(db, bank_id)
                if bank:
                    # 銀行コードを更新
                    bank_code_field.value = bank.bank_code
                    
                    # 支店リストをロード
                    load_branch_options(page, bank_id)
                    
                    # 画面更新 (支店リストと銀行コードの変更を反映)
                    bank_code_field.update()
                    # load_branch_options の中で page.update() が呼ばれないように調整されている場合、ここで page.update() が必要
                    page.update()
                    return
        except ValueError:
            pass
            
    # 選択がリセットされた場合 (銀行IDが空または無効な場合)
    bank_code_field.value = ""
    branch_name_field.options = []
    branch_name_field.value = "def" # 支店名ドロップダウンもクリア
    branch_code_field.value = ""
    page.update()

def update_branch_details(page: Page):
    """
    支店名選択時に支店コードを更新し、画面を更新する。
    """
    selected_branch_id_str = branch_name_field.value
    
    if selected_branch_id_str:
        try:
            branch_id = int(selected_branch_id_str)
            with Session(bind=Engine) as db:
                from services.db_setup import BranchMaster
                # 支店マスタをIDで取得 (この関数が services/deceased_service.py に存在しない場合は、ここでクエリを実行)
                branch = db.query(BranchMaster).filter(BranchMaster.id == branch_id).first()
                
                if branch:
                    branch_code_field.value = branch.branch_code
                    branch_code_field.update()
                    # page.update() は不要。Fletではコントロールの update() がページ全体を更新しないため。
                    return
        except ValueError:
            pass
            
    # 選択がリセットされた場合
    branch_code_field.value = ""
    branch_code_field.update()
    page.update()

def load_branch_options(page: Page, bank_id: int):
    """選択された銀行に基づいて支店マスタをロードする"""
    branch_name_field.value = "def" # 支店をリセット (value="" に変更)
    branch_code_field.value = ""
    
    with Session(bind=Engine) as db:
        branches = get_branch_masters_by_bank_id(db, bank_id)
        branch_name_field.options = [
            # 💡 修正点: 先頭に空のオプションを追加
            dropdown.Option("def", text="選択してください"),
            dropdown.Option('add_new_branch', text="[ ➕ 新しい支店を登録 ]"), # 導線も追加
        ]
        branch_name_field.options.extend([
            dropdown.Option(str(branch.id), text=f"{branch.branch_name} ({branch.branch_code})")
            for branch in branches
        ])
    
    
    # 💡 口座種類も初期ロードしておく
    load_account_type_options(page)

def load_account_type_options(page: Page):
    """口座種類マスタをロードする"""
    with Session(bind=Engine) as db:
        types = get_account_type_masters(db)
        account_type_field.options = [
            dropdown.Option(str(t.id), text=t.type_name)
            for t in types
        ]
    # page.update()

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
    global my_page
    # 💡 編集モードの判定に利用するローカル変数
    editing_asset_id = None
    my_page = page

    # ----------------------------------------------------
    # 自動補完ヘルパー関数 (zengin_codeの Bank/Branch オブジェクトを検索)
    # ----------------------------------------------------

    def get_bank_master_id_by_code(bank_code: str):
        """銀行コードから BankMaster ID を取得する (DBアクセス)"""
        # BankMaster, Session, Engine は外部スコープからアクセス可能と仮定
        with Session(bind=Engine) as db:
            from services.db_setup import BankMaster 
            bank = db.query(BankMaster.id).filter(BankMaster.bank_code == bank_code).first()
            return bank[0] if bank else None

    def find_bank_data(name=None, code=None):
        """銀行名または銀行コードで Bank オブジェクトを検索する (zengin_code利用)"""
        if code and code in Bank.all:
            return Bank.all[code]
        if name:
            # 銀行名で検索 (valueが Bank オブジェクトなので、.name 属性で比較)
            for bank_data in Bank.all.values():
                # print(bank_data.name) # デバッグログ
                if bank_data.name == name.replace("銀行", "").replace(
                    "農業協同組合", "農協"
                ).replace("信用金庫", "信金"):
                    return bank_data
        return None

    def find_branch_data(bank_code: str, name=None, code=None):
        """
        支店名または支店コードで Branch オブジェクトを検索する (zengin_code利用)
        """
        if bank_code in Bank.all:
            bank = Bank.all[bank_code]
            # 支店コードがある場合
            if code and code in bank.branches:
                return bank.branches[code]

            # 支店名がある場合
            if name:
                # 支店名で検索 (valueが Branch オブジェクトなので、.name 属性で比較)
                for branch_data in bank.branches.values():
                    # print(branch_data.name) # デバッグログ
                    if branch_data.name == name.replace("支店", ""):
                        return branch_data
        return None
    
    # 💡 修正: 支店コードから BranchMaster ID を取得するヘルパー関数
    def get_branch_master_id_by_code(bank_code: str, branch_code: str):
        """銀行コードと支店コードから BranchMaster ID を取得する (DBアクセス)"""
        with Session(bind=Engine) as db:
            from services.db_setup import BankMaster, BranchMaster
            # 銀行IDをまず取得
            bank_id = db.query(BankMaster.id).filter(BankMaster.bank_code == bank_code).scalar()
            if not bank_id:
                return None
            # 支店コードと bank_id で検索
            branch = db.query(BranchMaster.id).filter(
                BranchMaster.bank_id == bank_id,
                BranchMaster.branch_code == branch_code
            ).first()
            return branch[0] if branch else None

    # ----------------------------------------------------
    # 自動補完ロジック (On Blur Handlers)
    # ----------------------------------------------------

    def handle_bank_change(e):
        """銀行コードの変更時に相互補完を行う"""

        bank_code = bank_code_field.value.strip()
        needs_update = False

        load_bank_options(e.page) # 画面はここでは更新しない

        # 💡 銀行コード入力 -> 銀行名(zengin_code)を検索
        if e.control == bank_code_field and bank_code and len(bank_code) == 4:
            bank = find_bank_data(code=bank_code)
            
            if bank:
                # 1. DBの BankMaster ID を銀行コードで直接検索
                bank_master_id = get_bank_master_id_by_code(bank_code)
                
                if bank_master_id:
                    # 2. Dropdownの値をマスターIDに設定
                    #    これにより、Dropdownは表示テキストとして BankMaster の bank_name を自動で表示します。
                    bank_name_field.value = str(bank_master_id)
                    bank_code_field.error_text = None

                    # 3. 支店リストのロードと画面更新を実行
                    # 💡 update_bank_details が支店をロードし、page.update()を呼ぶ
                    update_bank_details(e.page)
                    needs_update = True
                    
                elif bank_name_field.value:
                    # DBマスターにない場合
                    bank_name_field.value = 'def'
                    bank_code_field.error_text = "該当する銀行コードがマスターに見つかりません。"
                    branch_name_field.options = []
                    branch_code_field.value = ""
                    needs_update = True

        # 支店コードの検索のために銀行コードが必須なので、支店フィールドも更新
        if bank_code_field.value and len(bank_code_field.value) == 4:
            handle_branch_change(e)
        
        # 💡 update_bank_details が成功した場合は既に update() されているため、ここでは pass 
        if not needs_update:
            e.page.update()

    def handle_branch_change(e):
        """支店名/コードの変更時に相互補完を行う"""
        
        bank_code = bank_code_field.value.strip()
        branch_code = branch_code_field.value.strip()
        needs_update = False

        if not bank_code or len(bank_code) != 4:
            # 銀行コードがない場合は支店は特定できない
            return

        # 💡 支店コード入力 -> 名前を検索
        if e.control == branch_code_field and branch_code and len(branch_code) == 3:
            branch = find_branch_data(bank_code=bank_code, code=branch_code)
            
            if branch:
                branch_master_id = get_branch_master_id_by_code(bank_code, branch_code)
                
                if branch_master_id:
                    # Dropdownの値をマスターIDに設定
                    branch_name_field.value = str(branch_master_id)
                    branch_code_field.error_text = None
                    
                    # 💡 修正: ここで options を更新するのではなく、load_branch_options に任せる
                    # load_branch_options は update_bank_details から既に呼ばれているが、
                    # ここで手動で呼び出して、選択肢にヒットした支店を含める必要がある。
                    
                    # 銀行IDを取得し、支店オプションをリロードする
                    bank_id = int(bank_name_field.value) if bank_name_field.value else None
                    if bank_id:
                         # 既にロードされているオプションの中に新しい支店が含まれていることを期待
                         # 選択値の設定のみでOK
                         pass 
                         
                    needs_update = True
        
            elif branch_name_field.value:
                # コードが見つからない場合、Dropdownの選択を解除
                branch_name_field.value = 'def'
                branch_code_field.error_text = "該当する支店コードがマスターに見つかりません。"
                needs_update = True

        if needs_update:
            e.page.update()
            
    # フォームの on_blur ハンドラを再割り当て
    # bank_name_field.on_change = handle_bank_change
    bank_name_field.on_change = update_bank_details
    bank_code_field.on_blur = handle_bank_change
    branch_name_field.on_change = lambda e: update_branch_details(e.page)
    branch_code_field.on_blur = handle_branch_change

    # ----------------------------------------------------
    # UI 更新ロジック
    # ----------------------------------------------------

    def reset_form_and_mode():
        """フォームをクリアし、登録モードに戻す"""
        nonlocal editing_asset_id
        editing_asset_id = None

        # フォームフィールドをクリア
        bank_name_field.value = "def"
        bank_code_field.value = ""
        branch_name_field.value = "def"
        branch_code_field.value = ""

        account_number_field.value = ""
        balance_field.value = ""
        status_field.value = "調査中"

        bank_name_field.update()
        branch_name_field.update()
        bank_code_field.update()
        branch_code_field.update()

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
        
        # 💡 DropdownにはIDを文字列としてセットする (サービス側から ID が取得できている前提)
        bank_id_from_asset = asset_to_edit.get("bank_id")
        branch_id_from_asset = asset_to_edit.get("branch_id")
        account_type_id_from_asset = asset_to_edit.get("account_type_id")

        # 銀行名 (Dropdown) に ID を設定
        if bank_id_from_asset:
            bank_name_field.value = str(bank_id_from_asset)
        else:
            bank_name_field.value = "def" # Dropdownクリアのため value="" を使用
            
        # 口座種類 (Dropdown) に ID を設定
        if account_type_id_from_asset:
            account_type_field.value = str(account_type_id_from_asset)
        else:
            account_type_field.value = "def" # Dropdownクリアのため value="" を使用
        
        # 銀行コード、支店コードは TextField に値を設定
        bank_code_field.value = asset_to_edit.get("bank_code", "")
        
        account_number_field.value = asset_to_edit["account_number"]
        balance_field.value = (
            f"{asset_to_edit['balance']:,.0f}" if asset_to_edit["balance"] is not None else ""
        )
        status_field.value = asset_to_edit["status"]

        # 💡 銀行IDが設定されたら、連動更新ロジックをトリガー
        if bank_id_from_asset:
            # update_bank_details が銀行コード設定と支店リストロードを行う
            update_bank_details(page)
            
            # 支店リストがロードされた後、支店名をIDで設定し直す
            if branch_id_from_asset:
                branch_name_field.value = str(branch_id_from_asset)
            else:
                branch_name_field.value = "def"

        branch_code_field.value = asset_to_edit.get("branch_code", "") 
        
        # UIモードを「修正」に切り替え
        main_action_button.text = "口座情報を修正"
        main_action_button.icon = Icons.SAVE
        cancel_edit_button.visible = True

        bank_name_field.update()
        branch_name_field.update()
        account_type_field.update()
        bank_code_field.update()
        branch_code_field.update()
        account_number_field.update()
        balance_field.update()
        status_field.update()
        main_action_button.update()
        cancel_edit_button.update()

        update_branch_details(e.page)
        
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

                account_type_info = f"種類: {asset.get('account_type', 'N/A')}"

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
                                account_type_info,
                                size=14,
                                width=100, # 幅を調整
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
        page = e.page # pageオブジェクトを取得
        case_id_val = case_id # case_idをローカル変数として取得

        # フォームからの値を取得
        # 💡 Dropdownの value は文字列IDまたは 'add_new_bank'
        bank_id_str = bank_name_field.value
        branch_id_str = branch_name_field.value
        account_type_id_str = account_type_field.value

        account_number = account_number_field.value.strip()
        balance_str = balance_field.value.strip().replace(",", "")
        status = status_field.value.strip()
        
        # ----------------------------------------------------
        # 1. 必須チェックと型変換 (DBスキーマに基づく)
        # ----------------------------------------------------

        bank_id = None
        branch_id = None
        account_type_id = None
        balance_value = 0.0

        try:
            # 必須入力チェック: 銀行IDと口座種類IDは必須 (nullable=False)
            if not bank_id_str or bank_id_str == "add_new_bank":
                raise ValueError("銀行を選択してください。")
            # if not account_type_id_str:
            #     raise ValueError("口座種類を選択してください。")

            bank_id = int(bank_id_str)
            account_type_id = int(account_type_id_str)
            
            # 支店IDは任意 (nullable=True)
            branch_id = int(branch_id_str) if branch_id_str else None
            
            # 残高
            balance_value = float(balance_str) if balance_str else 0.0

        except ValueError as ve:
            # 型変換エラーまたは必須項目エラー
            error_message = str(ve) if str(ve) else "入力値が無効です。"
            page.open(
                SnackBar(
                    content=Text(error_message, color=Colors.WHITE),
                    bgcolor=Colors.RED_700,
                )
            )
            page.update()
            return
            
        # ----------------------------------------------------
        # 2. サービス層への呼び出し (編集モード vs 新規登録モード)
        # ----------------------------------------------------
        
        try:
            # 編集モード
            if editing_asset_id:
                # サービス関数を呼び出して更新
                success = update_financial_asset(
                    asset_id=editing_asset_id,
                    bank_id=bank_id,
                    branch_id=branch_id,
                    account_type_id=account_type_id,
                    account_number=account_number, # ローカル変数を渡す
                    balance=balance_value,         # ローカル変数を渡す
                    status=status,                 # ローカル変数を渡す
                )
                print(f"DEBUG: 資産ID {editing_asset_id} を修正しました。")
                success_message = "銀行口座情報を修正しました。"

            # 新規登録モード
            else:
                # サービス関数を呼び出して新規登録
                success = add_financial_asset(
                    case_id=case_id_val,
                    bank_id=bank_id,
                    branch_id=branch_id,
                    account_type_id=account_type_id,
                    account_number=account_number, # ローカル変数を渡す
                    balance=balance_value,         # ローカル変数を渡す
                    status=status,                 # ローカル変数を渡す
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

    # 銀行名ドロップダウンのオプションを初期ロードする
    load_bank_options(page)

    load_account_type_options(page)
    
    # 登録済み資産のリストを初期ロードする (既に存在)
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
                        Row([account_number_field, account_type_field, balance_field, status_field]),
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