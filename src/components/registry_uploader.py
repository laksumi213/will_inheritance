# src/views/components/registry_uploader.py (コンポーネント化の例)
from flet import (
    Colors,
    Column,
    ElevatedButton,
    FilePicker,
    FilePickerResultEvent,
    Icons,
    Image,
    Row,
    SnackBar,
    Text,
)

from src.services.real_estate_service import get_real_estate_image, save_registry_document


class RegistryUploader(Column):
    def __init__(self, page, case_id, real_estate_id):
        super().__init__()
        self.page = page
        self.case_id = case_id
        self.real_estate_id = real_estate_id

        self.file_picker = FilePicker(on_result=self.on_file_picked)
        self.page.overlay.append(self.file_picker)

        self.img_preview = Image(src="", width=300, height=200, fit="contain", visible=False)

        # 初期表示
        self._load_current_image()

        self.controls = [
            Text("登記情報 (表題部)"),
            Row(
                [
                    ElevatedButton(
                        "PDFを選択して登録",
                        icon=Icons.UPLOAD_FILE,
                        on_click=lambda _: self.file_picker.pick_files(
                            allow_multiple=False, allowed_extensions=["pdf"]
                        ),
                    ),
                ]
            ),
            self.img_preview,
        ]

    def _load_current_image(self):
        path = get_real_estate_image(self.real_estate_id)
        if path:
            self.img_preview.src = path
            self.img_preview.visible = True
        else:
            self.img_preview.visible = False

    def on_file_picked(self, e: FilePickerResultEvent):
        if e.files:
            pdf_path = e.files[0].path
            # 処理中表示
            self.page.open(SnackBar(Text("処理中..."), bgcolor=Colors.BLUE))
            self.page.update()

            success = save_registry_document(self.case_id, self.real_estate_id, pdf_path)

            if success:
                self._load_current_image()
                self.update()
                self.page.open(SnackBar(Text("登録完了"), bgcolor=Colors.GREEN))
            else:
                self.page.open(SnackBar(Text("エラーが発生しました"), bgcolor=Colors.RED))

            self.page.update()
