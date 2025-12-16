# src/views/securities_edit.py
import os
import unicodedata
from typing import Optional, Dict, Any, List

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
    Icon,
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
    FilePicker,
    FilePickerResultEvent,
    Stack,
    Image,
    GestureDetector,
    DragStartEvent,
    DragUpdateEvent,
    Slider,
    ScrollMode,
    DataRow,
    DataCell,
    DataTable,
    DataColumn,
    ButtonStyle,
    CrossAxisAlignment,
    alignment,
    Card,
)
from zengin_code import Bank

# DB設定
from src.models.database import SessionLocal
# モデル
from src.models.tables import BankMaster, BranchMaster, AccountTypeMaster, FinancialAsset
# サービス
from src.services.deceased_service import (
    add_financial_asset_with_type,
    add_or_update_bank_master,
    delete_financial_asset,
    get_account_type_masters,
    get_bank_master_by_id,
    get_bank_masters,
    get_branch_masters_by_bank_id,
    get_financial_asset_by_case_and_type,
    update_financial_asset,
    add_branch_master,
    add_account_type_master,
    update_branch_code,
    update_branch_name,
    get_case_folder_path,
)
from src.services.securities_data import SECURITIES_LIST, SECURITIES_MASTER
from src.services.pdf_service import pdf_service
from src.services.ai_service import ai_service
from src.utils.image_utils import apply_masking_to_image


# --- ヘルパー関数: 文字列正規化 ---
def normalize_str(s: str) -> str:
    """全角英数字を半角に、半角カナを全角に正規化し、空白を除去する"""
    if not s:
        return ""
    return unicodedata.normalize("NFKC", s).strip()


