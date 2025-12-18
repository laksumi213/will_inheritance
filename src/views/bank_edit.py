# src/views/bank_edit.py
import threading
import os
import unicodedata
from typing import Optional, List, Dict, Any

from flet import (
    ButtonStyle, Card, Colors, Column, Container, DataCell, DataColumn, DataRow, DataTable,
    Divider, Dropdown, ElevatedButton, FilePicker, FilePickerResultEvent, FontWeight, Icon, Icons,
    Image, MainAxisAlignment, Page, Row, ScrollMode, SnackBar, Stack, Text, TextField,
    border, dropdown, IconButton, CrossAxisAlignment, alignment, TextStyle,
    GestureDetector, DragStartEvent, DragUpdateEvent, Slider,
    AlertDialog, TextButton, ListView, ListTile
)
from zengin_code import Bank

# サービス層
from src.services.deceased_service import (
    get_case_folder_path,
    move_and_rename_bank_pdf,
    update_financial_asset_status_fuzzy,
    get_bank_masters,
    get_branch_masters_by_bank_id,
    get_account_type_masters,
    get_financial_asset_by_case_and_type,
    add_financial_asset,
    update_financial_asset,
    delete_financial_asset,
    get_bank_master_by_id,
    add_or_update_bank_master,
    add_branch_master,
    add_account_type_master,
    update_branch_code
)
from src.services.securities_data import SECURITIES_MASTER
from src.services.pdf_service import pdf_service
from src.services.ai_service import ai_service
from src.utils.image_utils import apply_masking_to_image
from src.models.database import SessionLocal
from src.models.tables import BankMaster, BranchMaster, AccountTypeMaster

# --- ヘルパー関数 ---
def normalize_str(s: str) -> str:
    """全角英数字を半角に、半角カナを全角に正規化し、空白を除去する"""
    if not s:
        return ""
    return unicodedata.normalize("NFKC", s).replace(" ", "").replace("　", "").strip()

