# components/pages/securities_edit.py

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

# 証券会社も金融機関コード（4桁）を持つため、zengin_codeを利用できる場合は利用する
from zengin_code import Bank

from services.db_setup import BankMaster, Engine, Session

# 💡 証券用のサービス関数
from services.deceased_service import (
    add_financial_asset_with_type,
    add_or_update_bank_master,
    delete_financial_asset,
    get_account_type_masters,
    get_bank_master_by_id,
    get_bank_masters,
    get_branch_masters_by_bank_id,
    get_financial_asset_by_case_and_type,
    update_financial_asset,
)

# 💡 共通ファイルからマスタデータをインポート
from services.securities_data import SECURITIES_LIST, SECURITIES_MASTER

# ---------------------------------------------
# 部店マスタ (BranchMaster) 編集/新規登録用モーダル (追加)
# ---------------------------------------------

dialog_branch_name_field = TextField(label="部店名", width=250)
dialog_branch_code_field = TextField(label="部店コード", width=150)
dialog_branch_save_button = ElevatedButton("保存")

branch_master_edit_dialog = AlertDialog(
    title=Text("部店マスタの登録"),
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
# 部店マスタ関連ロジック (追加)
# ---------------------------------------------


def open_branch_dialog(page: Page):
    """部店登録モーダルを開く"""
    # 親となる証券会社が選択されているかチェック
    if not securities_name_field.value or securities_name_field.value in ["def", "add_new"]:
        page.open(SnackBar(Text("先に証券会社を選択してください。"), bgcolor=Colors.RED_500))
        page.update()
        # ドロップダウンをリセット
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
    """部店マスタを保存"""
    name = dialog_branch_name_field.value
    code = dialog_branch_code_field.value
    parent_bank_id = int(securities_name_field.value)  # 親ID

    if not name or not code:
        page.open(SnackBar(Text("部店名とコードは必須です。"), bgcolor=Colors.RED_500))
        page.update()
        return

    with Session(bind=Engine) as db:
        from services.db_setup import BranchMaster

        # 重複チェック（簡易）
        existing = (
            db.query(BranchMaster)
            .filter(BranchMaster.bank_id == parent_bank_id, BranchMaster.branch_code == code)
            .first()
        )

        if existing:
            page.open(
                SnackBar(Text("この部店コードは既に登録されています。"), bgcolor=Colors.RED_500)
            )
            page.update()
            return

        try:
            new_branch = BranchMaster(bank_id=parent_bank_id, branch_name=name, branch_code=code)
            db.add(new_branch)
            db.commit()

            # 成功処理
            close_branch_dialog(None, page)
            page.open(SnackBar(Text("部店を登録しました。"), bgcolor=Colors.GREEN_500))

            # リストをリロードして、今登録した支店を選択状態にする
            load_branch_options(page, parent_bank_id)
            branch_name_field.value = str(new_branch.id)
            branch_code_field.value = new_branch.branch_code

            # 画面更新
            branch_name_field.update()
            branch_code_field.update()

        except Exception as ex:
            db.rollback()
            print(ex)
            page.open(SnackBar(Text("保存エラーが発生しました。"), bgcolor=Colors.RED_500))
            page.update()


# ---------------------------------------------
# 証券会社検索ヘルパー (独自マスタを使用)
# ---------------------------------------------


def find_securities_global(name=None, code=None):
    """証券会社コード検索 (独自マスタ利用)"""
    # コード検索
    if code:
        return SECURITIES_MASTER.get(code)

    # 名称検索 (部分一致)
    if name:
        # 検索用文字列の正規化（「証券」などを削除）
        search_name = name.replace("証券", "").replace("株式会社", "").strip()

        for sec in SECURITIES_LIST:
            # 名前またはカナで部分一致
            if search_name in sec["name"] or search_name in sec["kana"]:
                return sec
    return None


# ---------------------------------------------
# UI定義: 証券登録フォーム
# ---------------------------------------------

# 証券会社名 (内部的にはBankMasterを利用)
securities_name_field = Dropdown(
    label="証券会社名 *",
    width=250,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)

# 本店・支店名 (内部的にはBranchMasterを利用)
branch_name_field = Dropdown(
    label="部店名 (本店・支店)",
    width=250,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)

# 口座種類 (特定、一般、NISAなど)
account_type_field = Dropdown(
    label="口座種類",
    width=150,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)

# 金融機関コード
securities_code_field = TextField(
    label="金融機関コード",
    width=100,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)

# 部店コード
branch_code_field = TextField(
    label="部店コード",
    width=100,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)

account_number_field = TextField(
    label="口座番号 (加入者コード) *",
    width=250,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK),
)

