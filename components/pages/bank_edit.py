# components/pages/bank_edit.py
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
    Control,
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
    add_account_type_master, # 💡 追加
    get_bank_master_by_id,
    get_bank_masters,
    get_branch_masters_by_bank_id,
    get_financial_asset_by_case,
    update_financial_asset,
)
from services.securities_data import SECURITIES_MASTER

# ---------------------------------------------
# 銀行マスタ編集/新規登録用ダイアログクラス
# ---------------------------------------------
class BankMasterEditDialog(AlertDialog):
    def __init__(self, page: Page, on_success: callable):
        super().__init__()
        self.page = page
        self.on_success = on_success
        self.current_editing_bank_id = None

        # UIコンポーネント
        self.name_field = TextField(
            label="銀行名",
            width=300,
            on_change=self.on_name_change,
            on_blur=self.on_name_blur,
        )
        self.code_field = TextField(
            label="銀行コード", 
            width=150, 
            on_blur=self.on_code_blur
        )
        
        # サジェストリスト
        self.suggestions_list = ListView(height=150, spacing=0)
        self.suggestions_container = Container(
            content=self.suggestions_list,
            visible=False,
            bgcolor=Colors.WHITE,
            border=border.all(1, Colors.GREY_300),
            border_radius=5,
            padding=0,
            width=300,
        )

        self.save_button = ElevatedButton("保存", on_click=self.save_master)
        
        self.title = Text("銀行マスタの登録/編集")
        self.content = Column(
            [
                self.name_field,
                self.suggestions_container,
                self.code_field,
            ],
            tight=True,
            spacing=5,
        )
        self.actions = [
            TextButton("キャンセル", on_click=self.close_dialog),
            self.save_button,
        ]
        self.modal = True

    def show(self, bank_id: int | None = None):
        """ダイアログを表示"""
        self.current_editing_bank_id = bank_id
        if bank_id is not None:
            with Session(bind=Engine) as db:
                bank = get_bank_master_by_id(db, bank_id)
                if bank:
                    self.name_field.value = bank.bank_name
                    self.code_field.value = bank.bank_code
                    self.title.value = "銀行マスタの編集"
        else:
            self.name_field.value = ""
            self.code_field.value = ""
            self.title.value = "新しい銀行を登録"
        
        self.suggestions_container.visible = False
        self.page.open(self)
        self.page.update()

    def close_dialog(self, e=None):
        self.page.close(self)
        self.page.update()

    def find_zengin_bank(self, name=None, code=None):
        if code and code in Bank.all:
            return Bank.all[code]
        if name:
            search_name = name.replace("銀行", "").replace("農業協同組合", "農協").replace("信用金庫", "信金")
            for bank_data in Bank.all.values():
                if bank_data.name == search_name:
                    return bank_data
        return None

    def on_name_change(self, e):
        val = self.name_field.value.strip()
        if not val:
            self.suggestions_container.visible = False
            self.suggestions_container.update()
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
            self.suggestions_list.controls.clear()
            for bank in matches:
                self.suggestions_list.controls.append(
                    ListTile(
                        title=Text(f"{bank.name}銀行", size=14),
                        subtitle=Text(f"{bank.kana} ({bank.code})", size=12, color=Colors.GREY),
                        data=bank,
                        on_click=self.select_suggestion,
                        dense=True,
                        bgcolor=Colors.WHITE,
                        hover_color=Colors.BLUE_50,
                    )
                )
            self.suggestions_container.visible = True
        else:
            self.suggestions_container.visible = False
        self.suggestions_container.update()

    def select_suggestion(self, e):
        bank_data = e.control.data
        self.name_field.value = f"{bank_data.name}銀行"
        self.code_field.value = bank_data.code
        self.name_field.update()
        self.code_field.update()
        self.suggestions_container.visible = False
        self.suggestions_container.update()
        self.save_button.focus()

    def on_name_blur(self, e):
        val = self.name_field.value
        if val:
            bank = self.find_zengin_bank(name=val)
            if bank:
                self.code_field.value = bank.code
                self.code_field.update()
                self.suggestions_container.visible = False
                self.suggestions_container.update()

    def on_code_blur(self, e):
        val = self.code_field.value
        if val and len(val) == 4:
            bank = self.find_zengin_bank(code=val)
            if bank:
                self.name_field.value = f"{bank.name}銀行"
                self.name_field.update()

    def save_master(self, e):
        bank_name = self.name_field.value
        bank_code = self.code_field.value

        if not bank_name or not bank_code:
            self.page.open(SnackBar(Text("銀行名と銀行コードは必須です。"), bgcolor=Colors.RED_500))
            self.page.update()
            return

        with Session(bind=Engine) as db:
            new_bank = add_or_update_bank_master(db, self.current_editing_bank_id, bank_name, bank_code)

        if new_bank:
            self.on_success(new_bank)
            self.close_dialog()
            self.page.open(SnackBar(Text("銀行情報が正常に保存されました。"), bgcolor=Colors.GREEN_500))
        else:
            self.page.open(SnackBar(Text("銀行情報の保存に失敗しました。"), bgcolor=Colors.RED_500))
        self.page.update()


