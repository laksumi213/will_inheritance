# src/views/bank_import_view.py
import os
import threading
from flet import (
    Page, Column, Row, Text, ElevatedButton, FilePicker, 
    FilePickerResultEvent, Icons, ProgressRing, SnackBar, 
    Colors, Container, Card, ListTile, Icon, MainAxisAlignment
)

# データベース設定
from src.utils.database import SessionLocal
# サービス
from src.services.bank_automation_service import BankAutomationService
from src.services.ai_service import ai_service # OCR用 (Gemini)
from src.services.pdf_service import pdf_service # PDF画像変換用

class BankImportView(Column):
    """
    銀行書類のインポート、OCR処理、名寄せ、リネームを行うビュー
    """
    def __init__(self, page: Page):
        super().__init__()
        self.page = page
        self.expand = True
        
        # UIコンポーネントの初期化
        self.status_text = Text(value="書類をアップロードしてください", size=16)
        self.file_picker = FilePicker(on_result=self.on_file_picked)
        self.page.overlay.append(self.file_picker)
        
        self.loading_indicator = ProgressRing(visible=False)
        self.process_button = ElevatedButton(
            text="書類を選択して処理開始",
            icon=Icons.UPLOAD_FILE,
            on_click=lambda _: self.file_picker.pick_files(
                allow_multiple=False,
                allowed_extensions=["pdf", "jpg", "png", "jpeg"]
            )
        )
        
        self.result_container = Column(scroll="auto", expand=True)

        # メインレイアウト
        self.controls = [
            Container(
                content=Column([
                    Text("銀行書類自動処理", size=24, weight="bold", color="primary"),
                    Text("スキャンした通帳や残高証明書を読み込み、自動で金融機関を特定・整理します。"),
                    Row([
                        self.process_button,
                        self.loading_indicator
                    ], alignment=MainAxisAlignment.START),
                    self.status_text,
                ]),
                padding=20,
                bgcolor="surfaceVariant",
                border_radius=10
            ),
            Container(height=20), # スペーサー
            Text("処理結果:", size=18, weight="bold"),
            self.result_container
        ]

    def on_file_picked(self, e: FilePickerResultEvent):
        """ファイル選択後の処理"""
        if not e.files:
            return

        file_path = e.files[0].path
        file_name = e.files[0].name
        
        if not file_path:
            self.show_snack("ファイルのパスが取得できませんでした。", is_error=True)
            return

        self.status_text.value = f"選択中: {file_name} (処理を開始します...)"
        self.status_text.update()

        # 非同期で処理を実行
        self.toggle_loading(True)
        threading.Thread(
            target=self.process_document_logic,
            args=(file_path,),
            daemon=True
        ).start()

    def process_document_logic(self, file_path: str):
        """
        ドキュメント処理のメインロジック（別スレッド実行）
        """
        session = SessionLocal()
        service = BankAutomationService(session)
        
        try:
            # 1. OCR処理 (Gemini利用)
            # 画像変換が必要な場合（PDF）は変換処理を挟む
            base64_image = self._get_image_for_ocr(file_path)
            
            if not base64_image:
                raise Exception("画像の読み込みに失敗しました。")

            # Geminiで銀行情報を解析
            # analyze_bank_document_sync はリストを返すが、今回は1件と仮定
            ocr_results = ai_service.analyze_bank_document_sync(base64_image)
            
            detected_bank_name = ""
            extracted_text_dummy = "" # 全文テキストが必要だが、JSON形式の場合は擬似的に判定

            if ocr_results:
                result = ocr_results[0]
                detected_bank_name = result.get("bank_name", "")
                # 簡易判定用にテキストを作成
                extracted_text_dummy = f"{detected_bank_name} {result.get('account_type','')} {result.get('account_number','')}"
            
            if not detected_bank_name:
                self.show_snack_thread_safe("銀行名を読み取れませんでした。", is_error=True)
                return

            # 2. 金融機関の検索 (リトライ・学習ロジック付き)
            institution = service.search_financial_institution(detected_bank_name)
            
            institution_name = "不明"
            if institution:
                institution_name = institution.bank_name
                print(f"特定された金融機関: {institution_name}")
            else:
                self.show_snack_thread_safe(f"金融機関マスタに見つかりませんでした: {detected_bank_name}", is_error=True)

            # 3. ファイルのリネーム
            # OCR結果に「残高証明書」などのキーワードが含まれているかは、
            # GeminiのJSONレスポンスだけでは完全ではない場合がありますが、
            # 今回は簡易的にファイル名判定ロジックを通します。
            success, new_path = service.rename_and_move_file(file_path, extracted_text_dummy)
            
            if success:
                result_msg = f"保存完了: {os.path.basename(new_path)}"
            else:
                result_msg = f"リネーム失敗: {new_path}"
                self.show_snack_thread_safe(result_msg, is_error=True)

            # 4. 結果表示の更新
            self.add_result_card(
                bank_name=institution_name,
                doc_type="残高証明書" if "残高証明書" in extracted_text_dummy else "通帳",
                file_path=new_path if success else file_path
            )
            
            self.status_text.value = "処理が完了しました。"
            self.status_text.update()

        except Exception as e:
            error_msg = f"処理中にエラーが発生しました: {str(e)}"
            print(error_msg)
            self.show_snack_thread_safe(error_msg, is_error=True)
        
        finally:
            session.close()
            self.toggle_loading(False)

    def _get_image_for_ocr(self, file_path: str) -> str:
        """ファイルをOCR用のBase64画像文字列に変換する"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            # PDFの場合は先頭ページを画像化
            images = pdf_service.convert_pdf_to_images_sync(file_path)
            if images:
                return images[0].base64_image
        else:
            # 画像ファイルの場合はそのまま読み込んでBase64化
            import base64
            with open(file_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        return ""

    def toggle_loading(self, is_loading: bool):
        """ローディング表示の切り替え"""
        self.loading_indicator.visible = is_loading
        self.process_button.disabled = is_loading
        self.loading_indicator.update()
        self.process_button.update()

    def show_snack(self, message: str, is_error: bool = False):
        """SnackBarを表示する"""
        snack = SnackBar(
            content=Text(message, color=Colors.WHITE),
            bgcolor=Colors.RED if is_error else Colors.GREEN,
        )
        self.page.open = snack
        self.page.update()

    def show_snack_thread_safe(self, message: str, is_error: bool = False):
        """スレッドセーフにSnackBarを表示する"""
        self.show_snack(message, is_error)

    def add_result_card(self, bank_name: str, doc_type: str, file_path: str):
        """結果カードをUIに追加"""
        card = Card(
            content=Container(
                content=ListTile(
                    leading=Icon(Icons.CHECK_CIRCLE, color=Colors.GREEN),
                    title=Text(bank_name, weight="bold"),
                    subtitle=Text(f"種類: {doc_type}\nパス: {file_path}"),
                ),
                padding=10
            )
        )
        self.result_container.controls.append(card)
        self.result_container.update()