# src/views/real_estate_edit.py
import os

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
    Image,
    Page,
    Row,
    SnackBar,
    Text,
    TextField,
    alignment,
    border,
    dropdown,
)

from src.services.real_estate_service import (
    add_real_estate,
    delete_real_estate,
    get_real_estates_by_case,
    save_registry_document,
)


class RealEstateEditView(Column):
    """不動産情報・登記情報管理画面"""

    def __init__(self, page: Page, case_id: int):
        super().__init__(expand=True, scroll="auto")
        self.page = page
        self.case_id = case_id

        # --- UI Components ---
        self.type_dropdown = Dropdown(
            label="種類",
            width=150,
            options=[
                dropdown.Option("Land", "土地"),
                dropdown.Option("Building", "建物"),
                dropdown.Option("Condo", "区分所有"),
            ],
            value="Land",
        )
        self.location_field = TextField(label="所在 (例: 東京都千代田区...)", expand=True)

        self.asset_list = Column(spacing=10)

        self.file_picker = FilePicker(on_result=self._on_file_picked)
        # Note: did_mountでoverlayに追加することを推奨

        # --- Layout ---
        self.controls = [
            Text("🏠 不動産・登記情報管理", size=24, weight=FontWeight.BOLD),
            Divider(),
            # 新規登録エリア
            Card(
                content=Container(
                    content=Column(
                        [
                            Text("新規不動産追加", weight=FontWeight.BOLD),
                            Row(
                                [
                                    self.type_dropdown,
                                    self.location_field,
                                    ElevatedButton(
                                        "追加", icon=Icons.ADD, on_click=self._add_asset
                                    ),
                                ]
                            ),
                        ]
                    ),
                    padding=15,
                )
            ),
            Divider(),
            Text("登録済み不動産一覧", size=16, weight=FontWeight.BOLD),
            self.asset_list,
        ]

        # アップロード対象の一時保存用ID
        self._target_asset_id = None

    def did_mount(self):
        if self.file_picker not in self.page.overlay:
            self.page.overlay.append(self.file_picker)
        self._load_assets()

    def _load_assets(self):
        self.asset_list.controls.clear()
        assets = get_real_estates_by_case(self.case_id)

        if not assets:
            self.asset_list.controls.append(Text("登録された不動産はありません"))

        for asset in assets:
            self.asset_list.controls.append(self._create_asset_card(asset))

        self.update()

    def _create_asset_card(self, asset):
        # 画像パスの確認
        img_src = ""
        img_visible = False
        if asset.registry_image_path and os.path.exists(asset.registry_image_path):
            img_src = asset.registry_image_path
            img_visible = True

        type_map = {"Land": "土地", "Building": "建物", "Condo": "区分所有"}

        return Card(
            content=Container(
                padding=10,
                content=Column(
                    [
                        Row(
                            [
                                Container(
                                    content=Text(
                                        type_map.get(asset.property_type, "その他"),
                                        color=Colors.WHITE,
                                        size=12,
                                    ),
                                    bgcolor=Colors.BLUE_GREY,
                                    padding=5,
                                    border_radius=4,
                                ),
                                Text(asset.location, weight=FontWeight.BOLD, size=16, expand=True),
                                IconButton(
                                    Icons.DELETE,
                                    icon_color=Colors.RED,
                                    on_click=lambda e: self._delete_asset(asset.id),
                                ),
                            ]
                        ),
                        Divider(),
                        Row(
                            [
                                # 左側：詳細情報（将来的にフィールド追加）
                                Column(
                                    [
                                        Text(f"ID: {asset.id}"),
                                        ElevatedButton(
                                            "登記PDF登録/更新",
                                            icon=Icons.UPLOAD_FILE,
                                            on_click=lambda e: self._open_picker(asset.id),
                                        ),
                                        Text(
                                            f"PDF: {'あり' if asset.registry_pdf_path else 'なし'}",
                                            size=12,
                                            color=Colors.GREY,
                                        ),
                                    ],
                                    expand=True,
                                ),
                                # 右側：プレビュー画像
                                Container(
                                    content=Image(
                                        src=img_src,
                                        width=200,
                                        height=140,
                                        fit="contain",
                                        border_radius=5,
                                    )
                                    if img_visible
                                    else Container(
                                        content=Text("No Image", color=Colors.GREY),
                                        width=200,
                                        height=140,
                                        bgcolor=Colors.GREY_100,
                                        alignment=alignment.center,
                                    ),
                                    border=border.all(1, Colors.GREY_300),
                                ),
                            ],
                            alignment="start",
                            vertical_alignment="start",
                        ),
                    ]
                ),
            )
        )

    def _add_asset(self, e):
        if not self.location_field.value:
            self.page.open(SnackBar(Text("所在を入力してください"), bgcolor=Colors.RED))
            return

        add_real_estate(self.case_id, self.type_dropdown.value, self.location_field.value)
        self.location_field.value = ""
        self._load_assets()
        self.page.open(SnackBar(Text("追加しました"), bgcolor=Colors.GREEN))

    def _delete_asset(self, asset_id):
        delete_real_estate(asset_id)
        self._load_assets()

    def _open_picker(self, asset_id):
        self._target_asset_id = asset_id
        self.file_picker.pick_files(allow_multiple=False, allowed_extensions=["pdf"])

    def _on_file_picked(self, e: FilePickerResultEvent):
        if not e.files or not self._target_asset_id:
            return

        file_path = e.files[0].path
        self.page.open(SnackBar(Text("PDFを処理中..."), bgcolor=Colors.BLUE))
        self.page.update()

        success = save_registry_document(self.case_id, self._target_asset_id, file_path)

        if success:
            self._load_assets()
            self.page.open(SnackBar(Text("登記情報を登録しました"), bgcolor=Colors.GREEN))
        else:
            self.page.open(SnackBar(Text("登録に失敗しました"), bgcolor=Colors.RED))
