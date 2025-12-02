# views/asset_register_view.py
from flet import (
    Page,
    View,
    AppBar,
    Text,
    Column,
    Row,
    ElevatedButton,
    ListView,
    Container,
    Colors,
    Icons,
    Icon,
    Card,
    ListTile,
    FloatingActionButton,
    padding,
    alignment,
)
from components.dialogs.bank_register_dialog import BankRegisterDialog
# 既存のモデルやサービスがあればインポート
# from services.deceased_service import DeceasedService 

class AssetRegisterView(View):
    """
    遺産（預貯金）登録画面
    """
    def __init__(self, page: Page):
        super().__init__(route="/asset_register")
        self.page = page
        
        # 画面コンポーネントの初期化
        self.bank_list = ListView(expand=1, spacing=10, padding=20)
        self.loading_text = Text("データを読み込み中...", visible=False)
        
        # レイアウト構築
        self.controls = [
            AppBar(
                title=Text("預貯金管理"),
                bgcolor=Colors.SURFACE_VARIANT,
                center_title=True,
            ),
            Container(
                content=Column(
                    controls=[
                        Row(
                            [
                                Text("登録済み銀行一覧", size=20, weight="bold"),
                                self.loading_text
                            ],
                            alignment="spaceBetween"
                        ),
                        # 銀行リスト表示エリア
                        Container(
                            content=self.bank_list,
                            expand=True, # 画面下まで広げる
                        )
                    ],
                ),
                padding=padding.all(20),
                expand=True,
            )
        ]

        # フローティングアクションボタン（登録ボタン）
        self.floating_action_button = FloatingActionButton(
            icon=Icons.ADD,
            text="銀行登録",
            bgcolor=Colors.PRIMARY,
            on_click=self.open_register_dialog
        )

        # 初期データロード（画面が表示された後に実行）
        # 注: Viewクラスにはdid_mountフックがない場合があるため、
        # 必要に応じて呼び出し元から初期化メソッドを呼ぶ設計にするか、
        # ここでモックデータをロードする。
        self._load_bank_data()

    def open_register_dialog(self, e) -> None:
        """銀行登録ダイアログを開く"""
        dialog = BankRegisterDialog(
            page=self.page,
            on_success=self._refresh_bank_list
        )
        dialog.show()

    def _refresh_bank_list(self) -> None:
        """
        ダイアログから呼び出されるコールバック。
        データ登録後にリストを再読み込みする。
        """
        self._load_bank_data()

    def _load_bank_data(self) -> None:
        """
        DBから銀行データを取得してリストを表示する
        """
        self.bank_list.controls.clear()
        
        # TODO: 本来は Service からデータを取得する
        # banks = DeceasedService().get_all_banks()
        # ここでは動作確認用のダミーデータを表示
        dummy_banks = [
            {"name": "三菱UFJ銀行", "branch": "本店", "type": "普通", "number": "1234567"},
            {"name": "三井住友銀行", "branch": "渋谷支店", "type": "当座", "number": "9876543"},
        ]

        for bank in dummy_banks:
            self.bank_list.controls.append(
                Card(
                    content=ListTile(
                        leading=Icon(Icons.ACCOUNT_BALANCE_WALLET, color=Colors.PRIMARY),
                        title=Text(f"{bank['name']} ({bank['branch']})"),
                        subtitle=Text(f"{bank['type']} - {bank['number']}"),
                        trailing=Icon(Icons.CHEVRON_RIGHT),
                    )
                )
            )
        
        self.update()