# ---------------------------------------------
# 証券会社マスタ編集/新規登録用ダイアログクラス
# ---------------------------------------------
class SecuritiesMasterEditDialog(AlertDialog):
    def __init__(self, page: Page, on_success: callable):
        super().__init__()
        self.page = page
        self.on_success = on_success
        self.current_editing_id = None

        self.name_field = TextField(label="証券会社名", width=300, on_change=self.on_name_change)
        self.code_field = TextField(label="金融機関コード", width=150)
        
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
        
        self.title = Text("証券会社マスタの登録/編集")
        self.content = Column([self.name_field, self.suggestions_container, self.code_field], tight=True, spacing=5)
        self.actions = [TextButton("キャンセル", on_click=self.close_dialog), self.save_button]
        self.modal = True

    def show(self, master_id: int | None = None):
        self.current_editing_id = master_id
        if master_id:
            master = get_bank_master_by_id(master_id)
            if master:
                self.name_field.value = master.bank_name
                self.code_field.value = master.bank_code
                self.title.value = "証券会社情報の編集"
        else:
            self.name_field.value = ""
            self.code_field.value = ""
            self.title.value = "新しい証券会社を登録"
        
        self.suggestions_container.visible = False
        self.page.open(self)
        self.page.update()

    def close_dialog(self, e=None):
        self.page.close(self)
        self.page.update()

    def on_name_change(self, e):
        val = self.name_field.value.strip()
        if not val:
            self.suggestions_container.visible = False
            self.suggestions_container.update()
            return

        matches = []
        # 証券会社リストから検索
        search_term = normalize_str(val).replace("証券", "").replace("株式会社", "")
        
        for sec in SECURITIES_LIST:
            sec_name_norm = normalize_str(sec["name"])
            sec_kana_norm = normalize_str(sec["kana"])
            if search_term in sec_name_norm or normalize_str(val) in sec_kana_norm:
                matches.append(sec)

        if matches:
            self.suggestions_list.controls.clear()
            for sec in matches:
                self.suggestions_list.controls.append(
                    ListTile(
                        title=Text(f"{sec['name']}", size=14),
                        subtitle=Text(f"{sec['kana']} ({sec['code']})", size=12, color=Colors.GREY),
                        data=sec,
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
        data = e.control.data
        self.name_field.value = data["name"]
        self.code_field.value = data["code"]
        self.name_field.update()
        self.code_field.update()
        self.suggestions_container.visible = False
        self.suggestions_container.update()
        self.save_button.focus()

    def save_master(self, e):
        name = self.name_field.value
        code = self.code_field.value

        if not name or not code:
            self.page.open(SnackBar(Text("名称とコードは必須です。"), bgcolor=Colors.RED_500))
            self.page.update()
            return

        new_master = add_or_update_bank_master(self.current_editing_id, name, code)

        if new_master:
            self.on_success(new_master)
            self.close_dialog()
            self.page.open(SnackBar(Text("証券会社情報が正常に保存されました。"), bgcolor=Colors.GREEN_500))
        else:
            self.page.open(SnackBar(Text("保存に失敗しました。"), bgcolor=Colors.RED_500))
        self.page.update()


# ---------------------------------------------
# 部店マスタ編集/新規登録用ダイアログクラス
# ---------------------------------------------
class BranchMasterEditDialog(AlertDialog):
    def __init__(self, page: Page, on_success: callable):
        super().__init__()
        self.page = page
        self.on_success = on_success
        self.parent_bank_id = None

        self.name_field = TextField(
            label="部店名", 
            width=250,
            on_blur=self.on_name_blur
        )
        self.code_field = TextField(
            label="部店コード", 
            width=150,
            on_blur=self.on_code_blur
        )
        self.save_button = ElevatedButton("保存", on_click=self.save_branch)

        self.title = Text("部店マスタの登録")
        self.content = Column([self.name_field, self.code_field], tight=True, spacing=10)
        self.actions = [TextButton("キャンセル", on_click=self.close_dialog), self.save_button]
        self.modal = True

    def show(self, bank_id: int):
        self.parent_bank_id = bank_id
        
        self.name_field.value = ""
        self.code_field.value = ""
        self.page.open(self)
        self.page.update()
        self.name_field.focus()

    def close_dialog(self, e=None):
        self.page.close(self)
        self.page.update()

    def on_code_blur(self, e):
        # 証券の場合はZenginCodeライブラリで部店まで網羅されていないことが多いため
        # ここでの自動検索は実装しないか、簡易的なものに留める
        pass

    def on_name_blur(self, e):
        pass

    def save_branch(self, e):
        name = self.name_field.value
        code = self.code_field.value

        if not name or not code:
            self.page.open(SnackBar(Text("部店名とコードは必須です。"), bgcolor=Colors.RED_500))
            self.page.update()
            return

        db = SessionLocal()
        try:
            existing = db.query(BranchMaster).filter(BranchMaster.bank_id == self.parent_bank_id, BranchMaster.branch_code == code).first()
            if existing:
                self.page.open(SnackBar(Text("この部店コードは既に登録されています。"), bgcolor=Colors.RED_500))
                self.page.update()
                return

            new_branch = BranchMaster(bank_id=self.parent_bank_id, branch_name=name, branch_code=code)
            db.add(new_branch)
            db.commit()
            db.refresh(new_branch)
            
            self.on_success(new_branch)
            self.close_dialog()
            self.page.open(SnackBar(Text("部店を登録しました。"), bgcolor=Colors.GREEN_500))
        except Exception as ex:
            db.rollback()
            self.page.open(SnackBar(Text(f"保存エラーが発生しました: {ex}"), bgcolor=Colors.RED_500))
            self.page.update()
        finally:
            db.close()


# ---------------------------------------------
# 口座種類マスタ編集/新規登録用ダイアログクラス
# ---------------------------------------------
class AccountTypeMasterEditDialog(AlertDialog):
    def __init__(self, page: Page, on_success: callable):
        super().__init__()
        self.page = page
        self.on_success = on_success

        self.name_field = TextField(label="口座種類名", width=250, hint_text="例: 特定預り、一般預り")
        self.save_button = ElevatedButton("保存", on_click=self.save_account_type)

        self.title = Text("口座種類の登録")
        self.content = Column([self.name_field], tight=True, spacing=10)
        self.actions = [TextButton("キャンセル", on_click=self.close_dialog), self.save_button]
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

        db = SessionLocal()
        try:
            existing = db.query(AccountTypeMaster).filter(AccountTypeMaster.type_name == name).first()
            if existing:
                self.page.open(SnackBar(Text("この口座種類は既に存在します。"), bgcolor=Colors.RED_500))
                self.page.update()
                return

            new_type = AccountTypeMaster(type_name=name)
            db.add(new_type)
            db.commit()
            db.refresh(new_type)
            
            self.on_success(new_type)
            self.close_dialog()
            self.page.open(SnackBar(Text("口座種類を登録しました。"), bgcolor=Colors.GREEN_500))
        except Exception as ex:
            db.rollback()
            self.page.open(SnackBar(Text(f"保存エラー: {ex}"), bgcolor=Colors.RED_500))
            self.page.update()
        finally:
            db.close()


# ---------------------------------------------
# メイン画面クラス (SecuritiesEditView)
# ---------------------------------------------
class SecuritiesEditView(Column):
    """証券口座登録・編集画面"""

    def __init__(self, page: Page, case_id: int):
        super().__init__(expand=True, scroll="auto", spacing=20)
        self.page = page
        self.case_id = case_id
        self.editing_asset_id = None

        # --- AI/PDF関連 ---
        self.nayose_picker = FilePicker(on_result=self._on_nayose_picked)
        self.page.overlay.append(self.nayose_picker)
        
        self.nayose_image_base64: Optional[str] = None
        self.nayose_img_width = 0
        self.nayose_img_height = 0
        self.current_display_width = 800.0
        self.page_images = []
        self.current_page_index = 0

        self.mask_rects = []
        self.current_mask = None
        self.drag_start_x = 0
        self.drag_start_y = 0

        # マスキングUI
        self.masking_stack = Stack()
        self.masking_container = Container(
            content=self.masking_stack,
            width=self.current_display_width,
            height=400,
            bgcolor=Colors.GREY_200,
            visible=False,
            border=border.all(1, Colors.GREY_400),
        )
        self.zoom_slider = Slider(
            min=600, max=1600, divisions=10, value=self.current_display_width,
            label="表示サイズ: {value}px", width=300, on_change=self._on_zoom_change, disabled=True,
        )
        self.analyze_btn = ElevatedButton(
            "表示ページをAI解析", icon=Icons.ANALYTICS, on_click=self._run_ai_analysis,
            bgcolor=Colors.PURPLE_600, color=Colors.WHITE, visible=False
        )

        self.btn_prev = IconButton(icon=Icons.ARROW_BACK, on_click=self.on_prev_page, disabled=True, tooltip="前のページ")
        self.btn_next = IconButton(icon=Icons.ARROW_FORWARD, on_click=self.on_next_page, disabled=True, tooltip="次のページ")
        self.txt_page_indicator = Text("0 / 0", size=16, weight=FontWeight.BOLD)
        
        def _header_text(label: str):
            return Text(label, color=Colors.BLUE_GREY_900, weight=FontWeight.BOLD)

        self.ai_candidates_table = DataTable(
            columns=[
                DataColumn(_header_text("会社名")),
                DataColumn(_header_text("部店名")),
                DataColumn(_header_text("区分")),
                DataColumn(_header_text("口座番号")),
                DataColumn(_header_text("評価額")),
                DataColumn(_header_text("操作")),
            ],
            rows=[], visible=False, heading_row_color=Colors.PURPLE_50,
        )

        # --- 登録フォーム ---
        self.securities_name_field = Dropdown(label="証券会社名 *", width=250, color=Colors.BLACK, label_style=TextStyle(color=Colors.BLACK), on_change=self.on_security_change)
        self.branch_name_field = Dropdown(label="部店名", width=250, color=Colors.BLACK, label_style=TextStyle(color=Colors.BLACK), on_change=self.on_branch_change)
        self.account_type_field = Dropdown(label="口座種類", width=150, color=Colors.BLACK, label_style=TextStyle(color=Colors.BLACK), on_change=self.on_account_type_change)
        
        self.securities_code_field = TextField(label="金融機関コード", width=100, color=Colors.BLACK, label_style=TextStyle(color=Colors.BLACK), on_blur=self.on_bank_code_blur)
        self.branch_code_field = TextField(label="部店コード", width=100, color=Colors.BLACK, label_style=TextStyle(color=Colors.BLACK), on_blur=self.on_branch_code_blur)
        
        self.account_number_field = TextField(label="口座番号 *", width=250, color=Colors.BLACK, label_style=TextStyle(color=Colors.BLACK))
        self.balance_field = TextField(label="評価額", width=250, color=Colors.BLACK, label_style=TextStyle(color=Colors.BLACK))
        self.status_field = TextField(label="ステータス", value="調査中", width=250, color=Colors.BLACK, label_style=TextStyle(color=Colors.BLACK))

        self.main_action_button = ElevatedButton("証券口座を登録", icon=Icons.ADD_CARD, bgcolor=Colors.BLUE_600, color=Colors.WHITE, on_click=self.save_asset)
        self.cancel_edit_button = ElevatedButton("キャンセル", icon=Icons.CANCEL, visible=False, bgcolor=Colors.GREY_600, color=Colors.WHITE, on_click=self.reset_form)

        self.assets_list_view = ListView(spacing=10, expand=True)

        # ダイアログ
        self.master_dialog = SecuritiesMasterEditDialog(page, self.on_master_saved)
        self.branch_dialog = BranchMasterEditDialog(page, self.on_branch_saved)
        self.account_type_dialog = AccountTypeMasterEditDialog(page, self.on_account_type_saved)

        # --- レイアウト ---
        self.controls = [
            Text("💹 証券口座登録", size=24, weight=FontWeight.BOLD),
            Divider(),
            
            # AI読み取りエリア
            Card(
                content=Container(
                    content=Column([
                        Row([Icon(Icons.AUTO_AWESOME, color=Colors.PURPLE), Text("取引残高報告書から読み取り", weight=FontWeight.BOLD, size=16)]),
                        Text("1. PDFを選択 → 2. ページ切り替え・サイズ調整 → 3. 黒塗り(ドラッグ) → 4. AI解析 → 5. 反映", size=12, color=Colors.GREY_700),
                        Row([
                            ElevatedButton("PDFを選択", icon=Icons.UPLOAD_FILE, on_click=self._open_nayose_picker, bgcolor=Colors.PURPLE_50, color=Colors.PURPLE_900),
                            Container(width=10),
                            self.btn_prev,
                            self.txt_page_indicator,
                            self.btn_next,
                            Container(width=20),
                            Text("表示サイズ:"), self.zoom_slider, self.analyze_btn,
                        ], vertical_alignment=CrossAxisAlignment.CENTER),
                        Row([self.masking_container], scroll=ScrollMode.AUTO),
                        self.ai_candidates_table,
                    ], spacing=15),
                    padding=20, border=border.all(1, Colors.PURPLE_100),
                ), elevation=0,
            ),
            Divider(height=30, color=Colors.TRANSPARENT),

            # 入力フォーム
            Container(
                content=Column([
                    Text("証券口座情報", weight=FontWeight.W_600, color=Colors.BLACK),
                    Row([self.securities_name_field, self.securities_code_field]),
                    Row([self.branch_name_field, self.branch_code_field]),
                    Row([self.account_number_field, self.account_type_field, self.balance_field, self.status_field]),
                    Row([self.cancel_edit_button, self.main_action_button], alignment=MainAxisAlignment.END),
                ], spacing=15),
                padding=20, border_radius=10, bgcolor=Colors.WHITE,
            ),
            Divider(),
            Text("登録済み証券口座一覧", size=18, weight=FontWeight.BOLD),
            Container(content=self.assets_list_view, padding=10, height=300, border_radius=5, bgcolor=Colors.WHITE),
        ]

        self.load_securities_options()
        self.load_account_type_options()
        self.update_assets_list()

    # --- AI/PDF 関連ロジック ---
    def _open_nayose_picker(self, e):
        init_path = get_case_folder_path(self.case_id)
        self.nayose_picker.pick_files(allow_multiple=False, allowed_extensions=["pdf"], initial_directory=init_path)

    def _on_nayose_picked(self, e: FilePickerResultEvent):
        if not e.files: return
        self.page.open(SnackBar(Text("読み込み中..."), bgcolor=Colors.BLUE))
        self.page.update()

        def process_pdf():
            try:
                images = pdf_service.convert_pdf_to_images_sync(e.files[0].path)
                if not images: raise ValueError("画像変換失敗")
                
                self.page_images = images
                self.current_page_index = 0
                
                self.mask_rects = []
                self.masking_stack.controls.clear()
                
                self._update_page_view()
                
                self.masking_container.visible = True
                self.analyze_btn.visible = True
                self.zoom_slider.disabled = False
                self.ai_candidates_table.rows.clear()
                self.ai_candidates_table.visible = False
                
                self.update()
                self.page.open(SnackBar(Text(f"読み込み完了 (全{len(images)}ページ)"), bgcolor=Colors.GREEN))
            except Exception as ex:
                self.page.open(SnackBar(Text(f"エラー: {ex}"), bgcolor=Colors.RED))
        
        self.page.run_thread(process_pdf)

    def _update_page_view(self):
        if not self.page_images: return

        page_img = self.page_images[self.current_page_index]
        self.nayose_image_base64 = page_img.base64_image
        self.nayose_img_width = page_img.width
        self.nayose_img_height = page_img.height

        self.mask_rects = []
        self.masking_stack.controls.clear()
        
        img_control = Image(src_base64=self.nayose_image_base64, width=self.current_display_width, fit="contain")
        gesture = GestureDetector(
            content=img_control, 
            on_pan_start=self._on_mask_pan_start, 
            on_pan_update=self._on_mask_pan_update, 
            on_pan_end=self._on_mask_pan_end
        )
        self.masking_stack.controls.append(gesture)

        display_h = self.current_display_width * (self.nayose_img_height / self.nayose_img_width)
        self.masking_container.width = self.current_display_width
        self.masking_container.height = display_h

        self.btn_prev.disabled = self.current_page_index == 0
        self.btn_next.disabled = self.current_page_index == len(self.page_images) - 1
        self.txt_page_indicator.value = f"{self.current_page_index + 1} / {len(self.page_images)}"
        
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
            self.masking_stack.controls[0].content.width = new_w
        
        new_masks = []
        for i in range(1, len(self.masking_stack.controls)):
            m = self.masking_stack.controls[i]
            m.left *= ratio
            m.top *= ratio
            m.width *= ratio
            m.height *= ratio
        
        for r in self.mask_rects:
            new_masks.append((r[0]*ratio, r[1]*ratio, r[2]*ratio, r[3]*ratio))
        self.mask_rects = new_masks
        self.update()

    def _on_mask_pan_start(self, e: DragStartEvent):
        self.drag_start_x, self.drag_start_y = e.local_x, e.local_y
        self.current_mask = Container(bgcolor=Colors.BLACK, opacity=0.8, left=self.drag_start_x, top=self.drag_start_y, width=0, height=0)
        self.masking_stack.controls.append(self.current_mask)
        self.masking_stack.update()

    def _on_mask_pan_update(self, e: DragUpdateEvent):
        if not self.current_mask: return
        curr_x, curr_y = e.local_x, e.local_y
        self.current_mask.left = min(self.drag_start_x, curr_x)
        self.current_mask.top = min(self.drag_start_y, curr_y)
        self.current_mask.width = abs(curr_x - self.drag_start_x)
        self.current_mask.height = abs(curr_y - self.drag_start_y)
        self.current_mask.update()

    def _on_mask_pan_end(self, e):
        if not self.current_mask: return
        self.mask_rects.append((self.current_mask.left, self.current_mask.top, self.current_mask.width, self.current_mask.height))
        self.masking_stack.controls.remove(self.current_mask)
        self.masking_stack.controls.append(Container(bgcolor=Colors.BLACK, opacity=0.8, left=self.current_mask.left, top=self.current_mask.top, width=self.current_mask.width, height=self.current_mask.height))
        self.current_mask = None
        self.masking_stack.update()

    def _run_ai_analysis(self, e):
        if not self.nayose_image_base64: return
        self.page.open(SnackBar(Text(f"{self.current_page_index + 1}ページ目を解析中..."), bgcolor=Colors.BLUE))
        self.analyze_btn.disabled = True
        self.update()

        def execute():
            try:
                masked_b64 = apply_masking_to_image(
                    self.nayose_image_base64, self.mask_rects, self.nayose_img_width, self.nayose_img_height,
                    self.current_display_width, self.masking_container.height
                )
                results = ai_service.analyze_securities_document_sync(masked_b64)
                self._show_ai_results(results)
                self.page.open(SnackBar(Text(f"解析完了: {len(results)}件"), bgcolor=Colors.GREEN))
            except Exception as ex:
                self.page.open(SnackBar(Text(f"解析エラー: {ex}"), bgcolor=Colors.RED))
            finally:
                self.analyze_btn.disabled = False
                self.update()
        self.page.run_thread(execute)

    def _show_ai_results(self, results):
        self.ai_candidates_table.rows.clear()
        if not results:
            self.ai_candidates_table.visible = False
            return
        
        for item in results:
            def apply(e, d=item):
                self._reflect_ai_result(d)

            row = DataRow(cells=[
                DataCell(Text(item.get("securities_name", "-"))),
                DataCell(Text(item.get("branch_name", "-"))),
                DataCell(Text(item.get("account_type", "-"))),
                DataCell(Text(item.get("account_number", "-"))),
                DataCell(Text(str(item.get("balance", "-")))),
                DataCell(ElevatedButton("反映", icon=Icons.ARROW_DOWNWARD, on_click=apply, style=ButtonStyle(padding=5), height=30))
            ])
            self.ai_candidates_table.rows.append(row)
        self.ai_candidates_table.visible = True
        self.update()

    def _reflect_ai_result(self, data):
        """AI結果をフォームに反映"""
        
        # 1. 証券会社マッチング
        raw_ai_sec = data.get("securities_name", "").replace("株式会社", "").replace("証券", "").strip()
        ai_sec_norm = normalize_str(raw_ai_sec)
        
        found_sec_id = None
        bank_id = None

        for opt in self.securities_name_field.options:
            if opt.key in ["def", "add_new"]: continue
            opt_text_norm = normalize_str(opt.text)
            if ai_sec_norm in opt_text_norm:
                found_sec_id = opt.key
                break
        
        if found_sec_id:
            self.securities_name_field.value = found_sec_id
            bank_id = int(found_sec_id)
            
            db = SessionLocal()
            try:
                master = db.query(BankMaster).get(bank_id)
                if master:
                    self.securities_code_field.value = master.bank_code
                    self.load_branch_options(bank_id)
            finally:
                db.close()
            
            # 2. 部店名マッチング & 自動登録
            raw_ai_branch = data.get("branch_name", "").replace("本店", "").replace("支店", "").replace("部店", "").strip()
            ai_branch_norm = normalize_str(raw_ai_branch)
            
            found_branch_id = None
            if raw_ai_branch:
                for opt in self.branch_name_field.options:
                    if opt.key in ["def", "add_new_branch"]: continue
                    opt_text_norm = normalize_str(opt.text)
                    if ai_branch_norm in opt_text_norm:
                        found_branch_id = opt.key
                        break
                
                if not found_branch_id:
                    # コードが読み取れていない場合は"000"などで登録
                    reg_code = "000" 
                    # 必要であればAI結果から部店コードを取得するロジックを追加可能

                    try:
                        db = SessionLocal()
                        existing_by_code = None
                        # 証券の場合、部店コードはAIから取得しにくい場合が多いので、名前重複を優先チェック
                        try:
                             # 名前で既存チェック (厳密にはコードで管理すべきだが、AI入力補助のため)
                             # 簡易的に同じ名前の支店があるか確認
                             pass 
                        finally:
                            db.close()

                        # 新規登録 (証券はコード必須ではない運用が多いが、システム上は必要なら000)
                        new_branch = add_branch_master(bank_id, raw_ai_branch, reg_code)
                        if new_branch:
                            self.load_branch_options(bank_id)
                            found_branch_id = str(new_branch.id)
                            self.page.open(SnackBar(Text(f"部店「{raw_ai_branch}」を自動登録しました"), bgcolor=Colors.GREEN))
                    
                    except Exception as e:
                        print(f"Auto branch register failed: {e}")

            if found_branch_id:
                self.branch_name_field.value = found_branch_id
                branch_id = int(found_branch_id)
                db = SessionLocal()
                try:
                    branch = db.query(BranchMaster).get(branch_id)
                    if branch: self.branch_code_field.value = branch.branch_code
                finally:
                    db.close()
        
        else:
            self.page.open(SnackBar(Text(f"証券会社「{raw_ai_sec}」が見つかりませんでした。手動で選択してください。"), bgcolor=Colors.ORANGE))

        # 3. その他フィールド
        self.account_number_field.value = str(data.get("account_number", "")).replace(" ", "")
        self.balance_field.value = str(data.get("balance", "")).replace(",", "")
        self.status_field.value = "調査完了"

        # 4. 口座種類
        ai_type = data.get("account_type", "").strip()
        found_type_id = None
        if ai_type:
            # 証券用のゆらぎ吸収 (例: 特定預り -> 特定)
            search_type = ai_type.replace("預り", "").replace("口座", "")
            
            for opt in self.account_type_field.options:
                if opt.key in ["def", "add_new_type"]: continue
                if search_type in opt.text:
                    found_type_id = opt.key
                    break
            
            if not found_type_id:
                try:
                    new_type = add_account_type_master(type_name=ai_type)
                    if new_type:
                        self.load_account_type_options()
                        found_type_id = str(new_type.id)
                except Exception as e:
                    print(f"Auto account type register failed: {e}")

        if found_type_id:
            self.account_type_field.value = found_type_id

        # 5. 既存口座チェック
        if bank_id and self.account_number_field.value:
            assets = get_financial_asset_by_case_and_type(self.case_id, "SECURITIES")
            existing_asset = next((a for a in assets if a.get("bank_id") == bank_id and a.get("account_number") == self.account_number_field.value), None)
            
            if existing_asset:
                self.editing_asset_id = existing_asset["id"]
                self.main_action_button.text = "口座情報を修正"
                self.main_action_button.icon = Icons.SAVE
                self.cancel_edit_button.visible = True
                self.page.open(SnackBar(Text("既存の口座が見つかりました。編集モードで反映します。"), bgcolor=Colors.AMBER))
            else:
                self.editing_asset_id = None
                self.main_action_button.text = "証券口座を登録"
                self.main_action_button.icon = Icons.ADD_CARD
                self.cancel_edit_button.visible = True

        self.update()

    # --- 既存ロジック ---
    def load_securities_options(self):
        masters = get_bank_masters()
        options = [dropdown.Option("def", text="選択してください"), dropdown.Option("add_new", text="[ ➕ 新しい証券会社を登録 ]")]
        for m in masters:
            # 証券会社のみを抽出 (コード範囲や名称で判定)
            is_sec = (m.bank_code in SECURITIES_MASTER) or ("証券" in m.bank_name)
            if is_sec:
                options.append(dropdown.Option(str(m.id), text=f"{m.bank_name} ({m.bank_code})"))
        self.securities_name_field.options = options

    def load_account_type_options(self):
        types = get_account_type_masters()
        options = [dropdown.Option("def", text="選択してください"), dropdown.Option("add_new_type", text="[ ➕ 新しい口座種類を登録 ]")]
        for t in types:
            options.append(dropdown.Option(str(t.id), text=t.type_name))
        self.account_type_field.options = options

    def on_security_change(self, e):
        val = self.securities_name_field.value
        if val == "add_new":
            self.securities_name_field.value = "def"
            self.master_dialog.show()
            self.securities_name_field.update()
            return
        if val and val != "def":
            mid = int(val)
            db = SessionLocal()
            try:
                master = db.query(BankMaster).get(mid)
                if master:
                    self.securities_code_field.value = master.bank_code
                    self.load_branch_options(mid)
                    self.securities_code_field.update()
                    self.page.update()
            finally:
                db.close()
        else:
            self.reset_branch_fields()
            self.page.update()

    def reset_branch_fields(self):
        self.securities_code_field.value = ""
        self.branch_name_field.options = [dropdown.Option("def", text="選択してください"), dropdown.Option("add_new_branch", text="[ ➕ 新しい部店を登録 ]")]
        self.branch_name_field.value = "def"
        self.branch_code_field.value = ""
        self.branch_name_field.update()

    def load_branch_options(self, master_id):
        self.branch_name_field.value = "def"
        self.branch_code_field.value = ""
        branches = get_branch_masters_by_bank_id(master_id)
        options = [dropdown.Option("def", text="選択してください"), dropdown.Option("add_new_branch", text="[ ➕ 新しい部店を登録 ]")]
        options.extend([dropdown.Option(str(b.id), text=f"{b.branch_name} ({b.branch_code})") for b in branches])
        self.branch_name_field.options = options

    def on_branch_change(self, e):
        val = self.branch_name_field.value
        if val == "add_new_branch":
            if not self.securities_name_field.value or self.securities_name_field.value == "def":
                self.page.open(SnackBar(Text("先に証券会社を選択してください"), bgcolor=Colors.RED_500))
                self.branch_name_field.value = "def"
                self.page.update()
                return
            self.branch_dialog.show(int(self.securities_name_field.value))
            self.branch_name_field.value = "def"
            return
        if val and val != "def":
            try:
                bid = int(val)
                db = SessionLocal()
                try:
                    br = db.query(BranchMaster).get(bid)
                    if br: 
                        self.branch_code_field.value = br.branch_code
                        self.branch_code_field.update()
                finally:
                    db.close()
            except ValueError:
                pass
        else:
            self.branch_code_field.value = ""
            self.branch_code_field.update()

    def on_account_type_change(self, e):
        if self.account_type_field.value == "add_new_type":
            self.account_type_field.value = "def"
            self.account_type_dialog.show()
            self.account_type_field.update()

    def on_master_saved(self, new_master):
        self.load_securities_options()
        self.securities_name_field.value = str(new_master.id)
        self.securities_code_field.value = new_master.bank_code
        self.load_branch_options(new_master.id)
        self.page.update()

    def on_branch_saved(self, new_branch):
        self.load_branch_options(new_branch.bank_id)
        self.branch_name_field.value = str(new_branch.id)
        self.branch_code_field.value = new_branch.branch_code
        self.page.update()

    def on_account_type_saved(self, new_type):
        self.load_account_type_options()
        self.account_type_field.value = str(new_type.id)
        self.page.update()

    def on_bank_code_blur(self, e):
        # 銀行コードからの逆引き（必要なら実装）
        pass

    def on_branch_code_blur(self, e):
        # 部店コードからの逆引き（必要なら実装）
        pass

    def save_asset(self, e):
        try:
            sec_id_str = self.securities_name_field.value
            if not sec_id_str or sec_id_str in ["def", "add_new"]:
                raise ValueError("証券会社を選択してください")
            
            mid = int(sec_id_str)
            bid = None
            if self.branch_name_field.value and self.branch_name_field.value not in ["def", "add_new_branch"]:
                bid = int(self.branch_name_field.value)
                
                # 💡 支店コードの上書き更新 (bank_edit.pyと同様)
                new_code = self.branch_code_field.value.strip()
                if new_code:
                     update_branch_code(bid, new_code)

            aid = None
            if self.account_type_field.value and self.account_type_field.value not in ["def", "add_new_type"]:
                aid = int(self.account_type_field.value)
            
            bal = float(self.balance_field.value.replace(",", "")) if self.balance_field.value else 0.0

            if self.editing_asset_id:
                success = update_financial_asset(self.editing_asset_id, mid, bid, aid, self.account_number_field.value, bal, self.status_field.value)
                msg = "証券口座情報を修正しました。"
            else:
                success = add_financial_asset_with_type(self.case_id, "SECURITIES", mid, bid, aid, self.account_number_field.value, bal, self.status_field.value)
                msg = "証券口座を登録しました。"
            
            if success:
                self.page.open(SnackBar(Text(msg, color=Colors.WHITE), bgcolor=Colors.GREEN_700))
                self.reset_form()
                self.update_assets_list()
            else:
                raise Exception("DB Error")
        except Exception as ex:
            self.page.open(SnackBar(Text(f"エラー: {ex}", color=Colors.WHITE), bgcolor=Colors.RED_700))
        self.page.update()

    def delete_asset(self, e):
        if delete_financial_asset(e.control.data):
            self.page.open(SnackBar(Text("削除しました"), bgcolor=Colors.RED_700))
            self.update_assets_list()
        self.page.update()

    def start_edit(self, e):
        aid = e.control.data
        assets = get_financial_asset_by_case_and_type(self.case_id, "SECURITIES")
        t = next((a for a in assets if a["id"] == aid), None)
        if t:
            self.editing_asset_id = aid
            self.securities_name_field.value = str(t.get("bank_id")) if t.get("bank_id") else "def"
            if t.get("bank_id"): self.load_branch_options(t["bank_id"])
            self.branch_name_field.value = str(t.get("branch_id")) if t.get("branch_id") else "def"
            self.account_type_field.value = str(t.get("account_type_id")) if t.get("account_type_id") else "def"
            self.securities_code_field.value = t.get("bank_code", "")
            self.branch_code_field.value = t.get("branch_code", "")
            self.account_number_field.value = t["account_number"]
            self.balance_field.value = f"{t['balance']:,.0f}" if t["balance"] else ""
            self.status_field.value = t["status"]
            self.main_action_button.text = "口座情報を修正"
            self.main_action_button.icon = Icons.SAVE
            self.cancel_edit_button.visible = True
            self.page.update()

    def reset_form(self, e=None):
        self.editing_asset_id = None
        self.securities_name_field.value = "def"
        self.reset_branch_fields() # 💡 修正
        self.account_type_field.value = "def"
        self.account_number_field.value = ""
        self.balance_field.value = ""
        self.status_field.value = "調査中"
        self.main_action_button.text = "証券口座を登録"
        self.main_action_button.icon = Icons.ADD_CARD
        self.cancel_edit_button.visible = False
        self.page.update()

    def update_assets_list(self):
        assets = get_financial_asset_by_case_and_type(self.case_id, "SECURITIES")
        self.assets_list_view.controls.clear()
        if not assets:
            self.assets_list_view.controls.append(Text("登録された口座はありません", color=Colors.GREY_600))
        else:
            for a in assets:
                info = f"🏢 {a['bank_name']} ({a.get('branch_name', '-')}) - {a['account_number']}"
                bal = f"¥{a['balance']:,.0f}" if a['balance'] is not None else "-"
                self.assets_list_view.controls.append(Row([
                    Text(info, width=400, color=Colors.BLACK87),
                    Text(bal, width=100, text_align="right", color=Colors.BLACK87),
                    IconButton(Icons.EDIT, icon_color=Colors.BLUE_400, data=a["id"], on_click=self.start_edit),
                    IconButton(Icons.DELETE, icon_color=Colors.RED_400, data=a["id"], on_click=self.delete_asset)
                ]))
        self.page.update()