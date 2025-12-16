# src/views/real_estate_edit.py
import os
import glob
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
)

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
    """不動産情報・登記情報管理画面"""

    def __init__(self, page: Page, case_id: int):
        super().__init__(expand=True, scroll="auto")
        self.page = page
        self.case_id = case_id

        # --- 入力フォーム管理 ---
        self.input_forms: List[Dict[str, Any]] = []
        self.forms_container = Column(spacing=15)

        # 登録ボタン
        self.register_btn = ElevatedButton(
            "不動産情報を登録",
            icon=Icons.SAVE,
            bgcolor=Colors.BLUE_600,
            color=Colors.WHITE,
            on_click=self._on_register_click,
            style=ButtonStyle(padding=20),
        )
        
        # フォーム追加ボタン
        self.add_form_btn = ElevatedButton(
            "入力欄を追加",
            icon=Icons.ADD,
            on_click=lambda e: self._add_input_form(),
            bgcolor=Colors.GREEN_600,
            color=Colors.WHITE
        )

        # --- 登録済みリスト ---
        self.asset_list = Column(spacing=10)

        # --- 名寄帳・AI解析ツール ---
        self.registry_picker = FilePicker(on_result=self._on_registry_picked)
        self.nayose_picker = FilePicker(on_result=self._on_nayose_picked)
        
        # 名寄帳読み取り用 State
        self.nayose_image_base64: Optional[str] = None
        self.nayose_img_width = 0
        self.nayose_img_height = 0
        self.current_display_width = 800.0
        
        self.mask_rects = []
        self.current_mask = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # ズームスライダー (名寄帳用)
        self.zoom_slider = Slider(
            min=600,
            max=1600,
            divisions=10,
            value=self.current_display_width,
            label="表示サイズ: {value}px",
            width=300,
            on_change=self._on_zoom_change,
            disabled=True,
        )

        # マスキングUI
        self.masking_stack = Stack()
        self.masking_container = Container(
            content=self.masking_stack,
            width=self.current_display_width,
            height=400, # 仮
            bgcolor=Colors.GREY_200,
            visible=False,
            border=border.all(1, Colors.GREY_400),
        )
        
        self.analyze_btn = ElevatedButton(
            "マスキングしてAI解析＆自動展開",
            icon=Icons.ANALYTICS,
            on_click=self._run_ai_analysis,
            bgcolor=Colors.PURPLE_600,
            color=Colors.WHITE,
            visible=False
        )

        # --- 登記情報プレビュー用 State ---
        self.preview_images: List[str] = []
        self.preview_page_index: int = 0
        self.preview_scale: float = 1.0

        # --- 画像プレビューダイアログ設定 ---
        self.preview_image_control = Image(src="", fit="contain", width=900, height=600)
        
        # ズームスライダー
        self.preview_scale_slider = Slider(
            min=0.5, max=3.0, value=1.0, 
            label="倍率: {value}", width=300,
            on_change=self._on_preview_scale_change
        )
        
        # ページ切り替えボタン
        self.preview_prev_btn = IconButton(icon=Icons.ARROW_BACK, on_click=self._prev_preview_page, disabled=True)
        self.preview_next_btn = IconButton(icon=Icons.ARROW_FORWARD, on_click=self._next_preview_page, disabled=True)
        self.preview_page_text = Text("0 / 0", size=16, weight=FontWeight.BOLD)

        self.preview_dialog = AlertDialog(
            modal=True,
            title=Text("登記情報プレビュー"),
            content=Column([
                # 画像表示エリア
                Container(
                    content=self.preview_image_control,
                    width=950,
                    height=650,
                    alignment=alignment.center,
                    clip_behavior="hardEdge", # 拡大時はみ出し防止
                    bgcolor=Colors.BLACK12,
                ),
                # コントロールエリア
                Row([
                    self.preview_prev_btn,
                    self.preview_page_text,
                    self.preview_next_btn,
                    Container(width=20),
                    Text("ズーム:"),
                    self.preview_scale_slider,
                ], alignment=MainAxisAlignment.CENTER)
            ], tight=True),
            actions=[
                TextButton("閉じる", on_click=self._close_preview_dialog)
            ],
            actions_alignment=MainAxisAlignment.CENTER,
        )

        # --- レイアウト構築 ---
        self.controls = [
            Text("🏠 不動産・登記情報管理", size=24, weight=FontWeight.BOLD),
            Divider(),
            
            # --- 1. AI読み取りエリア (一番上に配置) ---
            Card(
                content=Container(
                    content=Column([
                        Row([Icon(Icons.AUTO_AWESOME, color=Colors.PURPLE), Text("名寄帳・課税明細書から読み取り", weight=FontWeight.BOLD, size=16)]),
                        Text("1. PDFを選択 → 2. 画像サイズを調整 → 3. 不要部分を黒塗り(ドラッグ) → 4. AI解析 → 自動で下のフォームに追加されます", size=12, color=Colors.GREY_700),
                        
                        Row([
                            ElevatedButton(
                                "名寄帳PDFを選択",
                                icon=Icons.UPLOAD_FILE,
                                on_click=self._open_nayose_picker,
                                bgcolor=Colors.PURPLE_50,
                                color=Colors.PURPLE_900,
                            ),
                            Text("表示サイズ:"),
                            self.zoom_slider,
                            self.analyze_btn,
                        ], vertical_alignment=CrossAxisAlignment.CENTER),
                        
                        # 画像表示エリア
                        Row([
                            self.masking_container
                        ], scroll=ScrollMode.AUTO),
                        
                    ], spacing=15),
                    padding=20,
                    border=border.all(1, Colors.PURPLE_100),
                ),
                elevation=0,
            ),

            Divider(height=30, color=Colors.TRANSPARENT),

            # --- 2. フォームエリア ---
            Card(
                content=Container(
                    content=Column([
                        Row([
                            Icon(Icons.EDIT, color=Colors.BLUE), 
                            Text("不動産情報の登録・編集", weight=FontWeight.BOLD, size=16),
                            Container(expand=True),
                            self.add_form_btn
                        ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                        
                        # 動的フォームエリア
                        self.forms_container,
                        
                        Divider(),
                        Row([self.register_btn], alignment=MainAxisAlignment.END),
                    ], spacing=15),
                    padding=20,
                ),
                elevation=2,
            ),

            Divider(),
            Text("登録済み不動産一覧", size=16, weight=FontWeight.BOLD),
            self.asset_list,
        ]

        self._target_asset_id = None

    def did_mount(self):
        # PickerをOverlayに追加
        if self.registry_picker not in self.page.overlay:
            self.page.overlay.append(self.registry_picker)
        if self.nayose_picker not in self.page.overlay:
            self.page.overlay.append(self.nayose_picker)
            
        self._load_assets()
        # 初期状態で1つフォームを表示
        self._add_input_form()

    # --- 画像プレビュー関連メソッド ---

    def _open_image_preview(self, first_image_path: str):
        """画像プレビューダイアログを開く"""
        if not first_image_path or not os.path.exists(first_image_path):
            return
        
        # ディレクトリ内の同シリーズ画像を取得する (registry_page_*.jpg)
        dir_path = Path(first_image_path).parent
        # ファイル名パターン: registry_page_{num}.jpg
        # globで取得し、ページ番号でソートする
        files = list(dir_path.glob("registry_page_*.jpg"))
        
        if not files:
            files = [Path(first_image_path)]
            
        # ページ番号順にソート (ファイル名末尾の数字を利用)
        def get_page_num(p: Path):
            try:
                # "registry_page_10.jpg" -> "10"
                return int(p.stem.split("_")[-1])
            except ValueError:
                return 0
        
        files.sort(key=get_page_num)
        
        self.preview_images = [str(f) for f in files]
        self.preview_page_index = 0
        self.preview_scale = 1.0
        
        # 初期表示更新
        self._update_preview_content()
        self.preview_scale_slider.value = 1.0
        
        self.page.open(self.preview_dialog)
        self.page.update()

    def _update_preview_content(self):
        """プレビューダイアログの内容を現在の状態に合わせて更新"""
        if not self.preview_images:
            return

        current_src = self.preview_images[self.preview_page_index]
        total = len(self.preview_images)
        
        self.preview_image_control.src = current_src
        self.preview_image_control.scale = self.preview_scale
        
        self.preview_page_text.value = f"{self.preview_page_index + 1} / {total}"
        
        self.preview_prev_btn.disabled = (self.preview_page_index == 0)
        self.preview_next_btn.disabled = (self.preview_page_index == total - 1)
        
        # コントロールの更新 (ダイアログ表示中はこれで反映される)
        self.preview_image_control.update()
        self.preview_page_text.update()
        self.preview_prev_btn.update()
        self.preview_next_btn.update()

    def _prev_preview_page(self, e):
        if self.preview_page_index > 0:
            self.preview_page_index -= 1
            self._update_preview_content()

    def _next_preview_page(self, e):
        if self.preview_page_index < len(self.preview_images) - 1:
            self.preview_page_index += 1
            self._update_preview_content()

    def _on_preview_scale_change(self, e):
        """プレビュー画像のズーム変更"""
        self.preview_scale = float(e.control.value)
        self.preview_image_control.scale = self.preview_scale
        self.preview_image_control.update()

    def _close_preview_dialog(self, e):
        self.page.close(self.preview_dialog)
        self.page.update()

    # --- フォーム動的生成ロジック ---

    def _add_input_form(self, initial_data: Optional[Dict] = None, asset_id: Optional[int] = None, focus_location: bool = False):
        """
        入力フォーム行を追加する
        :param initial_data: 初期値辞書 {'type', 'location', ...}
        :param asset_id: 編集モード時のID (Noneなら新規)
        :param focus_location: 追加時に所在フィールドにフォーカスを当てるか
        """
        initial_data = initial_data or {}
        
        # 共通スタイル
        input_style = TextStyle(color=Colors.BLACK)
        label_style = TextStyle(color=Colors.BLUE_GREY_700)

        # コントロール作成
        c_type = Dropdown(
            label="種類 *",
            width=120,
            options=[
                dropdown.Option("Land", "土地"),
                dropdown.Option("Building", "建物"),
                dropdown.Option("Condo", "区分所有"),
            ],
            value=initial_data.get("type", "Land"),
            dense=True,
            text_style=input_style,
            label_style=label_style,
        )
        c_loc = TextField(
            label="所在", 
            value=initial_data.get("location", ""), 
            expand=True, 
            dense=True,
            text_style=input_style,
            label_style=label_style,
            autofocus=focus_location, # フォーカス制御
        )
        c_share = TextField(
            label="持分", 
            value=initial_data.get("share", ""), 
            width=80, 
            dense=True,
            text_style=input_style,
            label_style=label_style,
        )
        
        c_lot = TextField(
            label="地番/家屋番号", 
            value=initial_data.get("lot_number", ""), 
            width=150, 
            dense=True,
            text_style=input_style,
            label_style=label_style,
        )
        c_cat = TextField(
            label="地目/種類", 
            value=initial_data.get("category", ""), 
            width=120, 
            dense=True,
            text_style=input_style,
            label_style=label_style,
        )
        c_area = TextField(
            label="地積/床面積", 
            value=str(initial_data.get("area", "")), 
            width=100, 
            dense=True, 
            suffix_text="㎡",
            text_style=input_style,
            label_style=label_style,
            suffix_style=input_style,
        )
        c_struc = TextField(
            label="構造", 
            value=initial_data.get("structure", ""), 
            width=200, 
            dense=True,
            text_style=input_style,
            label_style=label_style,
        )

        # フォーム管理用辞書
        form_data = {
            "id": asset_id, # DB上のID (新規ならNone)
            "controls": {
                "type": c_type,
                "location": c_loc,
                "share": c_share,
                "lot_number": c_lot,
                "category": c_cat,
                "area": c_area,
                "structure": c_struc,
            },
            "view": None # コンテナ参照（後でセット）
        }

        # 削除ボタン
        def delete_this_form(e):
            if form_data in self.input_forms:
                self.input_forms.remove(form_data)
                self.forms_container.controls.remove(form_data["view"])
                
                # 全て消えたら空のフォームを1つ追加
                if not self.input_forms:
                    self._add_input_form()
                
                self._update_register_button_label()
        
            self.update()

        delete_btn = IconButton(
            icon=Icons.DELETE_OUTLINE, 
            icon_color=Colors.RED, 
            on_click=delete_this_form,
            tooltip="この入力を削除"
        )

        # ラベル（新規 or 編集）
        label_text = f"編集 (ID: {asset_id})" if asset_id else "新規登録"
        label_color = Colors.ORANGE if asset_id else Colors.BLUE

        # 行コンテナ
        row_container = Container(
            content=Column([
                Row([
                    Icon(Icons.CIRCLE, size=10, color=label_color),
                    Text(label_text, size=12, color=label_color, weight=FontWeight.BOLD),
                    Container(expand=True),
                    delete_btn
                ], spacing=5, alignment=MainAxisAlignment.START),
                Row([c_type, c_loc, c_share]),
                Row([c_lot, c_cat, c_area, c_struc]),
            ], spacing=5),
            padding=10,
            border=border.all(1, Colors.GREY_300),
            border_radius=5,
            bgcolor=Colors.WHITE,
        )
        
        form_data["view"] = row_container
        
        self.input_forms.append(form_data)
        self.forms_container.controls.append(row_container)
        
        self._update_register_button_label()
        self.update()

    def _update_register_button_label(self):
        """登録ボタンのラベルを状態に応じて更新"""
        has_edit = any(f["id"] is not None for f in self.input_forms)
        if has_edit:
            self.register_btn.text = "不動産情報を修正・登録"
            self.register_btn.icon = Icons.UPDATE
            self.register_btn.bgcolor = Colors.ORANGE_700
        else:
            self.register_btn.text = "不動産情報を登録"
            self.register_btn.icon = Icons.SAVE
            self.register_btn.bgcolor = Colors.BLUE_600
        self.register_btn.update()

    # --- データ操作 (CRUD) ---

    def _load_assets(self):
        self.asset_list.controls.clear()
        assets = get_real_estates_by_case(self.case_id)

        if not assets:
            self.asset_list.controls.append(Text("登録された不動産はありません", color=Colors.GREY))

        for asset in assets:
            self.asset_list.controls.append(self._create_asset_card(asset))

        self.update()

    def _on_register_click(self, e):
        """一括登録・修正ボタン: 全フォームの内容を処理"""
        if not self.input_forms:
            return

        success_count = 0
        error_count = 0

        for form in self.input_forms:
            ctrls = form["controls"]
            asset_id = form["id"]
            
            # バリデーション
            loc_val = ctrls["location"].value
            if not loc_val:
                ctrls["location"].error_text = "必須"
                ctrls["location"].update()
                error_count += 1
                continue

            # 面積の数値変換
            area_str = ctrls["area"].value
            land_area_val = None
            if area_str:
                try:
                    val_str = area_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')).replace(",", "")
                    land_area_val = float(val_str)
                except ValueError:
                    pass 

            # データ構築
            data = {
                "property_type": ctrls["type"].value,
                "location": loc_val,
                "ownership_share": ctrls["share"].value,
                "lot_number": ctrls["lot_number"].value,
                "land_category": ctrls["category"].value,
                "land_area": land_area_val,
                "house_number": ctrls["lot_number"].value, # 建物の場合も同じフィールドを使用
                "structure": ctrls["structure"].value,
                "floor_area": ctrls["area"].value,
            }

            if asset_id:
                # 更新
                if update_real_estate(asset_id, **data):
                    success_count += 1
                else:
                    error_count += 1
            else:
                # 新規登録
                if add_real_estate(self.case_id, **data):
                    success_count += 1
                else:
                    error_count += 1

        # 結果表示
        if error_count == 0:
            self.page.open(SnackBar(Text(f"{success_count}件の処理が完了しました"), bgcolor=Colors.GREEN))
            # フォームクリア
            self.input_forms.clear()
            self.forms_container.controls.clear()
            self._add_input_form() # 空を1つ追加
            self._load_assets()
        else:
            self.page.open(SnackBar(Text(f"成功: {success_count}件, 失敗: {error_count}件。エラー項目を確認してください"), bgcolor=Colors.RED))
            self._load_assets() # 成功分は反映

    def _delete_asset(self, asset_id):
        if delete_real_estate(asset_id):
            self.page.open(SnackBar(Text("削除しました"), bgcolor=Colors.GREEN))
            self._load_assets()

    def _start_edit_asset(self, asset):
        """編集ボタン押下時の処理"""
        # 現在のフォームをクリア
        self.input_forms.clear()
        self.forms_container.controls.clear()
        
        # 編集対象のデータでフォームを作成
        initial_data = {
            "type": asset.property_type,
            "location": asset.location,
            "share": asset.ownership_share,
            "lot_number": asset.lot_number or asset.house_number,
            "category": asset.land_category,
            "area": asset.land_area if asset.property_type == "Land" else asset.floor_area,
            "structure": asset.structure
        }
        
        # 編集開始時は「所在」にフォーカスを当てる
        self._add_input_form(initial_data, asset_id=asset.id, focus_location=True)
        
        # 上部へスクロール
        self.page.open(SnackBar(Text("上部のフォームで編集してください"), bgcolor=Colors.BLUE))

    def _create_asset_card(self, asset):
        img_src = ""
        img_visible = False
        if asset.registry_image_path and os.path.exists(asset.registry_image_path):
            img_src = asset.registry_image_path
            img_visible = True

        type_map = {"Land": "土地", "Building": "建物", "Condo": "区分所有"}
        type_label = type_map.get(asset.property_type, "その他")
        
        details = []
        if asset.lot_number: details.append(f"地番: {asset.lot_number}")
        if asset.house_number: details.append(f"家屋番号: {asset.house_number}")
        if asset.land_category: details.append(f"地目: {asset.land_category}")
        if asset.land_area: details.append(f"地積: {asset.land_area}㎡")
        if asset.structure: details.append(f"構造: {asset.structure}")
        if asset.floor_area: details.append(f"床面積: {asset.floor_area}㎡")
        
        detail_text = " / ".join(details)

        return Card(
            content=Container(
                padding=10,
                content=Column(
                    [
                        Row(
                            [
                                Container(
                                    content=Text(type_label, color=Colors.WHITE, size=12),
                                    bgcolor=Colors.BLUE_GREY,
                                    padding=5,
                                    border_radius=4,
                                ),
                                Text(asset.location, weight=FontWeight.BOLD, size=16, expand=True),
                                Text(f"持分: {asset.ownership_share or '-'}", size=12),
                                # 編集ボタン
                                IconButton(Icons.EDIT, icon_color=Colors.ORANGE, on_click=lambda e: self._start_edit_asset(asset), tooltip="編集"),
                                # 削除ボタン
                                IconButton(Icons.DELETE, icon_color=Colors.RED, on_click=lambda e: self._delete_asset(asset.id), tooltip="削除"),
                            ]
                        ),
                        Text(detail_text, size=12, color=Colors.GREY_700),
                        Divider(),
                        Row(
                            [
                                Column([
                                    ElevatedButton("登記PDF登録/更新", icon=Icons.UPLOAD_FILE, on_click=lambda e: self._open_registry_picker(asset.id)),
                                    Text(f"PDF: {'あり' if asset.registry_pdf_path else 'なし'}", size=12, color=Colors.GREY),
                                ], expand=True),
                                Container(
                                    content=Image(
                                        src=img_src, 
                                        width=200, 
                                        height=140, 
                                        fit="contain", 
                                        border_radius=5
                                    ) if img_visible else Container(content=Text("No Image", color=Colors.GREY), width=200, height=140, bgcolor=Colors.GREY_100, alignment=alignment.center),
                                    border=border.all(1, Colors.GREY_300),
                                    # 画像クリックで拡大表示 (画像がある場合のみ)
                                    on_click=lambda e: self._open_image_preview(img_src) if img_visible else None,
                                    ink=True, # クリックエフェクト
                                ),
                            ],
                            vertical_alignment=CrossAxisAlignment.START,
                        ),
                    ]
                ),
            )
        )

    # --- 登記PDF登録 ---
    def _open_registry_picker(self, asset_id):
        self._target_asset_id = asset_id
        init_path = get_case_folder_path(self.case_id)
        self.registry_picker.pick_files(allow_multiple=False, allowed_extensions=["pdf"], initial_directory=init_path)

    def _on_registry_picked(self, e: FilePickerResultEvent):
        if not e.files or not self._target_asset_id: return
        
        self.page.open(SnackBar(Text("PDFを処理中..."), bgcolor=Colors.BLUE))
        self.page.update()
        
        success = save_registry_document(self.case_id, self._target_asset_id, e.files[0].path)
        
        if success:
            self._load_assets()
            self.page.open(SnackBar(Text("登録しました"), bgcolor=Colors.GREEN))
        else:
            self.page.open(SnackBar(Text("登録に失敗しました"), bgcolor=Colors.RED))

    # --- 名寄帳読み取り & AI解析 ---

    def _open_nayose_picker(self, e):
        init_path = get_case_folder_path(self.case_id)
        self.nayose_picker.pick_files(allow_multiple=False, allowed_extensions=["pdf"], initial_directory=init_path)

    def _on_nayose_picked(self, e: FilePickerResultEvent):
        if not e.files: return
        
        file_path = e.files[0].path
        self.page.open(SnackBar(Text("PDFを読み込み中..."), bgcolor=Colors.BLUE))
        self.page.update()

        def process_pdf():
            try:
                images = pdf_service.convert_pdf_to_images_sync(file_path)
                if not images: raise ValueError("画像変換に失敗しました")
                
                page_img = images[0]
                self.nayose_image_base64 = page_img.base64_image
                self.nayose_img_width = page_img.width
                self.nayose_img_height = page_img.height
                
                self.mask_rects = []
                self.masking_stack.controls.clear()
                
                display_w = self.current_display_width
                
                img_control = Image(
                    src_base64=self.nayose_image_base64,
                    width=display_w,
                    fit="contain"
                )
                gesture = GestureDetector(
                    content=img_control,
                    on_pan_start=self._on_mask_pan_start,
                    on_pan_update=self._on_mask_pan_update,
                    on_pan_end=self._on_mask_pan_end,
                )
                self.masking_stack.controls.append(gesture)
                
                display_height = display_w * (self.nayose_img_height / self.nayose_img_width)
                self.masking_container.width = display_w
                self.masking_container.height = display_height
                self.masking_container.visible = True
                self.analyze_btn.visible = True
                self.zoom_slider.disabled = False
                
                self.update()
                self.page.open(SnackBar(Text("画像を読み込みました。不要箇所をドラッグして黒塗りしてください。"), bgcolor=Colors.GREEN))

            except Exception as ex:
                self.page.open(SnackBar(Text(f"エラー: {ex}"), bgcolor=Colors.RED))

        self.page.run_thread(process_pdf)

    def _on_zoom_change(self, e):
        if not self.nayose_image_base64: return
        
        new_width = float(e.control.value)
        old_width = self.current_display_width
        
        if old_width == 0: return
        
        ratio = new_width / old_width
        self.current_display_width = new_width
        
        new_height = new_width * (self.nayose_img_height / self.nayose_img_width)
        
        self.masking_container.width = new_width
        self.masking_container.height = new_height
        
        if self.masking_stack.controls:
            gesture = self.masking_stack.controls[0]
            if hasattr(gesture, "content") and isinstance(gesture.content, Image):
                gesture.content.width = new_width
        
        new_mask_rects = []
        for i in range(1, len(self.masking_stack.controls)):
            mask = self.masking_stack.controls[i]
            mask.left *= ratio
            mask.top *= ratio
            mask.width *= ratio
            mask.height *= ratio
        
        for rect in self.mask_rects:
            new_mask_rects.append((
                rect[0] * ratio,
                rect[1] * ratio,
                rect[2] * ratio,
                rect[3] * ratio
            ))
        self.mask_rects = new_mask_rects
        
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
        rect = (self.current_mask.left, self.current_mask.top, self.current_mask.width, self.current_mask.height)
        if rect[2] > 5 and rect[3] > 5:
            self.mask_rects.append(rect)
        else:
            self.masking_stack.controls.remove(self.current_mask)
            self.masking_stack.update()
        self.current_mask = None

    def _run_ai_analysis(self, e):
        if not self.nayose_image_base64: return
        
        self.page.open(SnackBar(Text("AI解析中..."), bgcolor=Colors.BLUE))
        self.analyze_btn.disabled = True
        self.update()

        def execute():
            try:
                masked_b64 = apply_masking_to_image(
                    self.nayose_image_base64,
                    self.mask_rects,
                    self.nayose_img_width,
                    self.nayose_img_height,
                    display_width=self.current_display_width,
                    display_height=self.masking_container.height
                )
                results = ai_service.analyze_real_estate_document_sync(masked_b64)
                self._expand_ai_results_to_forms(results)
                self.page.open(SnackBar(Text(f"解析完了: {len(results)}件をフォームに展開しました"), bgcolor=Colors.GREEN))
            except Exception as ex:
                self.page.open(SnackBar(Text(f"解析エラー: {ex}"), bgcolor=Colors.RED))
            finally:
                self.analyze_btn.disabled = False
                self.update()

        self.page.run_thread(execute)

    def _expand_ai_results_to_forms(self, results: List[Dict[str, Any]]):
        """AI解析結果をフォームに自動展開する"""
        if not results:
            return

        # ヘルパー: 空白除去
        def clean_text(text: Any) -> str:
            if text is None: return ""
            return str(text).replace(" ", "").replace("　", "")

        # 既存フォームが1つだけで、かつ未入力であればクリアしてから展開する
        is_empty_form = False
        if len(self.input_forms) == 1:
            ctrls = self.input_forms[0]["controls"]
            if not ctrls["location"].value:
                is_empty_form = True
        
        if is_empty_form:
            self.input_forms.clear()
            self.forms_container.controls.clear()

        # 結果をフォームに追加
        for item in results:
            data = {
                "type": item.get("type", "Land"),
                "location": clean_text(item.get("location")),
                "lot_number": clean_text(item.get("lot_number")),
                "category": clean_text(item.get("category")),
                "area": clean_text(item.get("area")),
                "structure": clean_text(item.get("structure")),
                "share": clean_text(item.get("share")),
            }
            self._add_input_form(initial_data=data)
        
        self.update()