# ---------------------------------------------
# 支店マスタ編集/新規登録用ダイアログクラス
# ---------------------------------------------
class BranchMasterEditDialog(AlertDialog):
    def __init__(self, page: Page, on_success: callable):
        super().__init__()
        self.page = page
        self.on_success = on_success
        self.parent_bank_id = None
        self.parent_bank_code = None 

        self.name_field = TextField(label="支店名", width=250)
        
        self.code_field = TextField(
            label="支店コード", 
            width=150,
            on_blur=self.on_code_blur 
        )
        
        self.save_button = ElevatedButton("保存", on_click=self.save_branch)

        self.title = Text("支店マスタの登録")
        self.content = Column(
            [self.name_field, self.code_field],
            tight=True,
            spacing=10,
        )
        self.actions = [
            TextButton("キャンセル", on_click=self.close_dialog),
            self.save_button,
        ]
        self.modal = True

    def show(self, bank_id: int):
        self.parent_bank_id = bank_id
        
        self.parent_bank_code = None
        with Session(bind=Engine) as db:
            bank = get_bank_master_by_id(db, bank_id)
            if bank:
                self.parent_bank_code = bank.bank_code

        self.name_field.value = ""
        self.code_field.value = ""
        self.page.open(self)
        self.page.update()
        self.name_field.focus()

    def close_dialog(self, e=None):
        self.page.close(self)
        self.page.update()

    def on_code_blur(self, e):
        """支店コード入力後に自動で支店名を検索する"""
        val = self.code_field.value.strip()
        
        if not val or not self.parent_bank_code:
            return

        # zengin_code ライブラリを使って検索
        if self.parent_bank_code in Bank.all:
            bank = Bank.all[self.parent_bank_code]
            if val in bank.branches:
                # 支店が見つかった場合、名前をセット
                branch = bank.branches[val]
                self.name_field.value = branch.name
                self.name_field.update()

    def save_branch(self, e):
        name = self.name_field.value
        code = self.code_field.value

        if not name or not code:
            self.page.open(SnackBar(Text("支店名とコードは必須です。"), bgcolor=Colors.RED_500))
            self.page.update()
            return

        with Session(bind=Engine) as db:
            from services.db_setup import BranchMaster
            try:
                # 重複チェック
                existing = (
                    db.query(BranchMaster)
                    .filter(BranchMaster.bank_id == self.parent_bank_id, BranchMaster.branch_code == code)
                    .first()
                )
                if existing:
                    self.page.open(SnackBar(Text("この支店コードは既に登録されています。"), bgcolor=Colors.RED_500))
                    self.page.update()
                    return

                new_branch = BranchMaster(bank_id=self.parent_bank_id, branch_name=name, branch_code=code)
                db.add(new_branch)
                db.commit()
                db.refresh(new_branch)
                
                self.on_success(new_branch)
                self.close_dialog()
                self.page.open(SnackBar(Text("支店を登録しました。"), bgcolor=Colors.GREEN_500))
                
            except Exception as ex:
                db.rollback()
                self.page.open(SnackBar(Text(f"保存エラーが発生しました: {ex}"), bgcolor=Colors.RED_500))
                self.page.update()


