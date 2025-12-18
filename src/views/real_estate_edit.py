# src/views/real_estate_edit.py
import os
import glob
import re
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Optional

from flet import (
    Card,
    Colors,
    Column,
    Container,
    Divider,
    Dropdown,
    ElevatedButton,
    FilePicker,
    FilePickerResultEvent,
    FontWeight,
    IconButton,
    Icons,
    Icon,
    Image,
    Page,
    Row,
    SnackBar,
    Text,
    TextField,
    alignment,
    border,
    dropdown,
    Stack,
    GestureDetector,
    DragStartEvent,
    DragUpdateEvent,
    MainAxisAlignment,
    CrossAxisAlignment,
    ButtonStyle,
    Slider,
    ScrollMode,
    TextStyle,
    AlertDialog,
    TextButton,
    ControlEvent,
    Chip,
    padding,
)

# サービス層のインポート
from src.services.real_estate_service import (
    add_real_estate,
    update_real_estate,
    delete_real_estate,
    get_real_estates_by_case,
    save_registry_document,
)
from src.services.deceased_service import get_case_folder_path
from src.services.pdf_service import pdf_service
from src.services.ai_service import ai_service
from src.utils.image_utils import apply_masking_to_image


class RealEstateEditView(Column):
    """
    不動産情報・登記情報管理画面 (完全版)
    登録・編集・削除・AI解析・自治体判別・プレビュー機能のすべてを含みます。
    """

    def __init__(self, page: Page, case_id: int):
        super().__init__(expand=True, scroll=ScrollMode.AUTO, spacing=20)
        self.page: Page = page
        self.case_id: int = case_id

        # --- 状態管理 ---
        self.input_forms: List[Dict[str, Any]] = []
        self.ai_properties_buffer: List[Dict[str, Any]] = [] # 解析結果の一時保持用
        self._target_asset_id: Optional[int] = None

        # --- UIコンポーネント: フォームエリア ---
        self.forms_container = Column(spacing=15)
        
        # 登録・修正ボタン
        self.register_btn = ElevatedButton(
            "不動産情報を登録",
            icon=Icons.SAVE,
            style=ButtonStyle(
                bgcolor="primary",
                color="onPrimary",
                padding=20,
            ),
            on_click=self._on_register_click,
        )
        
        self.add_form_btn = ElevatedButton(
            "入力欄を追加",
            icon=Icons.ADD,
            on_click=lambda _: self._add_input_form(),
            style=ButtonStyle(
                bgcolor="secondaryContainer",
                color="onSecondaryContainer",
            )
        )

        # --- UIコンポーネント: AI解析エリア ---
        self.location_candidates_row = Row(wrap=True, spacing=10)
        self.candidate_area = Container(
            content=Column([
                Text("📍 AIが特定した自治体候補 (クリックして住所に反映):", weight=FontWeight.BOLD, size=14, color="onSurface"),
                self.location_candidates_row,
            ], spacing=10),
            visible=False,
            padding=15,
            bgcolor="surfaceVariant",
            border_radius=10,
        )

        self.nayose_picker = FilePicker(on_result=self._on_nayose_picked)
        self.nayose_image_base64: Optional[str] = None
        self.nayose_img_width: int = 0
        self.nayose_img_height: int = 0
        self.current_display_width: float = 800.0
        self.mask_rects: List[tuple] = []
        self.current_mask: Optional[Container] = None
        self.drag_start_x: float = 0
        self.drag_start_y: float = 0

        self.zoom_slider = Slider(
            min=600, max=1600, value=self.current_display_width,
            label="表示サイズ: {value}px", width=300, on_change=self._on_zoom_change, disabled=True,
        )

        self.masking_stack = Stack()
        self.masking_container = Container(
            content=self.masking_stack,
            visible=False,
            border=border.all(1, "outlineVariant"),
            bgcolor="surface",
        )
        
        self.analyze_btn = ElevatedButton(
            "AI解析を実行", 
            icon=Icons.ANALYTICS, 
            on_click=self._run_ai_analysis,
            bgcolor="primary", 
            color="onPrimary", 
            visible=False
        )

        # --- UIコンポーネント: リスト表示エリア ---
        self.asset_list = Column(spacing=10)

        # --- UIコンポーネント: プレビューダイアログ ---
        self.registry_picker = FilePicker(on_result=self._on_registry_picked)
        self.preview_images: List[str] = []
        self.preview_page_index: int = 0
        self.preview_scale: float = 1.0
        self.preview_image_control = Image(src="", fit="contain", width=900, height=600)
        self.preview_scale_slider = Slider(
            min=0.5, max=3.0, value=1.0, width=300, on_change=self._on_preview_scale_change
        )
        self.preview_prev_btn = IconButton(icon=Icons.ARROW_BACK, on_click=self._prev_preview_page, disabled=True)
        self.preview_next_btn = IconButton(icon=Icons.ARROW_FORWARD, on_click=self._next_preview_page, disabled=True)
        self.preview_page_text = Text("0 / 0", size=16, weight=FontWeight.BOLD)

        self.preview_dialog = AlertDialog(
            modal=True,
            title=Text("登記情報プレビュー"),
            content=Column([
                Container(
                    content=self.preview_image_control,
                    width=950, height=650, alignment=alignment.center,
                    clip_behavior="hardEdge", bgcolor="black12",
                ),
                Row([
                    self.preview_prev_btn, self.preview_page_text, self.preview_next_btn,
                    Container(width=20), Text("ズーム:"), self.preview_scale_slider,
                ], alignment=MainAxisAlignment.CENTER)
            ], tight=True),
            actions=[TextButton("閉じる", on_click=self._close_preview_dialog)],
            actions_alignment=MainAxisAlignment.CENTER,
        )

        self._init_layout()

    def _init_layout(self) -> None:
        """画面の初期レイアウトを構築"""
        self.controls = [
            Text("🏠 不動産・登記情報管理", size=24, weight=FontWeight.BOLD, color="onSurface"),
            Divider(),
            
            # AI読み取りセクション
            Card(
                content=Container(
                    padding=20,
                    content=Column([
                        Row([Icon(Icons.AUTO_AWESOME, color="primary"), Text("名寄帳・課税明細書から読み取り", weight=FontWeight.BOLD, size=16)]),
                        Text("PDFを選択して解析範囲を黒塗り（マスキング）することで、プライバシーを守りつつ物件情報を自動抽出します。", size=13, color="secondary"),
                        Row([
                            ElevatedButton("PDFを選択", icon=Icons.UPLOAD_FILE, on_click=self._open_nayose_picker),
                            self.zoom_slider,
                            self.analyze_btn,
                        ]),
                        Row([self.masking_container], scroll=ScrollMode.AUTO),
                        self.candidate_area,
                    ], spacing=15),
                )
            ),

            # 入力・編集セクション
            Card(
                content=Container(
                    padding=20,
                    content=Column([
                        Row([
                            Icon(Icons.EDIT, color="primary"), 
                            Text("物件情報の入力", weight=FontWeight.BOLD, size=16),
                            Container(expand=True),
                            self.add_form_btn
                        ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                        self.forms_container,
                        Divider(),
                        Row([self.register_btn], alignment=MainAxisAlignment.END),
                    ], spacing=15),
                )
            ),

            Divider(),
            Text("登録済み不動産一覧", size=18, weight=FontWeight.BOLD),
            self.asset_list,
        ]

    def did_mount(self) -> None:
        """マウント時にピッカー登録とデータロードを行う"""
        self.page.overlay.extend([self.nayose_picker, self.registry_picker])
        self._load_assets()
        if not self.input_forms:
            self._add_input_form()

    # --- データ操作 (CRUD) ---

    def _load_assets(self) -> None:
        """DBから現在の物件リストを取得してカード表示"""
        self.asset_list.controls.clear()
        try:
            assets = get_real_estates_by_case(self.case_id)
            if not assets:
                self.asset_list.controls.append(Text("登録された不動産はありません", color="secondary", italic=True))
            else:
                for asset in assets:
                    self.asset_list.controls.append(self._create_asset_card(asset))
        except Exception as e:
            self._show_snack(f"データ取得エラー: {e}", "error")
        self.update()

    def _add_input_form(self, initial_data: Optional[Dict] = None, asset_id: Optional[int] = None, focus: bool = False) -> None:
        """動的な入力フォーム行を追加"""
        initial_data = initial_data or {}
        
        # フィールド定義
        c_type = Dropdown(
            label="種類 *", width=130, dense=True,
            options=[
                dropdown.Option("Land", "土地"),
                dropdown.Option("Building", "建物"),
                dropdown.Option("Condo", "区分所有"),
            ],
            value=initial_data.get("type", "Land")
        )
        c_loc = TextField(label="所在", value=initial_data.get("location", ""), expand=True, dense=True, autofocus=focus)
        c_share = TextField(label="持分", value=initial_data.get("share", "1/1"), width=80, dense=True)
        c_lot = TextField(label="地番/家屋番号", value=initial_data.get("lot_number", ""), width=150, dense=True)
        c_cat = TextField(label="地目/種類", value=initial_data.get("category", ""), width=120, dense=True)
        c_area = TextField(label="地積/面積", value=str(initial_data.get("area", "")), width=110, dense=True, suffix_text="㎡")
        c_struc = TextField(label="構造", value=initial_data.get("structure", ""), width=250, dense=True)

        form_id = asset_id
        
        def delete_form(_):
            # フォームの削除
            for i, f in enumerate(self.input_forms):
                if f["view"] == row_container:
                    self.input_forms.pop(i)
                    self.forms_container.controls.remove(row_container)
                    break
            if not self.input_forms:
                self._add_input_form()
            self._update_save_button_label()
            self.update()

        row_container = Container(
            padding=15, border=border.all(1, "outlineVariant"), border_radius=8, bgcolor="surface",
            content=Column([
                Row([
                    Text(f"ID: {form_id}" if form_id else "新規入力", weight=FontWeight.BOLD, color="primary"),
                    Container(expand=True),
                    IconButton(Icons.DELETE_OUTLINE, icon_color="error", on_click=delete_form, tooltip="削除")
                ]),
                Row([c_type, c_loc, c_share]),
                Row([c_lot, c_cat, c_area, c_struc]),
            ], spacing=10)
        )

        self.input_forms.append({
            "id": form_id,
            "controls": {
                "type": c_type, "location": c_loc, "share": c_share, "lot_number": c_lot,
                "category": c_cat, "area": c_area, "structure": c_struc
            },
            "view": row_container
        })
        self.forms_container.controls.append(row_container)
        self._update_save_button_label()
        self.update()

    def _on_register_click(self, e) -> None:
        """入力された全フォームを保存"""
        success_count = 0
        for form in self.input_forms:
            ctrls = form["controls"]
            asset_id = form["id"]
            
            if not ctrls["location"].value:
                ctrls["location"].error_text = "所在は必須です"
                ctrls["location"].update()
                continue

            # 面積の数値クレンジング
            area_val = None
            try:
                raw_area = ctrls["area"].value.replace(" ", "").replace("　", "").replace(",", "")
                area_val = float(raw_area) if raw_area else 0.0
            except: pass

            data = {
                "property_type": ctrls["type"].value,
                "location": ctrls["location"].value,
                "ownership_share": ctrls["share"].value,
                "lot_number": ctrls["lot_number"].value,
                "land_category": ctrls["category"].value,
                "land_area": area_val,
                "house_number": ctrls["lot_number"].value,
                "structure": ctrls["structure"].value,
                "floor_area": ctrls["area"].value,
            }

            if asset_id:
                if update_real_estate(asset_id, **data): success_count += 1
            else:
                if add_real_estate(self.case_id, **data): success_count += 1

        self._show_snack(f"{success_count}件の物件情報を保存しました", "success")
        self.input_forms.clear()
        self.forms_container.controls.clear()
        self._add_input_form()
        self._load_assets()

    def _create_asset_card(self, asset) -> Card:
        """登録済み不動産のカード表示"""
        img_src = asset.registry_image_path if asset.registry_image_path and os.path.exists(asset.registry_image_path) else ""
        
        type_labels = {"Land": "土地", "Building": "建物", "Condo": "区分所有"}
        
        return Card(
            content=Container(
                padding=15,
                content=Column([
                    Row([
                        Container(
                            content=Text(type_labels.get(asset.property_type, "不明"), size=11, color="onPrimary"),
                            bgcolor="primary", padding=padding.symmetric(horizontal=8, vertical=2), border_radius=4
                        ),
                        Text(asset.location, weight=FontWeight.BOLD, size=16, expand=True),
                        IconButton(Icons.EDIT, icon_color="primary", on_click=lambda _: self._start_edit_asset(asset)),
                        IconButton(Icons.DELETE, icon_color="error", on_click=lambda _: self._on_delete_asset(asset)),
                    ]),
                    Text(f"地番/家屋番号: {asset.lot_number or asset.house_number} | 面積: {asset.land_area or asset.floor_area}㎡ | 持分: {asset.ownership_share}", size=13, color="secondary"),
                    Divider(),
                    Row([
                        Column([
                            ElevatedButton("登記PDFを登録", icon=Icons.FILE_UPLOAD, on_click=lambda _: self._open_registry_picker(asset.id)),
                            Text(f"PDF: {'済' if asset.registry_pdf_path else '未'}", size=11),
                        ], expand=True),
                        Container(
                            width=180, height=120, bgcolor="surfaceVariant", border_radius=5,
                            content=Image(src=img_src, fit="contain") if img_src else Icon(Icons.IMAGE_NOT_SUPPORTED, color="outline"),
                            on_click=lambda _: self._open_image_preview(img_src) if img_src else None
                        )
                    ])
                ])
            )
        )

    def _start_edit_asset(self, asset) -> None:
        """編集モードの開始"""
        self.input_forms.clear()
        self.forms_container.controls.clear()
        initial = {
            "type": asset.property_type, "location": asset.location, "share": asset.ownership_share,
            "lot_number": asset.lot_number or asset.house_number, "category": asset.land_category,
            "area": asset.land_area or asset.floor_area, "structure": asset.structure
        }
        self._add_input_form(initial, asset_id=asset.id, focus=True)
        self._show_snack("編集モードを開始しました", "info")

    def _on_delete_asset(self, asset) -> None:
        if delete_real_estate(asset.id):
            self._show_snack(f"削除しました: {asset.location}", "success")
            self._load_assets()

    # --- AI・名寄帳解析ロジック (新機能統合) ---

    def _open_nayose_picker(self, e) -> None:
        """名寄帳PDF選択ダイアログ（案件フォルダを初期表示）"""
        init_path = get_case_folder_path(self.case_id)
        self.nayose_picker.pick_files(
            allow_multiple=False, 
            allowed_extensions=["pdf"], 
            initial_directory=init_path
        )

    def _on_nayose_picked(self, e: FilePickerResultEvent) -> None:
        if not e.files: return
        self._show_snack("名寄帳を読み込んでいます...", "info")
        
        def process():
            try:
                images = pdf_service.convert_pdf_to_images_sync(e.files[0].path)
                page_img = images[0]
                self.nayose_image_base64 = page_img.base64_image
                self.nayose_img_width, self.nayose_img_height = page_img.width, page_img.height
                
                # 表示の初期化
                self.mask_rects.clear()
                self.masking_stack.controls.clear()
                
                img_view = Image(src_base64=self.nayose_image_base64, width=self.current_display_width)
                gesture = GestureDetector(
                    content=img_view,
                    on_pan_start=self._on_mask_pan_start,
                    on_pan_update=self._on_mask_pan_update,
                    on_pan_end=self._on_mask_pan_end,
                )
                self.masking_stack.controls.append(gesture)
                
                self.masking_container.width = self.current_display_width
                self.masking_container.height = self.current_display_width * (self.nayose_img_height / self.nayose_img_width)
                self.masking_container.visible = True
                self.analyze_btn.visible = True
                self.zoom_slider.disabled = False
                self.update()
            except Exception as ex:
                self._show_snack(f"読込エラー: {ex}", "error")

        self.page.run_thread(process)

    def _on_mask_pan_start(self, e: DragStartEvent) -> None:
        self.drag_start_x, self.drag_start_y = e.local_x, e.local_y
        self.current_mask = Container(bgcolor=Colors.BLACK, opacity=0.7, left=e.local_x, top=e.local_y, width=0, height=0)
        self.masking_stack.controls.append(self.current_mask)
        self.update()

    def _on_mask_pan_update(self, e: DragUpdateEvent) -> None:
        if not self.current_mask: return
        self.current_mask.left = min(self.drag_start_x, e.local_x)
        self.current_mask.top = min(self.drag_start_y, e.local_y)
        self.current_mask.width = abs(e.local_x - self.drag_start_x)
        self.current_mask.height = abs(e.local_y - self.drag_start_y)
        self.current_mask.update()

    def _on_mask_pan_end(self, e) -> None:
        if self.current_mask:
            self.mask_rects.append((self.current_mask.left, self.current_mask.top, self.current_mask.width, self.current_mask.height))
            self.current_mask = None

    def _run_ai_analysis(self, e) -> None:
        if not self.nayose_image_base64: return
        self.analyze_btn.disabled = True
        self.candidate_area.visible = False
        self.update()
        self._show_snack("AI解析を実行中...", "info")

        def task():
            try:
                # マスキング済みの画像を生成してAIへ
                masked_b64 = apply_masking_to_image(
                    self.nayose_image_base64, self.mask_rects, self.nayose_img_width, self.nayose_img_height,
                    self.current_display_width, self.masking_container.height
                )
                # AIサービス呼び出し (カスタムプロンプト版)
                result = ai_service.analyze_real_estate_document_sync(masked_b64)
                
                # 物件データを一時保持
                self.ai_properties_buffer = result.get("properties", [])
                
                # 自治体候補の表示
                self._render_candidates(result.get("candidate_locations", []))
            except Exception as ex:
                self._show_snack(f"AI解析エラー: {ex}", "error")
            finally:
                self.analyze_btn.disabled = False
                self.update()

        self.page.run_thread(task)

    def _render_candidates(self, locations: List[Dict[str, str]]) -> None:
        """AIが提案した自治体候補をチップとして表示"""
        self.location_candidates_row.controls.clear()
        if not locations:
            locations = [{"prefecture": "", "municipality": "不明（手動入力してください）"}]

        for loc in locations:
            pref = loc.get("prefecture", "")
            mun = loc.get("municipality", "")
            full = f"{pref}{mun}".strip()
            
            self.location_candidates_row.controls.append(
                Chip(
                    label=Text(full),
                    leading=Icon(Icons.LOCATION_CITY, size=16),
                    on_select=lambda e, p=pref, m=mun: self._apply_ai_with_location(p, m),
                    bgcolor="primaryContainer",
                )
            )
        self.candidate_area.visible = True
        self.update()

    def _apply_ai_with_location(self, pref: str, mun: str) -> None:
        """選択された自治体を住所の接頭辞として全物件に適用して展開"""
        if not self.ai_properties_buffer: return
        
        # 既存の空フォームがあれば消去
        if len(self.input_forms) == 1 and not self.input_forms[0]["controls"]["location"].value:
            self.input_forms.clear()
            self.forms_container.controls.clear()

        prefix = f"{pref}{mun}"
        for p in self.ai_properties_buffer:
            data = {
                "type": p.get("type", "Land"),
                "location": f"{prefix}{p.get('location', '')}",
                "lot_number": p.get("lot_number", ""),
                "category": p.get("category", ""),
                "area": p.get("area", ""),
                "structure": p.get("structure", ""),
                "share": p.get("share", "1/1"),
            }
            self._add_input_form(data)

        self.ai_properties_buffer = []
        self.candidate_area.visible = False
        self._show_snack(f"{prefix} の物件として展開しました", "success")

    # --- 共通ユーティリティ・プレビュー ---

    def _show_snack(self, msg: str, mode: str = "info") -> None:
        color = "primary"
        if mode == "error": color = "error"
        if mode == "success": color = Colors.GREEN_600
        self.page.open(SnackBar(Text(msg), bgcolor=color))

    def _update_save_button_label(self) -> None:
        has_edit = any(f["id"] is not None for f in self.input_forms)
        self.register_btn.text = "不動産情報を修正・更新" if has_edit else "不動産情報を登録"

    def _on_zoom_change(self, e) -> None:
        self.current_display_width = float(e.control.value)
        if self.masking_stack.controls:
            self.masking_stack.controls[0].content.width = self.current_display_width
        self.update()

    def _open_registry_picker(self, asset_id: int) -> None:
        """登記PDF選択ダイアログ（案件フォルダを初期表示）"""
        self._target_asset_id = asset_id
        init_path = get_case_folder_path(self.case_id)
        self.registry_picker.pick_files(
            allowed_extensions=["pdf"],
            initial_directory=init_path
        )

    def _on_registry_picked(self, e: FilePickerResultEvent) -> None:
        if not e.files or not self._target_asset_id: return
        if save_registry_document(self.case_id, self._target_asset_id, e.files[0].path):
            self._show_snack("登記PDFを保存しました", "success")
            self._load_assets()

    def _open_image_preview(self, path: str) -> None:
        """ディレクトリ内の画像をシリーズで取得するプレビュー機能"""
        try:
            dir_path = Path(path).parent
            # ファイル名の数字でソート
            files = sorted(list(dir_path.glob("registry_page_*.jpg")), 
                          key=lambda x: int(re.search(r'\d+', x.name).group()) if re.search(r'\d+', x.name) else 0)
            self.preview_images = [str(f) for f in files]
            self.preview_page_index = next((i for i, p in enumerate(self.preview_images) if p == path), 0)
            self._update_preview_state()
            self.page.open(self.preview_dialog)
        except Exception as ex:
            self._show_snack(f"プレビューエラー: {ex}", "error")

    def _update_preview_state(self) -> None:
        if not self.preview_images: return
        self.preview_image_control.src = self.preview_images[self.preview_page_index]
        self.preview_page_text.value = f"{self.preview_page_index + 1} / {len(self.preview_images)}"
        self.preview_prev_btn.disabled = self.preview_page_index == 0
        self.preview_next_btn.disabled = self.preview_page_index == len(self.preview_images) - 1
        self.update()

    def _prev_preview_page(self, _) -> None:
        self.preview_page_index -= 1
        self._update_preview_state()

    def _next_preview_page(self, _) -> None:
        self.preview_page_index += 1
        self._update_preview_state()

    def _on_preview_scale_change(self, e) -> None:
        self.preview_image_control.scale = float(e.control.value)
        self.preview_image_control.update()

    def _close_preview_dialog(self, _) -> None:
        self.page.close(self.preview_dialog)