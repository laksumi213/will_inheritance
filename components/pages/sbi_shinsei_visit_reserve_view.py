# /components/pages/sbi_shinsei_visit_reserve_view.py

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
    Icon,
    Icons,
    SnackBar,
    ButtonStyle,
    RoundedRectangleBorder,
)

from services.deceased_service import get_financial_asset_automation_data
from services.web_automation_service import WebAutomationService


class SbiShinseiVisitReserveView(Column):
    """
    SBI新生銀行の来店予約入力フォーム画面
    """

    def __init__(self, page: Page, case_id: int, bank_code: str = "0397"):
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

        # 被相続人情報
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
            content=Column([
                Row([
                    Icon(Icons.ACCOUNT_BALANCE, size=30, color=Colors.BLUE_800),
                    Text("SBI新生銀行", size=24, weight=FontWeight.BOLD, color=Colors.BLUE_800),
                ]),
                Divider(height=1, color=Colors.GREY_300),
                Text("来店予約入力 (Web自動入力)", size=20, weight=FontWeight.W_500),
            ]),
            padding=padding.only(bottom=20),
        )

        # 2. ご相談内容
        self.consultation_purpose = Dropdown(
            label="ご相談の目的",
            width=400,
            options=[
                dropdown.Option("inheritance", "相続について"),
            ],
            value="inheritance"
        )

        # 3. 店舗
        self.store_name = Dropdown(
            label="ご来店店舗",
            width=400,
            options=[
                dropdown.Option("head_office", "本店フィナンシャルセンター"),
                dropdown.Option("yokohama", "横浜フィナンシャルセンター"),
                # 必要に応じて店舗を追加
            ],
            value="head_office"
        )

        # 4. お客さま情報
        self.last_name = TextField(label="姓", value=self.last_name_val, width=150)
        self.first_name = TextField(label="名", value=self.first_name_val, width=150)
        self.last_name_kana = TextField(label="セイ", value=self.last_name_kana_val, width=150)
        self.first_name_kana = TextField(label="メイ", value=self.first_name_kana_val, width=150)

        self.tel_number = TextField(label="電話番号", value=self.staff_tel, width=300)
        self.email = TextField(label="メールアドレス", value=self.staff_mail, width=400)

        self.has_account = RadioGroup(
            content=Row([
                Radio(value="yes", label="あり"),
                Radio(value="no", label="なし"),
            ]),
            value="no"
        )
        
        self.account_number = TextField(label="店番号-口座番号", width=200, disabled=True)

        # 💡 詳細入力 (イオン銀行と同様のラジオボタン形式に統合)
        self.consultation_detail = TextField(
            label="ご相談内容の詳細",
            multiline=True,
            min_lines=3,
            width=600,
            visible=False # 自動生成するので非表示でも良いが、手動修正用に残すことも可。今回はイオン式に合わせるため自動生成ロジックを使用。
        )

        self.procedure_select = RadioGroup(
            content=Column([
                Radio(value="残高証明書の申請", label="残高証明書の申請"),
                Radio(value="取引明細の申請", label="取引明細の申請"),
                Radio(value="残高証明書及び取引明細の申請", label="残高証明書及び取引明細の申請"),
            ]),
            value="残高証明書の申請"
        )

        # 5. ボタン
        self.submit_button = ElevatedButton(
            text="Webフォームに入力を作成する",
            style=self._get_button_style(Colors.BLUE_800),
            on_click=self.on_submit
        )
        self.cancel_button = ElevatedButton(
            text="戻る",
            on_click=lambda e: self.page.go(f"/case/{self.case_id}/reserve/visit")
        )


        # --- レイアウト構築 (イオン銀行と同じセクション構成) ---
        self.controls = [
            self.header,
            self._create_section("1. ご予約内容", [
                self._create_label_row("ご相談の目的", self.consultation_purpose, required=True),
                self._create_label_row("ご来店店舗", self.store_name, required=True),
            ]),
            self._create_section("2. お客さま情報", [
                self._create_label_row("お名前(漢字)", Row([self.last_name, self.first_name]), required=True),
                self._create_label_row("お名前(カナ)", Row([self.last_name_kana, self.first_name_kana]), required=True),
                self._create_label_row("電話番号", self.tel_number, required=True),
                self._create_label_row("メールアドレス", self.email, required=True),
                self._create_label_row("口座をお持ちですか", self.has_account, required=True),
                self._create_label_row("口座番号", self.account_number, note="口座をお持ちの方のみ"),
                # イオン銀行と同様の形式で追加
                self._create_label_row("手続き内容(詳細)", self.procedure_select, required=True, note="WEBの「ご相談内容の詳細」に入力されます"),
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
        # 💡 テキストデータの整形 (イオン銀行と同じロジック)
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
            "tel": self.tel_number.value,
            "email": self.email.value,
            "other_content": other_content_text, # 整形したテキスト
        }

        # WebAutomationServiceを使用
        service = WebAutomationService(self.page)
        service.run_sbi_shinsei_automation(input_data)

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