# ---------------------------------------------
# 口座種類マスタ編集/新規登録用ダイアログクラス (新規追加)
# ---------------------------------------------
class AccountTypeMasterEditDialog(AlertDialog):
    def __init__(self, page: Page, on_success: callable):
        super().__init__()
        self.page = page
        self.on_success = on_success

        self.name_field = TextField(label="口座種類名", width=250, hint_text="例: 当座預金、貯蓄預金")
        
        self.save_button = ElevatedButton("保存", on_click=self.save_account_type)

        self.title = Text("口座種類の登録")
        self.content = Column(
            [self.name_field],
            tight=True,
            spacing=10,
        )
        self.actions = [
            TextButton("キャンセル", on_click=self.close_dialog),
            self.save_button,
        ]
        self.modal = True

    def show(self):
        self.name_field.value = ""
        self.page.open(self)
        self.page.update()
        self.name_field.focus()

    def close_dialog(self, e=None):
        self.page.close(self)
        self.page.update()

    def save_account_type(self, e):
        name = self.name_field.value.strip()

        if not name:
            self.page.open(SnackBar(Text("口座種類名は必須です。"), bgcolor=Colors.RED_500))
            self.page.update()
            return

        with Session(bind=Engine) as db:
            new_type = add_account_type_master(db, name)
            
            if new_type:
                self.on_success(new_type)
                self.close_dialog()
                self.page.open(SnackBar(Text("口座種類を登録しました。"), bgcolor=Colors.GREEN_500))
            else:
                self.page.open(SnackBar(Text("保存エラーまたは重複しています。"), bgcolor=Colors.RED_500))
        self.page.update()


