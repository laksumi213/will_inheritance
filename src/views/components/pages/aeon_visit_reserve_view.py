# /components/pages/aeon_visit_reserve_view.py

from flet import (
    Column,
    Container,
    ElevatedButton,
    Row,
    Text,
    TextField,
    Dropdown,
    dropdown,
    RadioGroup,
    Radio,
    Colors,
    FontWeight,
    border,
    padding,
    alignment,
    MainAxisAlignment,
    CrossAxisAlignment,
    Page,
    Divider,
    SnackBar,
    ButtonStyle,
    RoundedRectangleBorder,
)

from services.deceased_service import get_financial_asset_automation_data
from services.web_automation_service import WebAutomationService


class AeonVisitReserveView(Column):
    """
    イオン銀行の来店予約入力フォーム画面
    """

    def __init__(self, page: Page, case_id: int, bank_code: str = "0040"):
        super().__init__(expand=True, scroll="auto", spacing=20)
        self.page = page
        self.case_id = case_id
        self.bank_code = bank_code

        # --- データ取得 ---
        self.automation_data = get_financial_asset_automation_data(case_id, bank_code) or {}
        
        # 担当者情報
        self.staff_name = self.automation_data.get("staff_name_kanji", "")
        self.staff_name_kana = self.automation_data.get("staff_name_kana", "")
        self.staff_tel = self.automation_data.get("staff_tel", "")
        self.staff_mail = self.automation_data.get("staff_mail", "")

        # 💡 被相続人情報の取得（フォーマット用）
        self.deceased_name = self.automation_data.get("deceased_name", "")
        self.deceased_dob = self.automation_data.get("deceased_dob", "")

        # 名前分割
        name_parts = self.staff_name.replace("　", " ").split(" ", 1)
        self.last_name_val = name_parts[0] if name_parts else ""
        self.first_name_val = name_parts[1] if len(name_parts) > 1 else ""

        kana_parts = self.staff_name_kana.replace("　", " ").split(" ", 1)
        self.last_name_kana_val = kana_parts[0] if kana_parts else ""
        self.first_name_kana_val = kana_parts[1] if len(kana_parts) > 1 else ""


        # --- UIコンポーネント定義 ---

        # 1. ヘッダー
        self.header = Container(
            content=Text("ご来店予約登録 (Web自動入力)", size=24, weight=FontWeight.BOLD, color=Colors.BLUE_GREY_800),
            padding=padding.only(bottom=20),
        )

        # 2. ご予約内容セクション
        self.shop_name = Text("イオン銀行　東京八重洲店", size=16, weight=FontWeight.BOLD)
        
        self.interview_method = RadioGroup(
            content=Row([
                Radio(value="visit", label="ご来店"),
            ]),
            value="visit"
        )

        # 💡 修正: 表示上は「各種お手続き」固定（自動化の内部処理と合わせるため）
        self.consultation_content = Dropdown(
            label="ご相談内容",
            width=400,
            options=[
                dropdown.Option("various", "各種お手続き（30分）～ (60分)"),
            ],
            value="various",
            disabled=True # ユーザーに変更させない
        )

        # 3. お客様情報セクション
        self.last_name = TextField(label="お名前(姓)", value=self.last_name_val, width=150)
        self.first_name = TextField(label="お名前(名)", value=self.first_name_val, width=150)
        
        self.last_name_kana = TextField(label="お名前(セイ)", value=self.last_name_kana_val, width=150)
        self.first_name_kana = TextField(label="お名前(メイ)", value=self.first_name_kana_val, width=150)

        self.has_account = RadioGroup(
            content=Row([
                Radio(value="yes", label="あり"),
                Radio(value="no", label="なし"),
            ]),
            value="no"
        )

        self.tel_number = TextField(label="電話番号", value=self.staff_tel, width=300, hint_text="ハイフンなし")

        self.request_phone_contact = RadioGroup(
            content=Row([
                Radio(value="no", label="しない"),
                Radio(value="yes", label="する"),
            ]),
            value="no"
        )

        self.email = TextField(label="メールアドレス", value=self.staff_mail, width=400)
        self.email_confirm = TextField(label="確認用メールアドレス", value=self.staff_mail, width=400)

        # 💡 修正: その他ご相談内容をラジオボタン選択に変更
        self.procedure_select = RadioGroup(
            content=Column([
                Radio(value="残高証明書の申請", label="残高証明書の申請"),
                Radio(value="取引明細の申請", label="取引明細の申請"),
                Radio(value="残高証明書及び取引明細の申請", label="残高証明書及び取引明細の申請"),
            ]),
            value="残高証明書の申請" # 初期表示
        )

        # 4. 同意事項
        self.agreement_info = Container(
            content=Column([
                Text("※ 「個人情報の取り扱い」等の同意チェックは、自動入力時にWebブラウザ上で行います。", color=Colors.RED_400, weight=FontWeight.BOLD),
            ]),
            padding=10,
            border=border.all(1, Colors.GREY_300)
        )

        # 5. アクションボタン
        self.submit_button = ElevatedButton(
            text="Webフォームに入力を作成する",
            style=self._get_button_style(Colors.BLUE_600),
            on_click=self.on_submit
        )
        self.cancel_button = ElevatedButton(
            text="戻る",
            on_click=lambda e: self.page.go(f"/case/{self.case_id}/reserve/visit")
        )


        # --- レイアウト構築 ---
        self.controls = [
            self.header,
            self._create_section("ご予約内容", [
                self._create_label_row("ご希望の店舗", self.shop_name),
                self._create_label_row("ご希望のご相談方法", self.interview_method, required=True),
                self._create_label_row("ご相談内容", self.consultation_content, required=True),
            ]),
            self._create_section("お客さま情報", [
                self._create_label_row("お名前(漢字)", Row([self.last_name, self.first_name]), required=True),
                self._create_label_row("お名前(カナ)", Row([self.last_name_kana, self.first_name_kana]), required=True),
                self._create_label_row("イオン銀行口座の有無", self.has_account, required=True),
                self._create_label_row("電話番号", self.tel_number, required=True, note="半角数字で入力してください"),
                self._create_label_row("電話連絡希望", self.request_phone_contact, required=True),
                self._create_label_row("メールアドレス", self.email, required=True),
                self._create_label_row("確認用メールアドレス", self.email_confirm, required=True),
                # 💡 修正: ラベルとコントロールを変更
                self._create_label_row("手続き内容(その他欄)", self.procedure_select, required=True, note="WEBの「その他ご相談内容」に入力されます"),
            ]),
            self._create_section("同意事項", [
                self.agreement_info
            ]),
            Container(height=20),
            Row([self.cancel_button, self.submit_button], alignment=MainAxisAlignment.CENTER, spacing=20),
            Container(height=50),
        ]

    def _create_section(self, title, controls):
        return Container(
            content=Column([
                Text(title, size=18, weight=FontWeight.BOLD, color=Colors.BLUE_GREY_700),
                Divider(),
                Column(controls, spacing=15)
            ]),
            padding=padding.symmetric(vertical=10),
        )

    def _create_label_row(self, label, content, required=False, note=None):
        label_text = Text(label, width=180, weight=FontWeight.W_500)
        if required:
            label_row = Row([label_text, Container(content=Text("必須", size=10, color=Colors.WHITE), bgcolor=Colors.RED, padding=padding.symmetric(horizontal=4, vertical=2), border_radius=3)])
        else:
            label_row = label_text

        content_col = Column([content])
        if note:
            content_col.controls.append(Text(f"※ {note}", size=12, color=Colors.GREY_600))

        return Row(
            [
                Container(content=label_row, width=200, alignment=alignment.top_left),
                content_col
            ],
            vertical_alignment=CrossAxisAlignment.START,
        )

    def _get_button_style(self, color):
        return ButtonStyle(
            color=Colors.WHITE,
            bgcolor=color,
            shape=RoundedRectangleBorder(radius=5),
            padding=20,
        )

    def on_submit(self, e):
        # 💡 修正: テキストデータの整形
        # {フォーム選択内容}　被相続人：〇〇　相続人：〇〇　生年月日：〇〇
        staff_full_name = f"{self.last_name.value} {self.first_name.value}"
        other_content_text = (
            f"{self.procedure_select.value}　"
            f"被相続人：{self.deceased_name}　"
            f"相続人：{staff_full_name}　"
            f"生年月日：{self.deceased_dob}"
        )

        # 入力データを収集
        input_data = {
            "last_name": self.last_name.value,
            "first_name": self.first_name.value,
            "last_name_kana": self.last_name_kana.value,
            "first_name_kana": self.first_name_kana.value,
            "has_account": self.has_account.value,
            "tel": self.tel_number.value,
            "request_contact": self.request_phone_contact.value,
            "email": self.email.value,
            "email_confirm": self.email_confirm.value,
            "other_content": other_content_text, # 整形したテキストを渡す
        }

        # Selenium自動化を実行
        service = WebAutomationService(self.page)
        service.run_aeon_automation(input_data)

        # メッセージ表示
        self.page.open(
            SnackBar(
                content=Text(
                    "Webブラウザで入力を開始しました... ⏳",
                    color=Colors.WHITE,
                ),
                bgcolor=Colors.BLUE_GREY_700,
                duration=3000,
            )
        )