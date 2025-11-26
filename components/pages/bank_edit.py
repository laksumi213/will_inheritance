# /components/pages/bank_edit.py
from flet import (
    AlertDialog,
    Colors,
    Column,
    Container,
    Divider,
    Dropdown,
    ElevatedButton,
    FontWeight,
    IconButton,
    Icons,
    ListTile,
    ListView,
    MainAxisAlignment,
    Page,
    Row,
    SnackBar,
    Text,
    TextButton,
    TextField,
    TextStyle,
    border,
    dropdown,
)
from zengin_code import Bank

from services.db_setup import (
    Engine,
    Session,
)
from services.deceased_service import (
    add_financial_asset,
    add_or_update_bank_master,
    delete_financial_asset,
    get_account_type_masters,
    get_bank_master_by_id,
    get_bank_masters,
    get_branch_masters_by_bank_id,
    get_financial_asset_by_case,
    update_financial_asset,
)
from services.securities_data import SECURITIES_MASTER

# ---------------------------------------------
# UIコンポーネント定義
# ---------------------------------------------

# 銀行名フィールド
bank_name_field = Dropdown(
    label="銀行名 *",
    width=250,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)

# 支店名フィールド
branch_name_field = Dropdown(
    label="支店名",
    width=250,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)

# 口座種類フィールド
account_type_field = Dropdown(
    label="口座種類",
    width=150,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)