# ---------------------------------------------
# メイン画面クラス (BankEditView)
# ---------------------------------------------
class BankEditView(Column):
    """銀行口座登録・編集画面"""

    def __init__(self, page: Page, case_id: int):
        super().__init__(
            expand=True,
            scroll="auto",
            spacing=20,
        )
        self.page = page
        self.case_id = case_id
        self.editing_asset_id = None

        # --- UIコンポーネント定義 (インスタンス変数として保持) ---
        self.bank_name_field = Dropdown(
            label="銀行名 *",
            width=250,
            color=Colors.BLACK,
            label_style=TextStyle(color=Colors.BLACK),
            on_change=self.on_bank_change
        )

        self.branch_name_field = Dropdown(
            label="支店名",
            width=250,
            color=Colors.BLACK,
            label_style=TextStyle(color=Colors.BLACK),
            on_change=self.on_branch_change
        )

        self.account_type_field = Dropdown(
            label="口座種類",
            width=150,
            color=Colors.BLACK,
            label_style=TextStyle(color=Colors.BLACK),
            on_change=self.on_account_type_change # 💡 ハンドラ追加
        )

        self.bank_code_field = TextField(
            label="銀行コード",
            width=100,
            color=Colors.BLACK,
            label_style=TextStyle(color=Colors.BLACK),
            on_blur=self.on_bank_code_blur
        )
        self.branch_code_field = TextField(
            label="支店コード",
            width=100,
            color=Colors.BLACK,
            label_style=TextStyle(color=Colors.BLACK),
            on_blur=self.on_branch_code_blur
        )

        self.account_number_field = TextField(
            label="口座番号 *",
            width=250,
            color=Colors.BLACK,
            label_style=TextStyle(color=Colors.BLACK),
        )
        self.balance_field = TextField(
            label="残高 (調査時点)",
            width=250,
            color=Colors.BLACK,
            label_style=TextStyle(color=Colors.BLACK),
        )
        self.status_field = TextField(
            label="ステータス",
            value="調査中",
            width=250,
            color=Colors.BLACK,
            label_style=TextStyle(color=Colors.BLACK),
        )

        self.main_action_button = ElevatedButton(
            "新規口座を登録", 
            icon=Icons.ADD_CARD, 
            bgcolor=Colors.BLUE_600, 
            color=Colors.WHITE,
            on_click=self.save_asset
        )

        self.cancel_edit_button = ElevatedButton(
            "キャンセル",
            icon=Icons.CANCEL,
            visible=False,
            bgcolor=Colors.GREY_600,
            color=Colors.WHITE,
            on_click=self.reset_form
        )

        self.assets_list_view = ListView(spacing=10, expand=True)

        # --- ダイアログの初期化 ---
        self.bank_master_dialog = BankMasterEditDialog(page, self.on_bank_master_saved)
        self.branch_master_dialog = BranchMasterEditDialog(page, self.on_branch_master_saved)
        self.account_type_dialog = AccountTypeMasterEditDialog(page, self.on_account_type_saved) # 💡 ダイアログ追加

        # --- レイアウト構築 ---
        self.controls = [
            Text("🏦 銀行口座登録", size=24, weight=FontWeight.BOLD),
            Divider(),
            Container(
                content=Column(
                    [
                        Text("口座情報入力", weight=FontWeight.W_600, color=Colors.BLACK),
                        Row([self.bank_name_field, self.bank_code_field]),
                        Row([self.branch_name_field, self.branch_code_field]),
                        Row(
                            [self.account_number_field, self.account_type_field, self.balance_field, self.status_field]
                        ),
                        Row(
                            [self.cancel_edit_button, self.main_action_button],
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
                content=self.assets_list_view,
                padding=10,
                height=300,
                border_radius=5,
                bgcolor=Colors.WHITE,
            ),
        ]

        # 初期ロード
        self.load_bank_options()
        self.load_account_type_options()
        self.update_assets_list()

    # --- イベントハンドラ & ロジック ---

    def load_bank_options(self):
        """銀行マスタをロードしてドロップダウンを更新"""
        with Session(bind=Engine) as db:
            banks = get_bank_masters(db)
            options = [
                dropdown.Option("def", text="選択してください"),
                dropdown.Option("add_new_bank", text="[ ➕ 新しい銀行を登録 ]"),
            ]
            for bank in banks:
                is_security = (bank.bank_code in SECURITIES_MASTER) or ("証券" in bank.bank_name)
                if not is_security:
                    options.append(dropdown.Option(str(bank.id), text=f"{bank.bank_name} ({bank.bank_code})"))
            self.bank_name_field.options = options

    def load_account_type_options(self):
        """口座種類マスタをロード"""
        with Session(bind=Engine) as db:
            types = get_account_type_masters(db)
            options = [
                dropdown.Option("def", text="選択してください"),
                dropdown.Option("add_new_type", text="[ ➕ 新しい口座種類を登録 ]"), # 💡 追加
            ]
            for t in types:
                options.append(dropdown.Option(str(t.id), text=t.type_name))
            
            self.account_type_field.options = options

    def on_bank_change(self, e):
        """銀行選択時の処理"""
        val = self.bank_name_field.value
        if val == "add_new_bank":
            self.bank_name_field.value = "def" # 選択状態をリセット
            self.bank_master_dialog.show(None)
            self.bank_name_field.update()
            return

        if val and val != "def":
            try:
                bank_id = int(val)
                with Session(bind=Engine) as db:
                    bank = get_bank_master_by_id(db, bank_id)
                    if bank:
                        self.bank_code_field.value = bank.bank_code
                        self.load_branch_options(bank_id)
                        self.bank_code_field.update()
                        self.page.update()
            except ValueError:
                pass
        else:
            self.reset_branch_fields()
            self.page.update()

    def reset_branch_fields(self):
        self.bank_code_field.value = ""
        self.branch_name_field.options = []
        self.branch_name_field.value = "def"
        self.branch_code_field.value = ""

    def load_branch_options(self, bank_id: int):
        """支店マスタをロード"""
        self.branch_name_field.value = "def"
        self.branch_code_field.value = ""
        with Session(bind=Engine) as db:
            branches = get_branch_masters_by_bank_id(db, bank_id)
            options = [
                dropdown.Option("def", text="選択してください"),
                dropdown.Option("add_new_branch", text="[ ➕ 新しい支店を登録 ]"),
            ]
            options.extend([
                dropdown.Option(str(b.id), text=f"{b.branch_name} ({b.branch_code})")
                for b in branches
            ])
            self.branch_name_field.options = options

    def on_branch_change(self, e):
        """支店選択時の処理"""
        val = self.branch_name_field.value
        if val == "add_new_branch":
            if not self.bank_name_field.value or self.bank_name_field.value == "def":
                self.page.open(SnackBar(Text("先に銀行を選択してください"), bgcolor=Colors.RED_500))
                self.branch_name_field.value = "def"
                self.page.update()
                return
            
            self.branch_master_dialog.show(int(self.bank_name_field.value))
            self.branch_name_field.value = "def" # 一旦戻す
            return

        if val and val != "def":
            try:
                branch_id = int(val)
                with Session(bind=Engine) as db:
                    from services.db_setup import BranchMaster
                    branch = db.query(BranchMaster).filter(BranchMaster.id == branch_id).first()
                    if branch:
                        self.branch_code_field.value = branch.branch_code
                        self.branch_code_field.update()
            except ValueError:
                pass
        else:
            self.branch_code_field.value = ""
            self.branch_code_field.update()

    def on_account_type_change(self, e):
        """口座種類選択時の処理（新規追加）"""
        val = self.account_type_field.value
        if val == "add_new_type":
            self.account_type_field.value = "def"
            self.account_type_dialog.show()
            self.account_type_field.update()

    def on_bank_master_saved(self, new_bank):
        """銀行マスタ保存後のコールバック"""
        self.load_bank_options()
        self.bank_name_field.value = str(new_bank.id)
        self.bank_code_field.value = new_bank.bank_code
        self.load_branch_options(new_bank.id)
        self.page.update()

    def on_branch_master_saved(self, new_branch):
        """支店マスタ保存後のコールバック"""
        self.load_branch_options(new_branch.bank_id)
        self.branch_name_field.value = str(new_branch.id)
        self.branch_code_field.value = new_branch.branch_code
        self.page.update()

    def on_account_type_saved(self, new_type):
        """口座種類マスタ保存後のコールバック"""
        self.load_account_type_options()
        self.account_type_field.value = str(new_type.id)
        self.page.update()

    # --- 自動補完ロジック ---
    def on_bank_code_blur(self, e):
        code = self.bank_code_field.value.strip()
        if len(code) == 4 and code in Bank.all:
            bank = Bank.all[code]
            # マスタに存在するか確認
            with Session(bind=Engine) as db:
                from services.db_setup import BankMaster
                existing = db.query(BankMaster).filter(BankMaster.bank_code == code).first()
                if existing:
                    self.bank_name_field.value = str(existing.id)
                    self.load_branch_options(existing.id)
                    self.page.update()
                else:
                    self.bank_code_field.error_text = "マスタ未登録のコードです"
                    self.bank_code_field.update()

    def on_branch_code_blur(self, e):
        """支店コードから支店名を検索して設定する"""
        branch_code = self.branch_code_field.value.strip()
        bank_id_str = self.bank_name_field.value

        # バリデーション: 支店コードがあり、かつ銀行が選択されていること
        if not branch_code or not bank_id_str or bank_id_str in ["def", "add_new_bank"]:
            return

        try:
            bank_id = int(bank_id_str)
            with Session(bind=Engine) as db:
                from services.db_setup import BranchMaster
                # 銀行IDと支店コードで検索
                branch = db.query(BranchMaster).filter(
                    BranchMaster.bank_id == bank_id, 
                    BranchMaster.branch_code == branch_code
                ).first()

                if branch:
                    self.branch_name_field.value = str(branch.id)
                    self.branch_code_field.error_text = None
                else:
                    # 見つからない場合
                    self.branch_code_field.error_text = "マスタ未登録"
                
                self.branch_name_field.update()
                self.branch_code_field.update()
        except ValueError:
            pass

    # --- CRUD操作 ---
    def save_asset(self, e):
        try:
            bank_id_str = self.bank_name_field.value
            if not bank_id_str or bank_id_str in ["def", "add_new_bank"]:
                raise ValueError("銀行を選択してください。")

            bank_id = int(bank_id_str)
            
            branch_id = None
            if self.branch_name_field.value and self.branch_name_field.value not in ["def", "add_new_branch"]:
                branch_id = int(self.branch_name_field.value)

            account_type_id = None
            if self.account_type_field.value and self.account_type_field.value not in ["def", "add_new_type"]:
                account_type_id = int(self.account_type_field.value)

            balance_val = float(self.balance_field.value.replace(",", "")) if self.balance_field.value else 0.0

            if self.editing_asset_id:
                success = update_financial_asset(
                    self.editing_asset_id,
                    bank_id, branch_id, account_type_id,
                    self.account_number_field.value,
                    balance_val,
                    self.status_field.value
                )
                msg = "口座情報を修正しました。"
            else:
                success = add_financial_asset(
                    self.case_id,
                    bank_id, branch_id, account_type_id,
                    self.account_number_field.value,
                    balance_val,
                    self.status_field.value
                )
                msg = "口座を登録しました。"

            if success:
                self.page.open(SnackBar(Text(msg, color=Colors.WHITE), bgcolor=Colors.GREEN_700))
                self.reset_form(None)
                self.update_assets_list()
            else:
                raise Exception("DB Error")

        except Exception as ex:
            self.page.open(SnackBar(Text(f"エラー: {ex}", color=Colors.WHITE), bgcolor=Colors.RED_700))
        self.page.update()

    def delete_asset(self, e):
        asset_id = e.control.data
        if delete_financial_asset(asset_id):
            self.page.open(SnackBar(Text("削除しました。"), bgcolor=Colors.RED_700))
            self.update_assets_list()
        self.page.update()

    def start_edit(self, e):
        asset_id = e.control.data
        assets = get_financial_asset_by_case(self.case_id)
        target = next((a for a in assets if a["id"] == asset_id), None)

        if target:
            self.editing_asset_id = asset_id
            self.bank_name_field.value = str(target["bank_id"]) if target.get("bank_id") else "def"
            
            # 連動して支店ロード
            if target.get("bank_id"):
                self.load_branch_options(target["bank_id"])
            
            self.branch_name_field.value = str(target["branch_id"]) if target.get("branch_id") else "def"
            self.account_type_field.value = str(target["account_type_id"]) if target.get("account_type_id") else "def"
            
            self.bank_code_field.value = target.get("bank_code", "")
            self.branch_code_field.value = target.get("branch_code", "")
            self.account_number_field.value = target["account_number"]
            self.balance_field.value = f"{target['balance']:,.0f}" if target["balance"] else ""
            self.status_field.value = target["status"]

            self.main_action_button.text = "口座情報を修正"
            self.main_action_button.icon = Icons.SAVE
            self.cancel_edit_button.visible = True
            self.page.update()

    def reset_form(self, e=None):
        self.editing_asset_id = None
        self.bank_name_field.value = "def"
        self.branch_name_field.value = "def"
        self.branch_name_field.options = [] # クリア
        self.account_type_field.value = "def"
        
        self.bank_code_field.value = ""
        self.branch_code_field.value = ""
        self.account_number_field.value = ""
        self.balance_field.value = ""
        self.status_field.value = "調査中"

        self.main_action_button.text = "新規口座を登録"
        self.main_action_button.icon = Icons.ADD_CARD
        self.cancel_edit_button.visible = False
        self.page.update()

    def update_assets_list(self):
        assets = get_financial_asset_by_case(self.case_id)
        self.assets_list_view.controls.clear()

        if not assets:
            self.assets_list_view.controls.append(Text("登録された口座はありません。", color=Colors.GREY_600))
        else:
            for asset in assets:
                # 証券会社は除外する（銀行編集画面なので）
                is_security = (asset.get("bank_code") in SECURITIES_MASTER) or ("証券" in asset.get("bank_name", ""))
                if is_security:
                    continue

                info_text = f"🏦 {asset['bank_name']} ({asset.get('branch_name', '-')}) - {asset['account_number']}"
                self.assets_list_view.controls.append(
                    Row(
                        [
                            Text(info_text, width=400, color=Colors.BLACK87),
                            Text(f"¥{asset['balance']:,.0f}", width=100, text_align="right", color=Colors.BLACK87),
                            IconButton(Icons.EDIT, icon_color=Colors.BLUE_400, data=asset["id"], on_click=self.start_edit),
                            IconButton(Icons.DELETE, icon_color=Colors.RED_400, data=asset["id"], on_click=self.delete_asset),
                        ]
                    )
                )
        self.page.update()