balance_field = TextField(
    label="評価額 (調査時点)",
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
# 証券マスタ(BankMaster) 編集/新規登録用モーダル
# ---------------------------------------------


# Zengin Code検索用ヘルパー (グローバル)
def find_zengin_bank_global(name=None, code=None):
    """全銀コード検索"""
    if code and code in Bank.all:
        return Bank.all[code]
    if name:
        search_name = name.replace("証券", "").replace("株式会社", "")
        for bank_data in Bank.all.values():
            # 部分一致検索
            if search_name in bank_data.name:
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
    data = e.control.data  # Bankオブジェクト または 証券辞書

    name_val = ""
    code_val = ""

    # 💡 データ型によって取り出し方を変える
    if isinstance(data, dict):
        # 証券会社（辞書）の場合: ["key"] でアクセス
        name_val = data["name"]
        code_val = data["code"]
    else:
        # 銀行（zengin_codeオブジェクト）の場合: .attr でアクセス
        name_val = f"{data.name}銀行"
        code_val = data.code

    # 値をセット
    dialog_securities_name_field.value = name_val
    dialog_securities_code_field.value = code_val

    # UI更新
    dialog_securities_name_field.update()
    dialog_securities_code_field.update()

    # リストを閉じる
    suggestions_container.visible = False
    suggestions_container.update()

    # 保存ボタンへフォーカス移動
    dialog_save_button.focus()


def on_dialog_name_change(e):
    """証券会社名入力時のインクリメンタルサーチ"""
    val = dialog_securities_name_field.value.strip()
    if not val:
        suggestions_container.visible = False
        suggestions_container.update()
        return

    matches = []
    search_term = val.replace("証券", "").replace("株式会社", "")

    # 💡 独自マスタ(SECURITIES_LIST)から検索
    for sec in SECURITIES_LIST:
        if search_term in sec["name"] or val in sec["kana"]:
            matches.append(sec)

    # 候補リストの構築
    if matches:
        list_view = suggestions_container.content
        list_view.controls.clear()
        for sec in matches:
            # Bankオブジェクトではなく辞書データなのでアクセス方法を変える
            list_view.controls.append(
                ListTile(
                    title=Text(f"{sec['name']}", size=14),
                    subtitle=Text(f"{sec['kana']} ({sec['code']})", size=12, color=Colors.GREY),
                    data=sec,  # 辞書データを保持
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


# UI定義
dialog_securities_name_field = TextField(
    label="証券会社名",
    width=300,
    on_change=on_dialog_name_change,
)
dialog_securities_code_field = TextField(label="金融機関コード", width=150)
dialog_save_button = ElevatedButton("保存")

current_editing_master_id: int | None = None

securities_master_edit_dialog = AlertDialog(
    title=Text("証券会社マスタの登録/編集"),
    content=Column(
        [
            dialog_securities_name_field,
            suggestions_container,
            dialog_securities_code_field,
        ],
        tight=True,
        spacing=5,
    ),
    actions=[],
    modal=True,
)

# ---------------------------------------------
# マスターデータ関連ロジック
# ---------------------------------------------


def open_master_dialog(page: Page, master_id: int | None):
    """マスタ登録モーダルを開く"""
    global current_editing_master_id
    current_editing_master_id = master_id
    dialog_save_button.on_click = lambda e: save_master(e, page)

    if master_id is not None:
        with Session(bind=Engine) as db:
            master = get_bank_master_by_id(db, master_id)
            if master:
                dialog_securities_name_field.value = master.bank_name
                dialog_securities_code_field.value = master.bank_code
                securities_master_edit_dialog.title.value = "証券会社情報の編集"
            else:
                return
    else:
        dialog_securities_name_field.value = ""
        dialog_securities_code_field.value = ""
        securities_master_edit_dialog.title.value = "新しい証券会社を登録"

    securities_master_edit_dialog.actions = [
        TextButton("キャンセル", on_click=lambda e: close_master_dialog(e, page)),
        dialog_save_button,
    ]
    page.open(securities_master_edit_dialog)
    page.update()


def close_master_dialog(e, page: Page):
    securities_master_edit_dialog.open = False
    page.update()


def save_master(e, page: Page):
    name = dialog_securities_name_field.value
    code = dialog_securities_code_field.value

    if not name or not code:
        page.open(SnackBar(Text("名称とコードは必須です。"), bgcolor=Colors.RED_500))
        page.update()
        return

    with Session(bind=Engine) as db:
        # 銀行マスタテーブルを証券会社マスタとして兼用
        new_master = add_or_update_bank_master(db, current_editing_master_id, name, code)

    if new_master:
        load_securities_options(page)
        securities_name_field.value = str(new_master.id)
        update_securities_details(page)
        close_master_dialog(None, page)
        page.open(SnackBar(Text("保存しました。"), bgcolor=Colors.GREEN_500))
    else:
        page.open(SnackBar(Text("保存に失敗しました。"), bgcolor=Colors.RED_500))
    page.update()


# ---------------------------------------------
# フィールド連動・ロードロジック
# ---------------------------------------------


def load_securities_options(page: Page):
    """
    SECURITIES_MASTER の内容をDBに自動登録（同期）し、
    証券会社のみをフィルタリングしてドロップダウンに表示する
    """
    with Session(bind=Engine) as db:
        # -------------------------------------------------
        # 1. 自動登録ロジック (Sync)
        # -------------------------------------------------

        # 現在DBに登録されている全ての金融機関コードを取得 (高速化のためSetにする)
        existing_codes = set(code[0] for code in db.query(BankMaster.bank_code).all())

        added_count = 0
        for code, info in SECURITIES_MASTER.items():
            # マスタにあるコードがDBになければ新規登録
            if code not in existing_codes:
                new_sec = BankMaster(bank_name=info["name"], bank_code=code)
                db.add(new_sec)
                added_count += 1

        if added_count > 0:
            db.commit()
            print(f"DEBUG: {added_count} 件の証券会社マスタを自動登録しました。")

        # -------------------------------------------------
        # 2. 表示用リストの作成
        # -------------------------------------------------

        # 自動登録分も含めて全マスタを再取得
        masters = get_bank_masters(db)

        options = [
            dropdown.Option("def", text="選択してください"),
            dropdown.Option("add_new", text="[ ➕ 新しい証券会社を登録 ]"),
        ]

        for m in masters:
            # 判定ロジック:
            # A. 金融機関コードが SECURITIES_MASTER (主要証券リスト) に含まれている
            # B. または、名称に「証券」が含まれている (手動登録分などをカバー)
            is_security = (m.bank_code in SECURITIES_MASTER) or ("証券" in m.bank_name)

            if is_security:
                options.append(dropdown.Option(str(m.id), text=f"{m.bank_name} ({m.bank_code})"))

        securities_name_field.options = options


def update_securities_details(page: Page):
    """証券会社選択時の処理"""
    selected_id_str = securities_name_field.value
    if selected_id_str == "add_new":
        securities_name_field.value = ""
        open_master_dialog(page, None)
        securities_name_field.update()
        return

    if selected_id_str and selected_id_str != "def":
        try:
            master_id = int(selected_id_str)
            with Session(bind=Engine) as db:
                master = get_bank_master_by_id(db, master_id)
                if master:
                    securities_code_field.value = master.bank_code
                    load_branch_options(page, master_id)
                    securities_code_field.update()
                    page.update()
                    return
        except ValueError:
            pass

    # リセット
    securities_code_field.value = ""
    branch_name_field.options = []
    branch_name_field.value = "def"
    branch_code_field.value = ""
    page.update()


def load_branch_options(page: Page, master_id: int):
    """部店マスタロード"""
    branch_name_field.value = "def"
    branch_code_field.value = ""
    with Session(bind=Engine) as db:
        branches = get_branch_masters_by_bank_id(db, master_id)
        branch_name_field.options = [
            dropdown.Option("def", text="選択してください"),
            dropdown.Option("add_new_branch", text="[ ➕ 新しい部店を登録 ]"),
        ]
        branch_name_field.options.extend(
            [
                dropdown.Option(str(b.id), text=f"{b.branch_name} ({b.branch_code})")
                for b in branches
            ]
        )
    load_account_type_options(page)


def update_branch_details(page: Page):
    """部店選択時の処理 (修正版)"""
    selected_str = branch_name_field.value

    # 💡 [ ➕ 新しい部店を登録 ] が選ばれた場合
    if selected_str == "add_new_branch":
        open_branch_dialog(page)
        return

    # 通常の支店選択処理
    if selected_str and selected_str != "def":
        try:
            branch_id = int(selected_str)
            with Session(bind=Engine) as db:
                from services.db_setup import BranchMaster

                branch = db.query(BranchMaster).filter(BranchMaster.id == branch_id).first()
                if branch:
                    branch_code_field.value = branch.branch_code
                    branch_code_field.update()
        except ValueError:
            pass

    elif selected_str == "def":
        branch_code_field.value = ""
        branch_code_field.update()

    page.update()


def load_account_type_options(page: Page):
    """口座種類ロード"""
    with Session(bind=Engine) as db:
        types = get_account_type_masters(db)
        account_type_field.options = [dropdown.Option(str(t.id), text=t.type_name) for t in types]


# ---------------------------------------------
# メインロジック
# ---------------------------------------------

assets_list_view = ListView(spacing=10, expand=True)

main_action_button = ElevatedButton(
    "証券口座を登録", icon=Icons.ADD_CARD, bgcolor=Colors.BLUE_600, color=Colors.WHITE
)
cancel_edit_button = ElevatedButton(
    "キャンセル", icon=Icons.CANCEL, visible=False, bgcolor=Colors.GREY_600, color=Colors.WHITE
)


def SecuritiesEditView(page: Page, case_id: int):
    editing_asset_id = None

    # イベントハンドラ設定
    securities_name_field.on_change = lambda e: update_securities_details(page)
    branch_name_field.on_change = lambda e: update_branch_details(page)

    def reset_form():
        nonlocal editing_asset_id
        editing_asset_id = None
        securities_name_field.value = "def"
        securities_code_field.value = ""
        branch_name_field.value = "def"
        branch_code_field.value = ""
        account_number_field.value = ""
        balance_field.value = ""
        status_field.value = "調査中"

        main_action_button.text = "証券口座を登録"
        main_action_button.icon = Icons.ADD_CARD
        cancel_edit_button.visible = False
        page.update()

    # 💡 共通コピー関数
    def copy_to_clipboard(e, text):
        if not text or text == "N/A":
            return
        page.set_clipboard(text)
        page.open(
            SnackBar(
                content=Text(f"「{text}」をコピーしました", color=Colors.WHITE),
                bgcolor=Colors.GREEN_700,
                duration=1000,
            )
        )
        page.update()

    def update_assets_list():
        # 💡 asset_type="SECURITIES" でフィルタリングして取得
        assets = get_financial_asset_by_case_and_type(case_id, "SECURITIES")
        assets_list_view.controls.clear()

        if not assets:
            assets_list_view.controls.append(
                Text("登録された証券口座はありません。", color=Colors.GREY_600)
            )
        else:
            for asset in assets:
                balance_str = f"¥{asset['balance']:,.0f}" if asset["balance"] is not None else "-"
                
                # 表示用データの準備
                securities_name = asset['bank_name']
                securities_code = asset.get('bank_code', '-')
                title_info = f"🏢 {securities_name} ({securities_code})"
                
                branch_name = asset.get('branch_name', '-')
                account_type = asset.get('account_type', '-')
                sub_info = f"{branch_name} | {account_type}"
                
                account_number = asset['account_number']
                account_info = f"口座: {account_number}"
                
                balance_info = f"評価額: {balance_str}"

                # 💡 クリック可能なコンテナを作成するヘルパー
                def create_clickable_text(text, data_val, width=None):
                    return Container(
                        content=Text(
                            text,
                            size=14,
                            weight=FontWeight.BOLD if "🏢" in text else FontWeight.NORMAL,
                            color=Colors.BLACK87,
                        ),
                        width=width,
                        on_click=lambda e: copy_to_clipboard(e, data_val),
                        tooltip="クリックしてコピー",
                        padding=5,
                        border_radius=5,
                        ink=True,
                    )

                assets_list_view.controls.append(
                    Row(
                        [
                            create_clickable_text(title_info, securities_name, width=200),
                            create_clickable_text(sub_info, branch_name, width=200),
                            create_clickable_text(account_info, account_number, width=150),
                            create_clickable_text(balance_info, str(asset['balance']), width=120),
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
                        ]
                    )
                )
        page.update()

    def start_edit(e):
        nonlocal editing_asset_id
        asset_id = e.control.data
        assets = get_financial_asset_by_case_and_type(case_id, "SECURITIES")
        target = next((a for a in assets if a["id"] == asset_id), None)

        if target:
            editing_asset_id = asset_id
            # 値のセット
            if target.get("bank_id"):
                securities_name_field.value = str(target["bank_id"])
                update_securities_details(page)  # 連動ロード

            if target.get("branch_id"):
                branch_name_field.value = str(target["branch_id"])

            if target.get("account_type_id"):
                account_type_field.value = str(target["account_type_id"])

            securities_code_field.value = target.get("bank_code", "")
            branch_code_field.value = target.get("branch_code", "")
            account_number_field.value = target["account_number"]
            balance_field.value = f"{target['balance']:,.0f}" if target["balance"] else ""
            status_field.value = target["status"]

            main_action_button.text = "口座情報を修正"
            main_action_button.icon = Icons.SAVE
            cancel_edit_button.visible = True
            page.update()

    def delete_asset(e):
        delete_financial_asset(e.control.data)
        update_assets_list()
        page.open(SnackBar(Text("削除しました"), bgcolor=Colors.RED_700))
        page.update()

    def save_asset(e):
        nonlocal editing_asset_id

        # バリデーションと変換
        try:
            if not securities_name_field.value or securities_name_field.value in ["def", "add_new"]:
                raise ValueError("証券会社を選択してください")

            master_id = int(securities_name_field.value)
            branch_id = (
                int(branch_name_field.value)
                if branch_name_field.value
                and branch_name_field.value not in ["def", "add_new_branch"]
                else None
            )
            acc_type_id = (
                int(account_type_field.value)
                if account_type_field.value and account_type_field.value != "def"
                else None
            )

            balance_val = (
                float(balance_field.value.replace(",", "")) if balance_field.value else 0.0
            )

            # 💡 asset_type="SECURITIES" で保存
            if editing_asset_id:
                update_financial_asset(
                    asset_id=editing_asset_id,
                    bank_id=master_id,
                    branch_id=branch_id,
                    account_type_id=acc_type_id,
                    account_number=account_number_field.value,
                    balance=balance_val,
                    status=status_field.value,
                )
            else:
                add_financial_asset_with_type(
                    case_id=case_id,
                    asset_type="SECURITIES",  # 💡 ここで種別指定
                    bank_id=master_id,
                    branch_id=branch_id,
                    account_type_id=acc_type_id,
                    account_number=account_number_field.value,
                    balance=balance_val,
                    status=status_field.value,
                )

            page.open(SnackBar(Text("保存しました"), bgcolor=Colors.GREEN_700))
            reset_form()
            update_assets_list()

        except Exception as ex:
            print(ex)
            page.open(SnackBar(Text(f"エラー: {ex}"), bgcolor=Colors.RED_700))
            page.update()

    main_action_button.on_click = save_asset
    cancel_edit_button.on_click = lambda e: reset_form()

    # 初期化
    load_securities_options(page)
    load_account_type_options(page)
    update_assets_list()

    return Column(
        controls=[
            Text("💹 証券口座登録", size=24, weight=FontWeight.BOLD),
            Divider(),
            Container(
                content=Column(
                    [
                        Text("証券口座情報", weight=FontWeight.W_600, color=Colors.BLACK),
                        Row([securities_name_field, securities_code_field]),
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
            Text("登録済み証券口座一覧", size=18, weight=FontWeight.BOLD),
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