# ---------------------------------------------
# 銀行マスタ編集/新規登録用ダイアログ (サジェスト機能付き)
# ---------------------------------------------
class BankMasterEditDialog(AlertDialog):
    def __init__(self, page: Page, on_success: callable):
        super().__init__()
        self.page = page
        self.on_success = on_success
        self.current_editing_id = None

        self.name_field = TextField(
            label="銀行名", 
            width=300, 
            autofocus=True, 
            on_change=self.on_name_change # インクリメンタルサーチ
        )
        self.code_field = TextField(label="金融機関コード", width=150)
        
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
        
        self.title = Text("銀行マスタの登録")
        self.content = Column([self.name_field, self.suggestions_container, self.code_field], tight=True, spacing=5)
        self.actions = [TextButton("キャンセル", on_click=self.close_dialog), self.save_button]
        self.modal = True

    def show(self):
        self.name_field.value = ""
        self.code_field.value = ""
        self.suggestions_container.visible = False
        self.page.open(self)
        self.page.update()

    def close_dialog(self, e=None):
        self.page.close(self)
        self.page.update()

    def on_name_change(self, e):
        """銀行名の入力変更時に検索"""
        val = self.name_field.value
        if not val:
            self.suggestions_container.visible = False
            self.suggestions_container.update()
            return

        search_term = normalize_str(val)
        matches = []
        
        # zengin_codeから検索 (最大10件まで表示)
        count = 0
        for bank in Bank.all.values():
            if count >= 10: break
            
            b_name = normalize_str(bank.name)
            b_kana = normalize_str(bank.kana)
            
            if search_term in b_name or search_term in b_kana:
                matches.append(bank)
                count += 1

        if matches:
            self.suggestions_list.controls.clear()
            for bank in matches:
                self.suggestions_list.controls.append(
                    ListTile(
                        title=Text(f"{bank.name}", size=14, color=Colors.BLACK87),
                        subtitle=Text(f"{bank.kana} ({bank.code})", size=11, color=Colors.GREY),
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
        """サジェスト選択時の処理"""
        bank = e.control.data
        self.name_field.value = bank.name
        self.code_field.value = bank.code
        self.name_field.update()
        self.code_field.update()
        
        self.suggestions_container.visible = False
        self.suggestions_container.update()
        self.code_field.focus()

    def save_master(self, e):
        name = self.name_field.value.strip()
        code = self.code_field.value.strip()
        if not name or not code:
            self.page.open(SnackBar(Text("名称とコードは必須です"), bgcolor=Colors.RED))
            self.page.update()
            return

        # 登録処理
        new_master = add_or_update_bank_master(None, name, code)
        if new_master:
            self.on_success(new_master)
            self.close_dialog()
            self.page.open(SnackBar(Text("銀行を登録しました"), bgcolor=Colors.GREEN))
        else:
            self.page.open(SnackBar(Text("保存に失敗しました"), bgcolor=Colors.RED))
        self.page.update()

# ---------------------------------------------
# 支店マスタ編集/新規登録用ダイアログ (サジェスト機能付き)
# ---------------------------------------------
class BranchMasterEditDialog(AlertDialog):
    def __init__(self, page: Page, on_success: callable):
        super().__init__()
        self.page = page
        self.on_success = on_success
        self.parent_bank_id = None

        self.name_field = TextField(
            label="支店名", 
            width=250, 
            autofocus=True,
            on_change=self.on_name_change # インクリメンタルサーチ
        )
        self.code_field = TextField(label="支店コード", width=150)
        
        # サジェストリスト
        self.suggestions_list = ListView(height=150, spacing=0)
        self.suggestions_container = Container(
            content=self.suggestions_list,
            visible=False,
            bgcolor=Colors.WHITE,
            border=border.all(1, Colors.GREY_300),
            border_radius=5,
            padding=0,
            width=250,
        )

        self.save_button = ElevatedButton("保存", on_click=self.save_branch)

        self.title = Text("支店マスタの登録")
        self.content = Column([self.name_field, self.suggestions_container, self.code_field], tight=True, spacing=5)
        self.actions = [TextButton("キャンセル", on_click=self.close_dialog), self.save_button]
        self.modal = True

    def show(self, bank_id: int):
        self.parent_bank_id = bank_id
        self.name_field.value = ""
        self.code_field.value = ""
        self.suggestions_container.visible = False
        self.page.open(self)
        self.page.update()

    def close_dialog(self, e=None):
        self.page.close(self)
        self.page.update()

    def on_name_change(self, e):
        """支店名の入力変更時に検索"""
        val = self.name_field.value
        if not val or not self.parent_bank_id:
            self.suggestions_container.visible = False
            self.suggestions_container.update()
            return

        # 親銀行のコードを取得
        db = SessionLocal()
        parent_bank = db.query(BankMaster).get(self.parent_bank_id)
        db.close()

        if not parent_bank: return

        matches = []
        search_term = normalize_str(val)

        try:
            zengin_bank = Bank.all.get(parent_bank.bank_code)
            if zengin_bank:
                count = 0
                for branch in zengin_bank.branches.values():
                    if count >= 10: break
                    
                    b_name = normalize_str(branch.name)
                    b_kana = normalize_str(branch.kana)
                    
                    if search_term in b_name or search_term in b_kana:
                        matches.append(branch)
                        count += 1
        except Exception:
            pass

        if matches:
            self.suggestions_list.controls.clear()
            for branch in matches:
                self.suggestions_list.controls.append(
                    ListTile(
                        title=Text(f"{branch.name}", size=14, color=Colors.BLACK87),
                        subtitle=Text(f"{branch.kana} ({branch.code})", size=11, color=Colors.GREY),
                        data=branch,
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
        """サジェスト選択時の処理"""
        branch = e.control.data
        self.name_field.value = branch.name
        self.code_field.value = branch.code
        self.name_field.update()
        self.code_field.update()
        
        self.suggestions_container.visible = False
        self.suggestions_container.update()
        self.code_field.focus()

    def save_branch(self, e):
        name = self.name_field.value.strip()
        code = self.code_field.value.strip()
        if not name or not code:
            self.page.open(SnackBar(Text("支店名とコードは必須です"), bgcolor=Colors.RED))
            self.page.update()
            return

        try:
            new_branch = add_branch_master(self.parent_bank_id, name, code)
            if new_branch:
                self.on_success(new_branch)
                self.close_dialog()
                self.page.open(SnackBar(Text("支店を登録しました"), bgcolor=Colors.GREEN))
        except Exception as ex:
            self.page.open(SnackBar(Text(f"エラー: {ex}"), bgcolor=Colors.RED))
        self.page.update()

# ---------------------------------------------
# 口座種類マスタ編集/新規登録用ダイアログ
# ---------------------------------------------
class AccountTypeMasterEditDialog(AlertDialog):
    def __init__(self, page: Page, on_success: callable):
        super().__init__()
        self.page = page
        self.on_success = on_success

        self.name_field = TextField(label="口座種類名", width=250, autofocus=True)
        self.save_button = ElevatedButton("保存", on_click=self.save_type)

        self.title = Text("口座種類の登録")
        self.content = Column([self.name_field], tight=True)
        self.actions = [TextButton("キャンセル", on_click=self.close_dialog), self.save_button]
        self.modal = True

    def show(self):
        self.name_field.value = ""
        self.page.open(self)
        self.page.update()

    def close_dialog(self, e=None):
        self.page.close(self)
        self.page.update()

    def save_type(self, e):
        name = self.name_field.value.strip()
        if not name:
            return
        
        new_type = add_account_type_master(type_name=name)
        if new_type:
            self.on_success(new_type)
            self.close_dialog()
            self.page.open(SnackBar(Text("口座種類を登録しました"), bgcolor=Colors.GREEN))
        else:
            self.page.open(SnackBar(Text("保存に失敗しました（重複など）"), bgcolor=Colors.RED))
        self.page.update()


# ---------------------------------------------
# メイン画面クラス (BankEditView)
# ---------------------------------------------
class BankEditView(Column):
    """
    銀行書類登録画面: AI解析(マスキング・ズーム付)、自動ファイル整理、手動登録・編集
    """

    def __init__(self, page: Page, case_id: int):
        super().__init__(expand=True, scroll="auto", spacing=20)
        self.page = page
        self.case_id = case_id
        self._current_source_pdf: Optional[str] = None
        self.editing_asset_id: Optional[int] = None

        # --- 画像操作・AI解析用ステート ---
        self.nayose_image_base64: Optional[str] = None
        self.nayose_img_width: int = 0
        self.nayose_img_height: int = 0
        self.current_display_width: float = 800.0
        self.mask_rects: List[tuple] = []
        self.current_mask: Optional[Container] = None
        self.drag_start_x: float = 0
        self.drag_start_y: float = 0
        
        # ページ管理用
        self.page_images = []
        self.current_page_index = 0

        # --- ファイルピッカー ---
        self.file_picker = FilePicker(on_result=self._on_pdf_picked)
        self.page.overlay.append(self.file_picker)
        
        # --- UIコンポーネント: 画像表示エリア ---
        self.masking_stack = Stack()
        self.masking_container = Container(
            content=self.masking_stack,
            visible=False,
            border=border.all(1, "outlineVariant"),
            border_radius=8,
            bgcolor="surfaceVariant",
            alignment=alignment.top_left
        )

        self.zoom_slider = Slider(
            min=600, max=1600, 
            value=self.current_display_width, 
            label="表示サイズ: {value}px", 
            width=300, 
            on_change=self._on_zoom_change, 
            disabled=True
        )
        
        self.analyze_btn = ElevatedButton(
            "AI解析してファイルを自動整理", 
            icon=Icons.AUTO_FIX_HIGH, 
            on_click=self._run_ai_analysis,
            bgcolor="primary", color="onPrimary", visible=False
        )
        
        # ページ送りボタン
        self.btn_prev = IconButton(icon=Icons.ARROW_BACK, on_click=self.on_prev_page, disabled=True, tooltip="前のページ")
        self.btn_next = IconButton(icon=Icons.ARROW_FORWARD, on_click=self.on_next_page, disabled=True, tooltip="次のページ")
        self.txt_page_indicator = Text("0 / 0", size=16, weight=FontWeight.BOLD)

        self.ai_results_table = DataTable(
            columns=[
                DataColumn(Text("金融機関")),
                DataColumn(Text("種類")),
                DataColumn(Text("口座番号")),
                DataColumn(Text("操作")),
            ],
            rows=[], visible=False
        )

        # --- 手動入力フォーム用コンポーネント ---
        # 銀行名
        self.bank_name_field = Dropdown(
            label="銀行名 *", width=250, 
            on_change=self._on_bank_change
        )
        self.bank_code_field = TextField(label="金融機関コード", width=120, read_only=True)
        
        # 支店名
        self.branch_name_field = Dropdown(
            label="支店名", width=250, 
            on_change=self._on_branch_change
        )
        self.branch_code_field = TextField(label="店番", width=100)
        
        # 口座種類
        self.account_type_field = Dropdown(
            label="口座種類", width=150,
            on_change=self._on_account_type_change
        )
        
        self.account_number_field = TextField(label="口座番号 *", width=200)
        self.balance_field = TextField(label="残高/評価額", width=200)
        self.status_field = TextField(label="ステータス", value="調査中", width=200)

        self.save_btn = ElevatedButton("口座を登録", icon=Icons.ADD_CARD, bgcolor="primary", color="onPrimary", on_click=self._on_save_click)
        self.cancel_btn = ElevatedButton("キャンセル", icon=Icons.CANCEL, bgcolor="grey", color="white", visible=False, on_click=self._reset_form)

        # --- 登録済みリスト ---
        self.assets_list_view = Column(spacing=10)

        # --- ダイアログ ---
        self.bank_master_dialog = BankMasterEditDialog(page, self.on_bank_master_saved)
        self.branch_master_dialog = BranchMasterEditDialog(page, self.on_branch_master_saved)
        self.account_type_dialog = AccountTypeMasterEditDialog(page, self.on_account_type_saved)

        # 画面構築
        self.controls = [
            Text("🏦 銀行口座登録・管理", size=24, weight=FontWeight.BOLD, color="onSurface"),
            Divider(),
            
            # 1. AI解析セクション
            Card(
                content=Container(
                    padding=20,
                    content=Column([
                        Row([Icon(Icons.AUTO_AWESOME, color="primary"), Text("書類から自動読み取り・フォルダ整理", weight=FontWeight.BOLD)]),
                        Text("PDFを選択 -> 必要に応じてズーム・黒塗り(ドラッグ) -> AI解析ボタンを押してください", size=12, color="secondary"),
                        Row([
                            ElevatedButton("PDFファイルを選択", icon=Icons.UPLOAD_FILE, on_click=self._open_pdf_picker),
                            Container(width=10),
                            self.btn_prev,
                            self.txt_page_indicator,
                            self.btn_next,
                            Container(width=20),
                            Text("表示サイズ:"),
                            self.zoom_slider,
                            self.analyze_btn,
                        ], vertical_alignment=CrossAxisAlignment.CENTER),
                        
                        Row([self.masking_container], scroll=ScrollMode.AUTO),
                        
                        self.ai_results_table,
                    ], spacing=15)
                )
            ),
            
            Divider(height=30, color="transparent"),

            # 2. 入力フォームセクション
            Card(
                content=Container(
                    padding=20,
                    content=Column([
                        Row([Icon(Icons.EDIT, color="secondary"), Text("口座情報の入力・編集", weight=FontWeight.BOLD, color="secondary")]),
                        Row([self.bank_name_field, self.bank_code_field]),
                        Row([self.branch_name_field, self.branch_code_field]),
                        Row([self.account_type_field, self.account_number_field]),
                        Row([self.balance_field, self.status_field]),
                        Row([self.cancel_btn, self.save_btn], alignment=MainAxisAlignment.END)
                    ], spacing=15)
                )
            ),

            Divider(),
            
            # 3. 登録済みリストセクション
            Text("登録済み銀行口座一覧", size=18, weight=FontWeight.BOLD),
            Container(
                content=self.assets_list_view,
                padding=10,
                border=border.all(1, "outlineVariant"),
                border_radius=8,
                bgcolor="surface"
            )
        ]

    def did_mount(self):
        """画面表示時の初期データロード"""
        self._load_masters()
        self._update_assets_list()

    def _load_masters(self):
        """マスタデータのロード (証券会社を除外)"""
        # 銀行マスタ
        all_banks = get_bank_masters()
        options = [dropdown.Option("def", "選択してください"), dropdown.Option("add_new", "[ ➕ 新しい銀行を登録 ]")]
        
        for b in all_banks:
            # 証券会社を除外するロジック
            # 1. 証券コードリストに含まれる
            # 2. 名称に「証券」が含まれる
            is_security = (b.bank_code in SECURITIES_MASTER) or ("証券" in b.bank_name)
            
            if not is_security:
                options.append(dropdown.Option(str(b.id), f"{b.bank_name} ({b.bank_code})"))
        
        self.bank_name_field.options = options
        self.bank_name_field.value = "def"

        # 口座種類マスタ
        types = get_account_type_masters()
        t_options = [dropdown.Option("def", "選択してください"), dropdown.Option("add_new_type", "[ ➕ 新しい種類を登録 ]")]
        for t in types:
            t_options.append(dropdown.Option(str(t.id), t.type_name))
        self.account_type_field.options = t_options
        self.account_type_field.value = "def"
        
        # 支店プルダウン初期化
        self.branch_name_field.options = [dropdown.Option("def", "選択してください")]
        self.branch_name_field.value = "def"
        self.branch_name_field.disabled = True
        
        self.update()

    def _on_bank_change(self, e):
        """銀行選択時の処理"""
        val = self.bank_name_field.value
        
        # 新規登録が選ばれた場合
        if val == "add_new":
            self.bank_name_field.value = "def" # 選択を戻す
            self.bank_master_dialog.show()
            self.update()
            return

        if val and val != "def":
            try:
                bank_id = int(val)
                db = SessionLocal()
                bank = db.query(BankMaster).get(bank_id)
                if bank:
                    self.bank_code_field.value = bank.bank_code
                db.close()
                
                # 支店ロード
                branches = get_branch_masters_by_bank_id(bank_id)
                options = [dropdown.Option("def", "選択してください"), dropdown.Option("add_new_branch", "[ ➕ 新しい支店を登録 ]")]
                for br in branches:
                    options.append(dropdown.Option(str(br.id), f"{br.branch_name} ({br.branch_code})"))
                self.branch_name_field.options = options
                self.branch_name_field.value = "def"
                self.branch_name_field.disabled = False
            except Exception as ex:
                print(f"Bank load error: {ex}")
        else:
            self.bank_code_field.value = ""
            self.branch_name_field.options = [dropdown.Option("def", "選択してください")]
            self.branch_name_field.value = "def"
            self.branch_name_field.disabled = True
        
        self.update()

    def _on_branch_change(self, e):
        """支店選択時の処理"""
        val = self.branch_name_field.value
        
        # 新規登録が選ばれた場合
        if val == "add_new_branch":
            bank_val = self.bank_name_field.value
            if not bank_val or bank_val == "def":
                self.page.open(SnackBar(Text("先に銀行を選択してください"), bgcolor="error"))
                self.branch_name_field.value = "def"
                self.update()
                return
            
            self.branch_name_field.value = "def" # 選択を戻す
            self.branch_master_dialog.show(int(bank_val))
            self.update()
            return
        
        # 既存支店選択時、コードをセット
        if val and val != "def":
            try:
                branch_id = int(val)
                db = SessionLocal()
                br = db.query(BranchMaster).get(branch_id)
                if br:
                    self.branch_code_field.value = br.branch_code
                db.close()
                self.update()
            except:
                pass

    def _on_account_type_change(self, e):
        """口座種類選択時の処理"""
        val = self.account_type_field.value
        if val == "add_new_type":
            self.account_type_field.value = "def"
            self.account_type_dialog.show()
            self.update()

    # --- ダイアログからのコールバック ---
    def on_bank_master_saved(self, new_master):
        self._load_masters()
        self.bank_name_field.value = str(new_master.id)
        self.bank_code_field.value = new_master.bank_code
        # 支店オプションをリセットして有効化
        self.branch_name_field.options = [dropdown.Option("def", "選択してください"), dropdown.Option("add_new_branch", "[ ➕ 新しい支店を登録 ]")]
        self.branch_name_field.disabled = False
        self.update()

    def on_branch_master_saved(self, new_branch):
        # 現在選択中の銀行IDで支店リストを再ロード
        if self.bank_name_field.value and self.bank_name_field.value != "def":
            bank_id = int(self.bank_name_field.value)
            branches = get_branch_masters_by_bank_id(bank_id)
            options = [dropdown.Option("def", "選択してください"), dropdown.Option("add_new_branch", "[ ➕ 新しい支店を登録 ]")]
            for br in branches:
                options.append(dropdown.Option(str(br.id), f"{br.branch_name} ({br.branch_code})"))
            self.branch_name_field.options = options
            
            # 新規作成した支店を選択状態に
            self.branch_name_field.value = str(new_branch.id)
            self.branch_code_field.value = new_branch.branch_code
            self.update()

    def on_account_type_saved(self, new_type):
        self._load_masters() 
        self.account_type_field.value = str(new_type.id)
        self.update()

    # --- 保存・編集・削除ロジック ---

    def _on_save_click(self, e):
        """保存ボタン"""
        try:
            # バリデーション
            if self.bank_name_field.value == "def":
                self.page.open(SnackBar(Text("銀行を選択してください"), bgcolor="error"))
                return
            if not self.account_number_field.value:
                self.page.open(SnackBar(Text("口座番号を入力してください"), bgcolor="error"))
                return

            bank_id = int(self.bank_name_field.value)
            
            branch_id = None
            if self.branch_name_field.value and self.branch_name_field.value != "def":
                branch_id = int(self.branch_name_field.value)
                
                # 支店コードの手動修正を反映
                new_code = self.branch_code_field.value.strip()
                if new_code:
                    update_branch_code(branch_id, new_code)

            account_type_id = int(self.account_type_field.value) if self.account_type_field.value != "def" else None
            
            balance = 0.0
            if self.balance_field.value:
                try:
                    balance = float(self.balance_field.value.replace(",", ""))
                except:
                    pass

            if self.editing_asset_id:
                success = update_financial_asset(
                    asset_id=self.editing_asset_id,
                    bank_id=bank_id,
                    branch_id=branch_id,
                    account_type_id=account_type_id,
                    account_number=self.account_number_field.value,
                    balance=balance,
                    status=self.status_field.value
                )
                msg = "口座情報を更新しました"
            else:
                success = add_financial_asset(
                    case_id=self.case_id,
                    bank_id=bank_id,
                    branch_id=branch_id,
                    account_type_id=account_type_id,
                    account_number=self.account_number_field.value,
                    balance=balance,
                    status=self.status_field.value
                )
                msg = "口座を登録しました"

            if success:
                self.page.open(SnackBar(Text(msg), bgcolor="green"))
                self._reset_form()
                self._update_assets_list()
            else:
                self.page.open(SnackBar(Text("保存に失敗しました"), bgcolor="error"))

        except Exception as ex:
            self.page.open(SnackBar(Text(f"エラー: {ex}"), bgcolor="error"))

    def _reset_form(self, e=None):
        """フォームのリセット"""
        self.editing_asset_id = None
        self.bank_name_field.value = "def"
        self.bank_code_field.value = ""
        self.branch_name_field.options = [dropdown.Option("def", "選択してください")]
        self.branch_name_field.value = "def"
        self.branch_name_field.disabled = True
        self.branch_code_field.value = ""
        self.account_type_field.value = "def"
        self.account_number_field.value = ""
        self.balance_field.value = ""
        self.status_field.value = "調査中"
        
        self.save_btn.text = "口座を登録"
        self.save_btn.icon = Icons.ADD_CARD
        self.cancel_btn.visible = False
        self.update()

    def _start_edit(self, e):
        """編集モード開始"""
        asset_id = e.control.data
        assets = get_financial_asset_by_case_and_type(self.case_id, "BANK")
        target = next((a for a in assets if a["id"] == asset_id), None)
        
        if target:
            self.editing_asset_id = asset_id
            self.bank_name_field.value = str(target["bank_id"])
            self._on_bank_change(None) # 支店リストロード
            
            if target.get("branch_id"):
                self.branch_name_field.value = str(target["branch_id"])
                # コードもセット
                db = SessionLocal()
                br = db.query(BranchMaster).get(target["branch_id"])
                if br: self.branch_code_field.value = br.branch_code
                db.close()
            
            if target.get("account_type_id"):
                self.account_type_field.value = str(target.get("account_type_id"))

            self.account_number_field.value = target["account_number"]
            self.balance_field.value = str(int(target["balance"])) if target["balance"] else ""
            self.status_field.value = target["status"]
            
            self.save_btn.text = "変更を保存"
            self.save_btn.icon = Icons.SAVE
            self.cancel_btn.visible = True
            
            self.update()
            self.account_number_field.focus()

    def _delete_asset(self, e):
        asset_id = e.control.data
        if delete_financial_asset(asset_id):
            self.page.open(SnackBar(Text("削除しました"), bgcolor="green"))
            self._update_assets_list()

    def _update_assets_list(self):
        """リスト更新"""
        self.assets_list_view.controls.clear()
        assets = get_financial_asset_by_case_and_type(self.case_id, "BANK")
        
        if not assets:
            self.assets_list_view.controls.append(Text("登録された口座はありません", color="grey"))
        else:
            for a in assets:
                info = f"{a['bank_name']} {a.get('branch_name', '')} : {a['account_number']}"
                bal = f"¥{a['balance']:,.0f}" if a['balance'] is not None else "-"
                
                self.assets_list_view.controls.append(
                    Container(
                        content=Row([
                            Icon(Icons.ACCOUNT_BALANCE, color="primary"),
                            Column([
                                Text(info, weight=FontWeight.BOLD),
                                Text(f"残高: {bal} | {a['status']}", size=12, color="grey")
                            ], expand=True),
                            IconButton(Icons.EDIT, icon_color="blue", data=a["id"], on_click=self._start_edit),
                            IconButton(Icons.DELETE, icon_color="red", data=a["id"], on_click=self._delete_asset)
                        ]),
                        padding=10,
                        border=border.only(bottom=border.BorderSide(1, "outlineVariant"))
                    )
                )
        self.update()

    # --- AI/ファイル操作・画像制御ロジック ---

    def _open_pdf_picker(self, e):
        """PDF選択ダイアログを開く（案件フォルダを初期表示）"""
        init_path = get_case_folder_path(self.case_id)
        self.file_picker.pick_files(
            allow_multiple=False, 
            allowed_extensions=["pdf"], 
            initial_directory=init_path
        )

    def _on_pdf_picked(self, e: FilePickerResultEvent):
        if not e.files: return
        self._current_source_pdf = e.files[0].path
        self.page.open(SnackBar(Text("書類をプレビュー中..."), bgcolor="primary"))
        
        def process():
            try:
                # 複数ページ対応: すべてのページを変換
                images = pdf_service.convert_pdf_to_images_sync(self._current_source_pdf)
                if not images:
                    raise ValueError("画像を生成できませんでした")

                self.page_images = images
                self.current_page_index = 0
                
                self.mask_rects.clear()
                self.masking_stack.controls.clear()
                
                self._update_page_view()
                
                self.masking_container.visible = True
                self.analyze_btn.visible = True
                self.zoom_slider.disabled = False
                
                self.update()
                
            except Exception as ex:
                print(f"PDF Load Error: {ex}")
                self.page.open(SnackBar(Text(f"読込エラー: {ex}"), bgcolor="error"))
        
        threading.Thread(target=process).start()

    def _update_page_view(self):
        """現在のページインデックスに基づいて画像表示を更新"""
        if not self.page_images: return

        # ページナビゲーションボタンの状態更新
        total = len(self.page_images)
        self.btn_prev.disabled = self.current_page_index == 0
        self.btn_next.disabled = self.current_page_index == total - 1
        self.txt_page_indicator.value = f"{self.current_page_index + 1} / {total}"

        # 現在のページ画像を取得
        page_img = self.page_images[self.current_page_index]
        self.nayose_image_base64 = page_img.base64_image
        self.nayose_img_width = page_img.width
        self.nayose_img_height = page_img.height

        # 既存のマスクをクリア (ページ切り替え時)
        self.mask_rects = []
        self.masking_stack.controls.clear()

        # 画像表示
        display_w = self.current_display_width
        display_h = display_w * (self.nayose_img_height / self.nayose_img_width)
        
        img_view = Image(src_base64=self.nayose_image_base64, width=display_w, fit="contain")
        
        gesture = GestureDetector(
            content=img_view,
            on_pan_start=self._on_mask_pan_start,
            on_pan_update=self._on_mask_pan_update,
            on_pan_end=self._on_mask_pan_end,
        )
        self.masking_stack.controls.append(gesture)
        
        self.masking_container.width = display_w
        self.masking_container.height = display_h
        
        self.update()

    def on_prev_page(self, e):
        if self.current_page_index > 0:
            self.current_page_index -= 1
            self._update_page_view()

    def on_next_page(self, e):
        if self.current_page_index < len(self.page_images) - 1:
            self.current_page_index += 1
            self._update_page_view()

    def _on_zoom_change(self, e):
        if not self.nayose_image_base64: return
        
        new_w = float(e.control.value)
        ratio = new_w / self.current_display_width
        self.current_display_width = new_w
        
        new_h = new_w * (self.nayose_img_height / self.nayose_img_width)
        self.masking_container.width = new_w
        self.masking_container.height = new_h
        
        if self.masking_stack.controls:
            gesture = self.masking_stack.controls[0]
            if isinstance(gesture, GestureDetector):
                gesture.content.width = new_w
        
        new_masks = []
        for i in range(1, len(self.masking_stack.controls)):
            mask_obj = self.masking_stack.controls[i]
            mask_obj.left *= ratio
            mask_obj.top *= ratio
            mask_obj.width *= ratio
            mask_obj.height *= ratio
        
        for r in self.mask_rects:
            new_masks.append((r[0]*ratio, r[1]*ratio, r[2]*ratio, r[3]*ratio))
        self.mask_rects = new_masks
        
        self.update()

    def _on_mask_pan_start(self, e: DragStartEvent):
        self.drag_start_x, self.drag_start_y = e.local_x, e.local_y
        self.current_mask = Container(bgcolor=Colors.BLACK, opacity=0.7, left=e.local_x, top=e.local_y, width=0, height=0)
        self.masking_stack.controls.append(self.current_mask)
        self.update()

    def _on_mask_pan_update(self, e: DragUpdateEvent):
        if not self.current_mask: return
        curr_x, curr_y = e.local_x, e.local_y
        self.current_mask.left = min(self.drag_start_x, e.local_x)
        self.current_mask.top = min(self.drag_start_y, e.local_y)
        self.current_mask.width = abs(e.local_x - self.drag_start_x)
        self.current_mask.height = abs(e.local_y - self.drag_start_y)
        self.current_mask.update()

    def _on_mask_pan_end(self, e):
        if self.current_mask:
            self.mask_rects.append((self.current_mask.left, self.current_mask.top, self.current_mask.width, self.current_mask.height))
            self.current_mask = None

    def _run_ai_analysis(self, e):
        if not self._current_source_pdf: return
        self.analyze_btn.disabled = True
        self.page.open(SnackBar(Text("AI解析およびファイル整理を実行中..."), bgcolor="primary"))
        self.update()

        def execute():
            try:
                masked_b64 = apply_masking_to_image(
                    self.nayose_image_base64, self.mask_rects, self.nayose_img_width, self.nayose_img_height,
                    self.current_display_width, self.masking_container.height
                )
                results = ai_service.analyze_bank_document_sync(masked_b64)
                
                bank_name = "不明銀行"
                doc_type = "残高証明書"
                if results:
                    bank_name = results[0].get("bank_name", "銀行")
                    # 文言判定ロジック廃止に伴い、doc_typeはデフォルト設定
                    doc_type = "残高証明書"

                saved_path = move_and_rename_bank_pdf(
                    case_id=self.case_id,
                    src_path=self._current_source_pdf,
                    bank_name=bank_name,
                    doc_type=doc_type
                )

                if saved_path:
                    update_financial_asset_status_fuzzy(self.case_id, bank_name, "調査完了")
                    self._update_assets_list() 
                    self.page.open(SnackBar(
                        content=Text(f"✅ ファイルを整理しました:\n{saved_path}"),
                        bgcolor="green", duration=5000
                    ))
                else:
                    raise Exception("ファイルの移動に失敗しました。パスを確認してください。")
                
                self._show_results_in_table(results)
                
            except Exception as ex:
                self.page.open(SnackBar(Text(f"❌ エラー: {str(ex)}"), bgcolor=Colors.RED))
            finally:
                self.analyze_btn.disabled = False
                self.update()

        threading.Thread(target=execute).start()

    def _show_results_in_table(self, results):
        self.ai_results_table.rows.clear()
        if not results:
            self.ai_results_table.visible = False
            return

        for res in results:
            def apply_to_form(e, data=res):
                self._reflect_ai_data_to_form(data)

            self.ai_results_table.rows.append(
                DataRow(cells=[
                    DataCell(Text(res.get("bank_name", "-"))),
                    DataCell(Text(res.get("account_type", "-"))),
                    DataCell(Text(res.get("account_number", "-"))),
                    DataCell(ElevatedButton("反映", icon=Icons.ARROW_DOWNWARD, on_click=apply_to_form, style=ButtonStyle(padding=5))),
                ])
            )
        self.ai_results_table.visible = True
        self.update()

    def _reflect_ai_data_to_form(self, data):
        """
        AI解析結果を入力フォームに転記する
        ・【修正】「銀行」や「株式会社」を除去した検索候補を追加してマッチング精度を向上
        ・【修正】フォーム初期化処理の追加
        """
        # ★追加: 反映前にフォームを初期化して、連続反映時の不具合を防ぐ
        self._reset_form()

        # 1. 銀行名の反映
        ai_bank_name = data.get("bank_name", "")
        found_bank_id = None
        
        # 検索候補リストを作成
        # 優先度: 生データ -> 株式会社除去 -> 銀行削除 -> 信用組合変換
        search_candidates = [ai_bank_name]
        
        # 株式会社の削除
        if "株式会社" in ai_bank_name:
            search_candidates.append(ai_bank_name.replace("株式会社", ""))

        # 銀行の削除 (例: ゆうちょ銀行 -> ゆうちょ)
        if "銀行" in ai_bank_name:
            search_candidates.append(ai_bank_name.replace("銀行", ""))

        # 信用組合 -> 信組
        if "信用組合" in ai_bank_name:
            search_candidates.append(ai_bank_name.replace("信用組合", "信組"))

        # 銀行マスタ検索
        for candidate in search_candidates:
            if found_bank_id: break
            candidate_norm = normalize_str(candidate)
            
            for opt in self.bank_name_field.options:
                if opt.key in ["def", "add_new"]: continue
                # マスタ側も正規化して比較
                if candidate_norm in normalize_str(opt.text):
                    found_bank_id = opt.key
                    break
        
        if found_bank_id:
            self.bank_name_field.value = found_bank_id
            self._on_bank_change(None) # 選択イベントを発火して支店リストをロード

            # --- 【追加】支店名の反映処理 ---
            ai_branch_name = data.get("branch_name", "")
            if ai_branch_name:
                # 検索用に正規化 (「支店」などのSuffixを除去して比較率を高める)
                search_branch = normalize_str(ai_branch_name.replace("支店", "").replace("出張所", "").replace("本店", "").replace("営業部", ""))
                found_branch_id = None

                for opt in self.branch_name_field.options:
                    if opt.key in ["def", "add_new_branch"]: continue
                    
                    # マスタ側の名称も正規化して部分一致判定
                    opt_norm = normalize_str(opt.text)
                    if search_branch in opt_norm:
                        found_branch_id = opt.key
                        break
                
                if found_branch_id:
                    self.branch_name_field.value = found_branch_id
                    self._on_branch_change(None) # 選択イベントを発火して支店コードを反映

        else:
            self.page.open(SnackBar(Text(f"銀行「{ai_bank_name}」がマスタに見つかりません。新規登録してください。"), bgcolor="orange"))

        # --- 【追加】口座種類の反映処理 ---
        ai_account_type = data.get("account_type", "")
        if ai_account_type:
            # 正規化して検索
            search_type = normalize_str(ai_account_type)
            found_type_id = None

            for opt in self.account_type_field.options:
                if opt.key in ["def", "add_new_type"]: continue
                
                # 「普通預金」と「普通」などをマッチさせるため部分一致
                if search_type in normalize_str(opt.text) or normalize_str(opt.text) in search_type:
                    found_type_id = opt.key
                    break
            
            if found_type_id:
                self.account_type_field.value = found_type_id

        # 3. その他のフィールド反映
        self.account_number_field.value = data.get("account_number", "")
        balance = str(data.get("balance", "")).replace(",", "")
        self.balance_field.value = balance
        self.status_field.value = "調査完了"
        
        self.update()
        self.page.open(SnackBar(Text("フォームに反映しました。"), bgcolor="blue"))