# 銀行コード
bank_code_field = TextField(
    label="銀行コード",
    width=100,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
    autofocus=True,
)
# 支店コード
branch_code_field = TextField(
    label="支店コード",
    width=100,
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

# ---------------------------------------------
# 銀行マスタ編集/新規登録用モーダル UI
# ---------------------------------------------


# Zengin Code検索用ヘルパー
def find_zengin_bank_global(name=None, code=None):
    """全銀コード検索 (モーダル用)"""
    if code and code in Bank.all:
        return Bank.all[code]
    if name:
        search_name = (
            name.replace("銀行", "").replace("農業協同組合", "農協").replace("信用金庫", "信金")
        )
        for bank_data in Bank.all.values():
            if bank_data.name == search_name:
                return bank_data
    return None


# 候補リスト用コンテナ
suggestions_container = Container(
    content=ListView(height=150, spacing=0),
    visible=False,
    bgcolor=Colors.WHITE,
    border=border.all(1, Colors.GREY_300),
    border_radius=5,
    padding=0,
    width=300,
)


def select_suggestion(e):
    """サジェスト候補を選択した時の処理"""
    bank_data = e.control.data
    dialog_bank_name_field.value = f"{bank_data.name}銀行"
    dialog_bank_code_field.value = bank_data.code
    dialog_bank_name_field.update()
    dialog_bank_code_field.update()
    suggestions_container.visible = False
    suggestions_container.update()
    dialog_save_button.focus()


def on_dialog_bank_name_change(e):
    """銀行名入力時のインクリメンタルサーチ処理"""
    val = dialog_bank_name_field.value.strip()
    if not val:
        suggestions_container.visible = False
        suggestions_container.update()
        return

    matches = []
    count = 0
    search_term = val.replace("銀行", "")

    for bank in Bank.all.values():
        if search_term in bank.name or val in bank.kana:
            matches.append(bank)
            count += 1
            if count >= 10:
                break

    if matches:
        list_view = suggestions_container.content
        list_view.controls.clear()
        for bank in matches:
            list_view.controls.append(
                ListTile(
                    title=Text(f"{bank.name}銀行", size=14),
                    subtitle=Text(f"{bank.kana} ({bank.code})", size=12, color=Colors.GREY),
                    data=bank,
                    on_click=select_suggestion,
                    dense=True,
                    bgcolor=Colors.WHITE,
                    hover_color=Colors.BLUE_50,
                )
            )
        suggestions_container.visible = True
    else:
        suggestions_container.visible = False
    suggestions_container.update()


def on_dialog_bank_name_blur(e):
    val = dialog_bank_name_field.value
    if val:
        bank = find_zengin_bank_global(name=val)
        if bank:
            dialog_bank_code_field.value = bank.code
            dialog_bank_code_field.update()
            suggestions_container.visible = False
            suggestions_container.update()
            dialog_save_button.focus()
            e.page.update()


def on_dialog_bank_code_blur(e):
    val = dialog_bank_code_field.value
    if val and len(val) == 4:
        bank = find_zengin_bank_global(code=val)
        if bank:
            dialog_bank_name_field.value = f"{bank.name}銀行"
            dialog_bank_name_field.update()
            dialog_save_button.focus()
            e.page.update()


dialog_bank_name_field = TextField(
    label="銀行名",
    width=300,
    on_change=on_dialog_bank_name_change,
    on_blur=on_dialog_bank_name_blur,
)
dialog_bank_code_field = TextField(label="銀行コード", width=150, on_blur=on_dialog_bank_code_blur)
dialog_save_button = ElevatedButton("保存")
current_editing_bank_id: int | None = None

bank_master_edit_dialog = AlertDialog(
    title=Text("銀行マスタの登録/編集"),
    content=Column(
        [
            dialog_bank_name_field,
            suggestions_container,
            dialog_bank_code_field,
        ],
        tight=True,
        spacing=5,
    ),
    actions=[],
    modal=True,
)

# ---------------------------------------------
# 支店マスタ (BranchMaster) 編集/新規登録用モーダル
# ---------------------------------------------

dialog_branch_name_field = TextField(label="支店名", width=250)
dialog_branch_code_field = TextField(label="支店コード", width=150)
dialog_branch_save_button = ElevatedButton("保存")

branch_master_edit_dialog = AlertDialog(
    title=Text("支店マスタの登録"),
    content=Column(
        [
            dialog_branch_name_field,
            dialog_branch_code_field,
        ],
        tight=True,
        spacing=10,
    ),
    actions=[],
    modal=True,
)

# ---------------------------------------------
# 支店マスタ関連ロジック
# ---------------------------------------------


def open_branch_dialog(page: Page):
    """支店登録モーダルを開く"""
    # 親となる銀行が選択されているかチェック
    if not bank_name_field.value or bank_name_field.value in ["def", "add_new_bank"]:
        page.open(SnackBar(Text("先に銀行を選択してください。"), bgcolor=Colors.RED_500))
        page.update()
        branch_name_field.value = "def"
        branch_name_field.update()
        return

    # フォームクリア
    dialog_branch_name_field.value = ""
    dialog_branch_code_field.value = ""

    dialog_branch_save_button.on_click = lambda e: save_branch_master(e, page)

    branch_master_edit_dialog.actions = [
        TextButton("キャンセル", on_click=lambda e: close_branch_dialog(e, page)),
        dialog_branch_save_button,
    ]

    page.open(branch_master_edit_dialog)
    page.update()
    dialog_branch_name_field.focus()


def close_branch_dialog(e, page: Page):
    branch_master_edit_dialog.open = False
    page.update()


def save_branch_master(e, page: Page):
    """支店マスタを保存"""
    name = dialog_branch_name_field.value
    code = dialog_branch_code_field.value

    try:
        parent_bank_id = int(bank_name_field.value)
    except ValueError:
        return

    if not name or not code:
        page.open(SnackBar(Text("支店名とコードは必須です。"), bgcolor=Colors.RED_500))
        page.update()
        return

    with Session(bind=Engine) as db:
        from services.db_setup import BranchMaster

        existing = (
            db.query(BranchMaster)
            .filter(BranchMaster.bank_id == parent_bank_id, BranchMaster.branch_code == code)
            .first()
        )

        if existing:
            page.open(
                SnackBar(Text("この支店コードは既に登録されています。"), bgcolor=Colors.RED_500)
            )
            page.update()
            return

        try:
            new_branch = BranchMaster(bank_id=parent_bank_id, branch_name=name, branch_code=code)
            db.add(new_branch)
            db.commit()

            close_branch_dialog(None, page)
            page.open(SnackBar(Text("支店を登録しました。"), bgcolor=Colors.GREEN_500))

            load_branch_options(page, parent_bank_id)
            branch_name_field.value = str(new_branch.id)
            branch_code_field.value = new_branch.branch_code

            branch_name_field.update()
            branch_code_field.update()

        except Exception as ex:
            db.rollback()
            print(ex)
            page.open(SnackBar(Text("保存エラーが発生しました。"), bgcolor=Colors.RED_500))
            page.update()


# ---------------------------------------------
# マスターデータ関連のロジック
# ---------------------------------------------


def open_bank_master_dialog(page: Page, bank_id: int | None):
    """銀行マスタの登録/編集モーダルを開く"""
    global current_editing_bank_id
    current_editing_bank_id = bank_id
    dialog_save_button.on_click = lambda e: save_bank_master(e, page)

    if bank_id is not None:
        with Session(bind=Engine) as db:
            bank = get_bank_master_by_id(db, bank_id)
            if bank:
                dialog_bank_name_field.value = bank.bank_name
                dialog_bank_code_field.value = bank.bank_code
                bank_master_edit_dialog.title.value = "銀行マスタの編集"
            else:
                return
    else:
        dialog_bank_name_field.value = ""
        dialog_bank_code_field.value = ""
        bank_master_edit_dialog.title.value = "新しい銀行を登録"

    bank_master_edit_dialog.actions = [
        TextButton("キャンセル", on_click=lambda e: close_bank_master_dialog(e, page)),
        dialog_save_button,
    ]

    page.open(bank_master_edit_dialog)
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
        page.open(
            SnackBar(
                Text("銀行名と銀行コードは必須です。"),
                bgcolor=Colors.RED_500,
            )
        )
        page.update()
        return

    with Session(bind=Engine) as db:
        new_bank = add_or_update_bank_master(db, current_editing_bank_id, bank_name, bank_code)

    if new_bank:
        load_bank_options(page)
        bank_name_field.value = str(new_bank.id)
        update_bank_details(page)
        close_bank_master_dialog(None, page)
        page.open(SnackBar(Text("銀行情報が正常に保存されました。"), bgcolor=Colors.GREEN_500))
    else:
        page.open(
            SnackBar(
                Text("銀行情報の保存に失敗しました。重複している可能性があります。"),
                bgcolor=Colors.RED_500,
            )
        )
    page.update()


def load_bank_options(page: Page):
    """銀行マスタをロードし、証券会社を除外してドロップダウンの選択肢を更新する"""
    with Session(bind=Engine) as db:
        banks = get_bank_masters(db)
        options = [
            dropdown.Option("def", text="選択してください"),
            dropdown.Option("add_new_bank", text="[ ➕ 新しい銀行を登録 ]"),
        ]

        for bank in banks:
            # 💡 判定ロジック: 証券会社かどうか
            # 新しい共通ファイルからインポートした SECURITIES_MASTER を使用
            is_security = (bank.bank_code in SECURITIES_MASTER) or ("証券" in bank.bank_name)

            # 証券会社でない場合（＝銀行の場合）のみ追加
            if not is_security:
                options.append(
                    dropdown.Option(str(bank.id), text=f"{bank.bank_name} ({bank.bank_code})")
                )

        bank_name_field.options = options
    # page.update()


def update_bank_details(page: Page):
    selected_bank_id_str = bank_name_field.value

    if selected_bank_id_str == "add_new_bank":
        bank_name_field.value = ""
        open_bank_master_dialog(page, None)
        bank_name_field.update()
        return

    if selected_bank_id_str:
        try:
            bank_id = int(selected_bank_id_str)
            with Session(bind=Engine) as db:
                bank = get_bank_master_by_id(db, bank_id)
                if bank:
                    bank_code_field.value = bank.bank_code
                    load_branch_options(page, bank_id)
                    bank_code_field.update()
                    page.update()
                    return
        except ValueError:
            pass

    bank_code_field.value = ""
    branch_name_field.options = []
    branch_name_field.value = "def"
    branch_code_field.value = ""
    page.update()


def update_branch_details(page: Page):
    """支店名選択時に支店コードを更新し、画面を更新する。"""
    selected_branch_id_str = branch_name_field.value

    # [ ➕ 新しい支店を登録 ] が選ばれた場合
    if selected_branch_id_str == "add_new_branch":
        open_branch_dialog(page)
        return

    if selected_branch_id_str:
        try:
            branch_id = int(selected_branch_id_str)
            with Session(bind=Engine) as db:
                from services.db_setup import BranchMaster

                branch = db.query(BranchMaster).filter(BranchMaster.id == branch_id).first()
                if branch:
                    branch_code_field.value = branch.branch_code
                    branch_code_field.update()
                    return
        except ValueError:
            pass

    branch_code_field.value = ""
    branch_code_field.update()
    page.update()


def load_branch_options(page: Page, bank_id: int):
    """選択された銀行に基づいて支店マスタをロードする"""
    branch_name_field.value = "def"
    branch_code_field.value = ""

    with Session(bind=Engine) as db:
        branches = get_branch_masters_by_bank_id(db, bank_id)
        branch_name_field.options = [
            dropdown.Option("def", text="選択してください"),
            dropdown.Option("add_new_branch", text="[ ➕ 新しい支店を登録 ]"),
        ]
        branch_name_field.options.extend(
            [
                dropdown.Option(str(branch.id), text=f"{branch.branch_name} ({branch.branch_code})")
                for branch in branches
            ]
        )
    load_account_type_options(page)


def load_account_type_options(page: Page):
    """口座種類マスタをロードする"""
    with Session(bind=Engine) as db:
        types = get_account_type_masters(db)
        account_type_field.options = [dropdown.Option(str(t.id), text=t.type_name) for t in types]


# ---------------------------------------------
# メインロジック
# ---------------------------------------------

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

    # ----------------------------------------------------
    # 自動補完関数 (zengin_codeの Bank/Branch オブジェクトを検索)
    # ----------------------------------------------------

    def get_bank_master_id_by_code(bank_code: str):
        with Session(bind=Engine) as db:
            from services.db_setup import BankMaster

            bank = db.query(BankMaster.id).filter(BankMaster.bank_code == bank_code).first()
            return bank[0] if bank else None

    def find_bank_data(name=None, code=None):
        if code and code in Bank.all:
            return Bank.all[code]
        if name:
            for bank_data in Bank.all.values():
                if bank_data.name == name.replace("銀行", "").replace(
                    "農業協同組合", "農協"
                ).replace("信用金庫", "信金"):
                    return bank_data
        return None

    def find_branch_data(bank_code: str, name=None, code=None):
        if bank_code in Bank.all:
            bank = Bank.all[bank_code]
            if code and code in bank.branches:
                return bank.branches[code]
            if name:
                for branch_data in bank.branches.values():
                    if branch_data.name == name.replace("支店", ""):
                        return branch_data
        return None

    def get_branch_master_id_by_code(bank_code: str, branch_code: str):
        with Session(bind=Engine) as db:
            from services.db_setup import BankMaster, BranchMaster

            bank_id = db.query(BankMaster.id).filter(BankMaster.bank_code == bank_code).scalar()
            if not bank_id:
                return None
            branch = (
                db.query(BranchMaster.id)
                .filter(BranchMaster.bank_id == bank_id, BranchMaster.branch_code == branch_code)
                .first()
            )
            return branch[0] if branch else None

    # ----------------------------------------------------
    # 自動補完ロジック (On Blur Handlers)
    # ----------------------------------------------------

    def handle_bank_change(e):
        bank_code = bank_code_field.value.strip()
        needs_update = False
        load_bank_options(page)

        if e.control == bank_code_field and bank_code and len(bank_code) == 4:
            bank = find_bank_data(code=bank_code)
            if bank:
                bank_master_id = get_bank_master_id_by_code(bank_code)
                if bank_master_id:
                    bank_name_field.value = str(bank_master_id)
                    bank_code_field.error_text = None
                    update_bank_details(page)
                    needs_update = True
                elif bank_name_field.value:
                    bank_name_field.value = "def"
                    bank_code_field.error_text = "該当する銀行コードがマスターに見つかりません。"
                    branch_name_field.options = []
                    branch_code_field.value = ""
                    needs_update = True

        if bank_code_field.value and len(bank_code_field.value) == 4:
            handle_branch_change(e)

        if not needs_update:
            e.page.update()

    def handle_branch_change(e):
        bank_code = bank_code_field.value.strip()
        branch_code = branch_code_field.value.strip()

        if not bank_code or len(bank_code) != 4:
            return
        if not branch_code or len(branch_code) != 3:
            return

        branch_master_id = get_branch_master_id_by_code(bank_code, branch_code)

        if branch_master_id:
            branch_name_field.value = str(branch_master_id)
            branch_code_field.error_text = None
        else:
            branch_name_field.value = "def"

        e.page.update()

    # フォームのハンドラ割り当て
    bank_name_field.on_change = lambda e: update_bank_details(page)
    bank_code_field.on_blur = handle_bank_change
    branch_name_field.on_change = lambda e: update_branch_details(page)
    branch_code_field.on_blur = handle_branch_change

    def reset_form_and_mode():
        nonlocal editing_asset_id
        editing_asset_id = None
        bank_name_field.value = "def"
        bank_code_field.value = ""
        branch_name_field.value = "def"
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
        asset_id = e.control.data
        try:
            delete_financial_asset(asset_id)
            update_assets_list()
            page.open(
                SnackBar(content=Text("削除しました。", color=Colors.WHITE), bgcolor=Colors.RED_700)
            )
        except Exception as ex:
            page.open(
                SnackBar(
                    content=Text(f"削除エラー: {ex}", color=Colors.WHITE), bgcolor=Colors.RED_700
                )
            )
        page.update()

    def start_edit(e):
        nonlocal editing_asset_id
        asset_id = e.control.data
        assets = get_financial_asset_by_case(case_id)
        asset_to_edit = next((a for a in assets if a["id"] == asset_id), None)

        if not asset_to_edit:
            return

        editing_asset_id = asset_id
        bank_id_from_asset = asset_to_edit.get("bank_id")
        branch_id_from_asset = asset_to_edit.get("branch_id")
        account_type_id_from_asset = asset_to_edit.get("account_type_id")

        if bank_id_from_asset:
            bank_name_field.value = str(bank_id_from_asset)
        else:
            bank_name_field.value = "def"

        if account_type_id_from_asset:
            account_type_field.value = str(account_type_id_from_asset)
        else:
            account_type_field.value = "def"

        bank_code_field.value = asset_to_edit.get("bank_code", "")
        account_number_field.value = asset_to_edit["account_number"]
        balance_field.value = (
            f"{asset_to_edit['balance']:,.0f}" if asset_to_edit["balance"] is not None else ""
        )
        status_field.value = asset_to_edit["status"]

        if bank_id_from_asset:
            update_bank_details(page)
            if branch_id_from_asset:
                branch_name_field.value = str(branch_id_from_asset)
            else:
                branch_name_field.value = "def"

        branch_code_field.value = asset_to_edit.get("branch_code", "")
        main_action_button.text = "口座情報を修正"
        main_action_button.icon = Icons.SAVE
        cancel_edit_button.visible = True
        page.update()
        bank_name_field.focus()

    def update_assets_list():
        assets = get_financial_asset_by_case(case_id)
        assets_list_view.controls.clear()

        if not assets:
            assets_list_view.controls.append(
                Text("登録された銀行口座情報はありません。", color=Colors.GREY_600)
            )
        else:
            for asset in assets:
                # 銀行のリストに証券口座を表示したくない場合はここでフィルタリングも可能
                # (SECURITIES_MASTER を使って判定するなど)
                is_security = (asset.get("bank_code") in SECURITIES_MASTER) or (
                    "証券" in asset.get("bank_name", "")
                )
                if is_security:
                    continue

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
                            Text(branch_info, size=14, width=200, color=Colors.BLACK),
                            Text(account_type_info, size=14, width=100, color=Colors.BLACK),
                            Text(
                                f"口座: {asset['account_number']}",
                                size=14,
                                width=200,
                                color=Colors.BLACK,
                            ),
                            Text(f"残高: {balance_str}", size=14, width=150, color=Colors.BLACK),
                            Text(f"状態: {asset['status']}", size=14, color=Colors.BLACK),
                            IconButton(
                                Icons.EDIT,
                                icon_color=Colors.BLUE_400,
                                data=asset["id"],
                                on_click=start_edit,
                            ),
                            IconButton(
                                Icons.DELETE,
                                icon_color=Colors.RED_400,
                                data=asset["id"],
                                on_click=delete_asset,
                            ),
                        ],
                        alignment=MainAxisAlignment.START,
                    )
                )
        page.update()

    def save_asset(e):
        nonlocal editing_asset_id
        bank_id_str = bank_name_field.value
        branch_id_str = branch_name_field.value
        account_type_id_str = account_type_field.value
        account_number = account_number_field.value.strip()
        balance_str = balance_field.value.strip().replace(",", "")
        status = status_field.value.strip()

        try:
            if not bank_id_str or bank_id_str == "add_new_bank":
                raise ValueError("銀行を選択してください。")

            bank_id = int(bank_id_str)
            account_type_id = (
                int(account_type_id_str)
                if account_type_id_str and account_type_id_str != "def"
                else None
            )
            branch_id = int(branch_id_str) if branch_id_str and branch_id_str != "def" else None
            balance_value = float(balance_str) if balance_str else 0.0

            if editing_asset_id:
                success = update_financial_asset(
                    editing_asset_id,
                    bank_id,
                    branch_id,
                    account_type_id,
                    account_number,
                    balance_value,
                    status,
                )
                msg = "修正しました。"
            else:
                # 銀行登録なので asset_type="BANK" (デフォルト)
                success = add_financial_asset(
                    case_id,
                    bank_id,
                    branch_id,
                    account_type_id,
                    account_number,
                    balance_value,
                    status,
                )
                msg = "登録しました。"

            if success:
                reset_form_and_mode()
                update_assets_list()
                page.open(SnackBar(content=Text(msg, color=Colors.WHITE), bgcolor=Colors.GREEN_700))
            else:
                raise Exception("DB操作失敗")

        except Exception as ex:
            page.open(
                SnackBar(content=Text(f"エラー: {ex}", color=Colors.WHITE), bgcolor=Colors.RED_700)
            )
        page.update()

    main_action_button.on_click = save_asset
    cancel_edit_button.on_click = lambda e: reset_form_and_mode()

    load_bank_options(page)
    load_account_type_options(page)
    update_assets_list()

    view_content = Column(
        controls=[
            Text("🏦 銀行口座登録", size=24, weight=FontWeight.BOLD),
            Divider(),
            Container(
                content=Column(
                    [
                        Text("口座情報入力", weight=FontWeight.W_600, color=Colors.BLACK),
                        Row([bank_name_field, bank_code_field]),
                        Row([branch_name_field, branch_code_field]),
                        Row(
                            [account_number_field, account_type_field, balance_field, status_field]
                        ),
                        Row(
                            [cancel_edit_button, main_action_button],
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
