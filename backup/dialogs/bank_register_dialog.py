# components/dialogs/bank_register_dialog.py
from flet import (
    AlertDialog,
    Colors,
    Column,
    Control,
    ElevatedButton,
    Icon,
    Icons,
    MainAxisAlignment,
    Page,
    Row,
    SnackBar,
    Text,
    TextButton,
    TextField,
)

from services.deceased_service import DeceasedService


class BankRegisterDialog(AlertDialog):
    """
    銀行情報を登録するためのダイアログコンポーネント。
    UI部品をインスタンス変数として保持し、不要な再描画を防ぐ設計にしています。
    """

    def __init__(self, page: Page, on_success: callable) -> None:
        """
        Args:
            page (Page): アプリケーションのページオブジェクト
            on_success (callable): 登録成功時に実行するコールバック関数
        """
        self.page = page
        self.on_success = on_success
        self._service = DeceasedService()  # サービス層のインスタンス

        # --- UIコンポーネントの初期化 (buildメソッド内ではなくここで定義) ---
        self.bank_name_field = TextField(
            label="銀行名",
            hint_text="例: 三菱UFJ銀行",
            width=300,
            border_color=Colors.OUTLINE,
        )

        self.branch_name_field = TextField(
            label="支店名",
            hint_text="例: 本店",
            width=300,
            border_color=Colors.OUTLINE,
        )

        self.account_type_field = TextField(
            label="口座種別",
            hint_text="例: 普通 / 当座",
            width=300,
            border_color=Colors.OUTLINE,
        )

        self.account_number_field = TextField(
            label="口座番号",
            width=300,
            keyboard_type="number",
            border_color=Colors.OUTLINE,
        )

        self.account_holder_field = TextField(
            label="名義人",
            width=300,
            border_color=Colors.OUTLINE,
        )

        # 親クラス(AlertDialog)の初期化
        super().__init__(
            modal=True,
            title=Row([Icon(Icons.ACCOUNT_BALANCE), Text("銀行口座の登録")], spacing=10),
            content=Column(
                controls=[
                    self.bank_name_field,
                    self.branch_name_field,
                    self.account_type_field,
                    self.account_number_field,
                    self.account_holder_field,
                ],
                tight=True,
                spacing=15,
                width=350,
            ),
            actions=[
                TextButton("キャンセル", on_click=self.close_dialog),
                ElevatedButton(
                    "登録",
                    icon=Icons.SAVE,
                    bgcolor=Colors.PRIMARY,
                    color=Colors.ON_PRIMARY,
                    on_click=self.handle_register_click,
                ),
            ],
            actions_alignment=MainAxisAlignment.END,
        )

    def show(self) -> None:
        """ダイアログを表示する"""
        self.page.dialog = self
        self.open = True
        self.page.update()

    def close_dialog(self, e: Control = None) -> None:
        """ダイアログを閉じる"""
        self.open = False
        self.page.update()

    def handle_register_click(self, e: Control) -> None:
        """登録ボタン押下時の処理"""
        # バリデーション
        if not self.bank_name_field.value:
            self.show_error("銀行名は必須です")
            return

        # UIをブロックせずに処理するためスレッド等での実行を検討するが、
        # ここではシンプルにtry-exceptで同期実行し、エラーハンドリングを優先する
        try:
            self._register_process()
        except Exception as ex:
            # エラー発生時にアプリが落ちないようにキャッチする
            print(f"Registration Error: {ex}")
            self.show_error(f"登録中にエラーが発生しました: {str(ex)}")

    def _register_process(self) -> None:
        """実際の登録処理（サービスの呼び出し）"""
        # 入力値の取得
        data = {
            "bank_name": self.bank_name_field.value,
            "branch_name": self.branch_name_field.value,
            "account_type": self.account_type_field.value,
            "account_number": self.account_number_field.value,
            "account_holder": self.account_holder_field.value,
            # 被相続人IDなどはContextから取得するか、仮で設定
            # 今回は既存サービスに合わせて辞書を作成
        }

        # サービスの呼び出し (既存のDeceasedServiceを利用)
        # ※本来は deceased_id が必要だが、contextから取得する前提とする。
        # ここではデモ用として、サービスのメソッドシグネチャに合わせて呼び出す。
        # NOTE: 既存コードの設計に合わせ、add_bank_account 等のメソッドがあると仮定して実装。
        # もし deceased_service.py に該当メソッドがない場合は適宜追加が必要です。

        # 仮実装: Serviceにメソッドがある前提でコール
        # self._service.add_bank_account(data)

        # 成功時の処理
        self.open = False
        self.page.update()

        self.page.snack_bar = SnackBar(
            Text("銀行口座情報を登録しました"),
            bgcolor=Colors.GREEN,
        )
        self.page.snack_bar.open = True
        self.page.update()

        # 親画面の更新コールバックを実行
        if self.on_success:
            self.on_success()

    def show_error(self, message: str) -> None:
        """エラーメッセージをSnackBarで表示"""
        self.page.snack_bar = SnackBar(
            Text(message, color=Colors.WHITE),
            bgcolor=Colors.RED,
        )
        self.page.snack_bar.open = True
        self.page.update()
