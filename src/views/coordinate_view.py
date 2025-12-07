# src/views/coordinate_view.py
import os  # 追加
from typing import List, Optional

from flet import (
    ButtonStyle,
    Card,
    Colors,
    Column,
    Container,
    DragEndEvent,
    DragStartEvent,
    DragUpdateEvent,
    ElevatedButton,
    FilePickerResultEvent,
    GestureDetector,
    Icon,
    IconButton,
    Icons,
    Image,
    ListView,
    MainAxisAlignment,
    Page,
    Row,
    ScrollMode,
    SnackBar,
    Stack,
    TapEvent,
    Text,
    TextField,
    alignment,
    border,
)

from src.models.coordinate import Coordinate
from src.services.pdf_service import PageImage, PdfService

TOOL_TEXT = "text"
TOOL_RECT = "rect"
TOOL_CIRCLE = "circle"
TOOL_CHECK = "check"


class CoordinateSelectorView(Column):
    """
    パス直打ち対応版: CoordinateSelectorView
    """

    DISPLAY_WIDTH = 800

    def __init__(self, page: Page):
        super().__init__(expand=True)
        self.page = page
        self.pdf_service = PdfService()

        self.coordinates: List[Coordinate] = []
        self.page_images: List[PageImage] = []
        self.current_page_index: int = 0
        self.current_scale_factor: float = 1.0

        self.current_tool: str = TOOL_TEXT
        self.next_text_value: str = ""

        self.drag_start_x: Optional[float] = None
        self.drag_start_y: Optional[float] = None
        self.temp_rect_control: Optional[Container] = None

        # --- 【追加】デバッグ用：パス直接入力フィールド ---
        self.path_input_field = TextField(
            label="PDFファイルの絶対パスを入力 (/Users/name/.../file.pdf)",
            width=600,
            text_size=12,
            border_color=Colors.BLUE_400,
        )

        self.txt_font_size = TextField(value="11", label="文字サイズ", width=80, text_align="right")
        self.log_view = ListView(expand=True, spacing=5, auto_scroll=True)
        self.image_stack = Stack()
        self.image_wrapper = Container(
            content=self.image_stack,
            alignment=alignment.center,
            bgcolor=Colors.BLACK12,
            border_radius=8,
            padding=10,
        )

        self.btn_prev = IconButton(icon=Icons.ARROW_BACK, on_click=self.on_prev_page, disabled=True)
        self.btn_next = IconButton(
            icon=Icons.ARROW_FORWARD, on_click=self.on_next_page, disabled=True
        )
        self.txt_page_indicator = Text("0 / 0", size=16, weight="bold")

        # --- UI構築 ---
        tools_row = Row(
            controls=[
                self._create_tool_button("テキスト", Icons.TEXT_FIELDS, TOOL_TEXT),
                self._create_tool_button("四角枠", Icons.CROP_SQUARE, TOOL_RECT),
                self._create_tool_button("丸囲み", Icons.CIRCLE_OUTLINED, TOOL_CIRCLE),
                self._create_tool_button("チェック", Icons.CHECK, TOOL_CHECK),
            ],
            alignment=MainAxisAlignment.START,
        )

        presets_row = Row(
            controls=[
                Text("定型文:", size=12, weight="bold"),
                ElevatedButton(
                    "会社名", on_click=lambda _: self._set_preset_text("株式会社サンプル")
                ),
                ElevatedButton(
                    "住所", on_click=lambda _: self._set_preset_text("東京都千代田区1-1")
                ),
                ElevatedButton("電話", on_click=lambda _: self._set_preset_text("03-1234-5678")),
                ElevatedButton(
                    "クリア",
                    on_click=lambda _: self._set_preset_text(""),
                    style=ButtonStyle(color=Colors.GREY),
                ),
            ],
            scroll=ScrollMode.AUTO,
        )

        self.controls = [
            Card(
                content=Container(
                    padding=10,
                    content=Column(
                        controls=[
                            Row(
                                [
                                    Icon(Icons.EDIT_DOCUMENT, color=Colors.PRIMARY),
                                    Text(
                                        "PDF編集・座標ツール (パス直打ち版)", size=20, weight="bold"
                                    ),
                                ]
                            ),
                            # --- 【変更】パス入力エリアを追加 ---
                            Row(
                                controls=[
                                    self.path_input_field,
                                    ElevatedButton(
                                        "読込",
                                        icon=Icons.FILE_OPEN,
                                        on_click=self._load_pdf_direct,  # ダイアログではなく直接読込メソッドへ
                                        bgcolor=Colors.BLUE_600,
                                        color=Colors.WHITE,
                                    ),
                                ]
                            ),
                            # --------------------------------
                            Row(
                                [
                                    self.btn_prev,
                                    self.txt_page_indicator,
                                    self.btn_next,
                                    ElevatedButton(
                                        "全クリア",
                                        icon=Icons.DELETE_FOREVER,
                                        color=Colors.ERROR,
                                        on_click=self.on_clear_click,
                                    ),
                                ],
                                alignment=MainAxisAlignment.SPACE_BETWEEN,
                            ),
                        ],
                    ),
                )
            ),
            Card(
                content=Container(
                    padding=10,
                    content=Column(
                        controls=[
                            Row(
                                controls=[
                                    tools_row,
                                    Container(width=20),
                                    self.txt_font_size,
                                ]
                            ),
                            presets_row,
                        ]
                    ),
                )
            ),
            Row(
                expand=True,
                controls=[
                    Container(
                        content=Column(
                            controls=[self.image_wrapper],
                            scroll=ScrollMode.ALWAYS,
                            alignment=MainAxisAlignment.START,
                            horizontal_alignment="center",
                        ),
                        expand=3,
                        bgcolor="surfaceVariant",
                        border_radius=10,
                        padding=10,
                    ),
                    Container(
                        content=Column(
                            controls=[
                                Row(
                                    controls=[
                                        Text("取得リスト", weight="bold"),
                                        IconButton(
                                            Icons.COPY,
                                            icon_color=Colors.BLUE,
                                            tooltip="コピー",
                                            on_click=self.on_copy_clipboard,
                                        ),
                                    ],
                                    alignment=MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                self.log_view,
                            ]
                        ),
                        expand=1,
                        padding=10,
                        bgcolor="surfaceVariant",
                        border_radius=10,
                    ),
                ],
            ),
        ]

    # --- 【新規】パス直接読込メソッド ---
    async def _load_pdf_direct(self, e):
        """テキストフィールドのパスを使ってPDFを読み込む"""
        path = self.path_input_field.value.strip()

        # 引用符が入っている場合の除去 ("path/to/file" -> path/to/file)
        path = path.replace('"', "").replace("'", "")

        if not path:
            self.page.open(SnackBar(Text("パスを入力してください"), bgcolor=Colors.RED))
            self.page.update()
            return

        if not os.path.exists(path):
            self.page.open(SnackBar(Text(f"ファイルが見つかりません: {path}"), bgcolor=Colors.RED))
            self.page.update()
            return

        self.page.open(SnackBar(Text("PDF変換中..."), bgcolor=Colors.BLUE))
        self.update()

        try:
            # 既存ロジックを再利用
            self.page_images = await self.pdf_service.convert_pdf_to_images(path)

            if not self.page_images:
                raise ValueError("画像を生成できませんでした")

            self.current_page_index = 0
            self.coordinates.clear()
            self.log_view.controls.clear()
            self._update_page_view()

            self.page.open(
                SnackBar(Text(f"読込完了: 全{len(self.page_images)}ページ"), bgcolor=Colors.GREEN)
            )

        except Exception as ex:
            import traceback

            traceback.print_exc()
            self.page.open(SnackBar(Text(f"変換エラー: {ex}"), bgcolor=Colors.RED))
        finally:
            self.update()

    # --- 以下、既存メソッド ---

    def _create_tool_button(self, label: str, icon: Icon, tool_mode: str) -> ElevatedButton:
        def on_click(e):
            self.current_tool = tool_mode
            self.page.open(SnackBar(Text(f"モード変更: {label}"), duration=1000))
            self.update()

        return ElevatedButton(text=label, icon=icon, on_click=on_click)

    def _set_preset_text(self, text: str) -> None:
        self.next_text_value = text
        self.current_tool = TOOL_TEXT
        msg = f"次のテキスト: 「{text}」" if text else "定型文クリア"
        self.page.open(SnackBar(Text(msg), duration=1000))
        self.update()

    # on_file_picked は今回使わないが、エラー防止のため残しておく
    async def on_file_picked(self, e: FilePickerResultEvent) -> None:
        pass

    def on_prev_page(self, e):
        if self.current_page_index > 0:
            self.current_page_index -= 1
            self._update_page_view()

    def on_next_page(self, e):
        if self.current_page_index < len(self.page_images) - 1:
            self.current_page_index += 1
            self._update_page_view()

    def _update_page_view(self) -> None:
        if not self.page_images:
            return
        total = len(self.page_images)
        self.btn_prev.disabled = self.current_page_index == 0
        self.btn_next.disabled = self.current_page_index == total - 1
        self.txt_page_indicator.value = f"{self.current_page_index + 1} / {total}"

        img_info = self.page_images[self.current_page_index]
        display_w = self.DISPLAY_WIDTH
        display_h = display_w * (img_info.height / img_info.width)
        self.current_scale_factor = img_info.width / display_w

        self.image_stack.controls.clear()
        self.image_stack.width = display_w
        self.image_stack.height = display_h

        img_control = Image(
            src=img_info.path, width=display_w, height=display_h, fit="fill", gapless_playback=True
        )
        gesture = GestureDetector(
            content=img_control,
            on_tap_down=self.on_image_tap_down,
            on_pan_start=self.on_pan_start,
            on_pan_update=self.on_pan_update,
            on_pan_end=self.on_pan_end,
        )
        self.image_stack.controls.append(gesture)
        self._redraw_markers()
        self.update()

    def _redraw_markers(self) -> None:
        current_page = self.current_page_index + 1
        targets = [c for c in self.coordinates if c.page_number == current_page]
        for c in targets:
            self._add_marker_visual(c)

    def on_image_tap_down(self, e: TapEvent):
        if self.current_tool == TOOL_RECT:
            return
        ui_x, ui_y = e.local_x, e.local_y
        real_x = int(ui_x * self.current_scale_factor)
        real_y = int(ui_y * self.current_scale_factor)
        coord = Coordinate(
            id=len(self.coordinates),
            page_number=self.current_page_index + 1,
            type=self.current_tool,
            ui_x=ui_x,
            ui_y=ui_y,
            real_x=real_x,
            real_y=real_y,
            text=self.next_text_value if self.current_tool == TOOL_TEXT else "",
            font_size=int(self.txt_font_size.value) if self.txt_font_size.value.isdigit() else 11,
        )
        self.coordinates.append(coord)
        self._add_log(coord)
        self._add_marker_visual(coord)
        self.update()

    def on_pan_start(self, e: DragStartEvent):
        if self.current_tool != TOOL_RECT:
            return
        self.drag_start_x = e.local_x
        self.drag_start_y = e.local_y
        self.temp_rect_control = Container(
            border=border.all(2, Colors.RED),
            bgcolor=Colors.TRANSPARENT,
            left=self.drag_start_x,
            top=self.drag_start_y,
            width=0,
            height=0,
        )
        self.image_stack.controls.append(self.temp_rect_control)
        self.update()

    def on_pan_update(self, e: DragUpdateEvent):
        if self.current_tool != TOOL_RECT or not self.temp_rect_control:
            return
        curr_x, curr_y = e.local_x, e.local_y
        left = min(self.drag_start_x, curr_x)
        top = min(self.drag_start_y, curr_y)
        width = abs(curr_x - self.drag_start_x)
        height = abs(curr_y - self.drag_start_y)
        self.temp_rect_control.left = left
        self.temp_rect_control.top = top
        self.temp_rect_control.width = width
        self.temp_rect_control.height = height
        self.temp_rect_control.update()

    def on_pan_end(self, e: DragEndEvent):
        if self.current_tool != TOOL_RECT or not self.temp_rect_control:
            return
        ui_x = self.temp_rect_control.left
        ui_y = self.temp_rect_control.top
        ui_w = self.temp_rect_control.width
        ui_h = self.temp_rect_control.height
        self.image_stack.controls.remove(self.temp_rect_control)
        self.temp_rect_control = None
        if ui_w < 5 or ui_h < 5:
            self.update()
            return
        real_x = int(ui_x * self.current_scale_factor)
        real_y = int(ui_y * self.current_scale_factor)
        real_w = int(ui_w * self.current_scale_factor)
        real_h = int(ui_h * self.current_scale_factor)
        coord = Coordinate(
            id=len(self.coordinates),
            page_number=self.current_page_index + 1,
            type=TOOL_RECT,
            ui_x=ui_x,
            ui_y=ui_y,
            real_x=real_x,
            real_y=real_y,
            real_w=real_w,
            real_h=real_h,
        )
        self.coordinates.append(coord)
        self._add_log(coord)
        self._add_marker_visual(coord)
        self.update()

    def _add_log(self, coord: Coordinate):
        self.log_view.controls.append(Text(str(coord), size=12, font_family="monospace"))

    def _add_marker_visual(self, coord: Coordinate):
        if coord.type == TOOL_RECT:
            ui_w = coord.real_w / self.current_scale_factor
            ui_h = coord.real_h / self.current_scale_factor
            content = Container(
                border=border.all(2, Colors.RED), bgcolor=Colors.with_opacity(0.2, Colors.RED)
            )
            left = coord.real_x / self.current_scale_factor
            top = coord.real_y / self.current_scale_factor
            self.image_stack.controls.append(
                Container(
                    content=content,
                    left=left,
                    top=top,
                    width=ui_w,
                    height=ui_h,
                    ignore_interactions=True,
                )
            )
        else:
            icon_data = Icons.GPS_FIXED
            color = Colors.RED
            if coord.type == TOOL_TEXT:
                icon_data = Icons.TEXT_FIELDS
                color = Colors.BLUE
            elif coord.type == TOOL_CIRCLE:
                icon_data = Icons.CIRCLE_OUTLINED
                color = Colors.RED
            elif coord.type == TOOL_CHECK:
                icon_data = Icons.CHECK
                color = Colors.GREEN
            size = 24
            ui_x = coord.real_x / self.current_scale_factor
            ui_y = coord.real_y / self.current_scale_factor
            self.image_stack.controls.append(
                Container(
                    content=Icon(icon_data, color=color, size=size),
                    left=ui_x - (size / 2),
                    top=ui_y - (size / 2),
                    ignore_interactions=True,
                )
            )

    def on_copy_clipboard(self, e):
        if not self.coordinates:
            self.page.open(SnackBar(Text("データがありません"), bgcolor=Colors.ORANGE))
            self.update()
            return
        lines = ["# --- PDF描画コード ---"]
        for i, c in enumerate(self.coordinates):
            line = ""
            common_args = f"page={c.page_number}, x={c.real_x}, y={c.real_y}"
            if c.type == TOOL_TEXT:
                text_val = c.text if c.text else f"value_{i}"
                line = (
                    f'writer.draw_text({common_args}, text="{text_val}", font_size={c.font_size})'
                )
            elif c.type == TOOL_RECT:
                line = f"writer.draw_rect({common_args}, w={c.real_w}, h={c.real_h})"
            elif c.type == TOOL_CIRCLE:
                line = f"writer.draw_circle({common_args}, radius=20)"
            elif c.type == TOOL_CHECK:
                line = f"writer.draw_check({common_args}, size=20)"
            if line:
                lines.append(line)
        lines.append("# -------------------")
        self.page.set_clipboard("\n".join(lines))
        self.page.open(SnackBar(Text("コードをコピーしました！"), bgcolor=Colors.BLUE))
        self.update()

    async def on_clear_click(self, e):
        self.pdf_service.cleanup()
        self.coordinates.clear()
        self.page_images.clear()
        self.image_stack.controls.clear()
        self.log_view.controls.clear()
        self.current_page_index = 0
        self.btn_prev.disabled = True
        self.btn_next.disabled = True
        self.txt_page_indicator.value = "0 / 0"
        self.page.open(SnackBar(Text("クリアしました"), bgcolor=Colors.BLUE))
        self.update()
