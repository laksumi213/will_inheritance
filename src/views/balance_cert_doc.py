# src/views/balance_cert_doc.py
from flet import (
    Colors,
    Column,
    Container,
    Divider,
    ElevatedButton,
    FontWeight,
    Icon,
    Icons,
    ListTile,
    ListView,
    Page,
    Text,
    border,
    ControlEvent,
    RoundedRectangleBorder
)

from src.services.deceased_service import get_financial_asset_by_case


class BalanceCertDocView(Column):
    """
    残高証明書作成のための銀行を選択するビュー。
    案件に登録されている銀行資産の一覧を表示し、各銀行ごとの書類作成画面へ遷移させる。
    """

    def __init__(self, page: Page, case_id: int):
        super().__init__(
            expand=True,
            scroll="auto",
            spacing=20,
        )
        self.page = page  # ページ参照を保持
        self.case_id = case_id

        # 💡 修正: 初期化時に immediately load を行わず、空のコントロールリストを設定
        self.bank_list_container = Column(
            controls=[Text("銀行情報をロード中...", color="onSurfaceVariant")],
            expand=True, 
            scroll="auto"
        )
        
        self.controls = [
            Text(
                "📄 残高証明書作成 - 銀行選択",
                size=24,
                weight=FontWeight.BOLD,
                color="onSurface",
            ),
            Divider(),
            Text(
                "残高証明書を作成する金融機関を選択してください。",
                size=16,
            ),
            self.bank_list_container
        ]

    def did_mount(self):
        """
        コントロールがPageにアタッチされた後、一度だけ実行される
        ここで初めてデータロードとUIの更新を行う
        """
        self._load_bank_list()

    def _load_bank_list(self):
        """登録済みの銀行リストを生成・更新する"""
        
        # 1. 案件の金融資産リストを取得
        financial_assets = get_financial_asset_by_case(self.case_id)
        
        # 2. 銀行名とコードのユニークなセットを作成
        unique_banks = {}
        for asset in financial_assets:
            if 'bank_code' not in asset or not asset['bank_code']:
                continue
            
            code = asset['bank_code']
            if code not in unique_banks:
                unique_banks[code] = {
                    'name': asset.get('bank_name', '銀行名不明'),
                    'code': code
                }
        
        controls = []
        if unique_banks:
            for code, bank_info in unique_banks.items():
                name = bank_info['name']

                def open_doc_create_page(e: ControlEvent, code=code):
                    """書類作成ボタン/リスト押下時のルーティング"""
                    if not self.page:
                        return
                    
                    # 銀行コードに基づいて次のルーティングを決定
                    if code == "0001":
                        self.page.go(f"/case/{self.case_id}/doc/balance_cert/mizuho")
                    elif code == "0009":
                        self.page.go(f"/case/{self.case_id}/doc/balance_cert/smbc")
                    else:
                        self.page.go(f"/case/{self.case_id}/doc/balance_cert/standard/{code}")

                controls.append(
                    ListTile(
                        leading=Icon(Icons.ACCOUNT_BALANCE, color="primary"),
                        title=Text(
                            f"{name} (銀行コード: {code})", 
                            color="onSurface",
                            weight=FontWeight.W_500
                        ),
                        trailing=ElevatedButton(
                            "書類作成へ",
                            icon=Icons.EDIT_DOCUMENT,
                            on_click=open_doc_create_page,
                            data=code,
                            bgcolor="primaryContainer",
                            color="onPrimaryContainer",
                        ),
                        on_click=open_doc_create_page,
                        bgcolor="surfaceVariant",
                        shape=RoundedRectangleBorder(radius=5),
                    )
                )
        else:
            controls.append(
                Container(
                    content=Text("現在、この案件に登録されている銀行口座情報がありません。\n先に「銀行登録」メニューから口座情報を登録してください。", color=Colors.ERROR),
                    padding=20
                )
            )

        # 3. コントロールを更新 (この時点でコントロールはPageにアタッチ済み)
        self.bank_list_container.controls = controls
        self.bank_list_container.update()
        
        # NOTE: 自身の update() 呼び出しは不要 (親の update() で対応)