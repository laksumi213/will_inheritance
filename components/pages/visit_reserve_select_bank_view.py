# /components/pages/visit_reserve_select_bank_view.py

from flet import (
    Colors,
    Column,
    Container,
    Divider,
    ElevatedButton,
    FontWeight,
    Icon,
    Icons,
    Page,
    Row,
    Text,
    ListTile,
    ListView,
)
from services.deceased_service import get_financial_asset_by_case
from services.deceased_service import get_financial_asset_automation_data 
from components.pages.mizuho_visit_reserve_process import start_mizuho_reservation_process


class VisitReserveSelectBankView(Column):
    """
    来店予約を行うための銀行を選択するビュー。
    案件に登録されている銀行資産の一覧を表示する。
    """

    def __init__(self, page: Page, case_id: int):
        super().__init__(
            expand=True,
            scroll="auto",
            spacing=20,
        )
        self.page = page
        self.case_id = case_id
        
        self.controls = [
            Text(
                "📅 来店予約 - 銀行選択",
                size=24,
                weight=FontWeight.BOLD,
            ),
            Divider(),
            Text(
                "来店予約を行う金融機関を、案件に登録されているリストから選択してください。",
                size=16,
            ),
            Container(
                content=self._create_bank_list_controls(),
                padding=10,
                border_radius=10,
                bgcolor=Colors.WHITE,
                height=400, # 一覧表示用の高さを設定
            )
        ]

    def _create_bank_list_controls(self):
        """登録済みの銀行リストを生成する"""
        
        # 1. 案件の金融資産リストを取得
        assets = get_financial_asset_by_case(self.case_id)
        
        # 2. 銀行名とコードのユニークなセットを作成
        unique_banks = {}
        for asset in assets:
            bank_code = asset.get('bank_code')
            bank_name = asset.get('bank_name')
            if bank_code and bank_code not in unique_banks:
                unique_banks[bank_code] = bank_name
        
        if not unique_banks:
            return ListView(controls=[
                Text("現在、この案件に登録されている銀行口座情報がありません。先に銀行登録を行ってください。", color=Colors.RED_700)
            ])

        controls = []
        for code, name in unique_banks.items():
            # 💡 銀行選択ボタンの作成
            def open_bank_reserve_page(e, code=code):
                # 銀行コードを付加した固有の来店予約ルートへ遷移
                # 例: /case/1/reserve/mizuho (みずほの銀行コードは 0001)
                
                # 銀行コードに基づいて次のルーティングを決定
                if code == "0001":
                    # みずほ銀行専用ルート
                    start_mizuho_reservation_process(self.page, self.case_id)
                    # self.page.go(f"/case/{self.case_id}/reserve/mizuho")
                elif code == "0009":
                    # 三井住友銀行専用ルート (仮)
                    self.page.go(f"/case/{self.case_id}/reserve/smbc")
                else:
                    # 汎用/標準予約ルート (銀行コードを引数として渡す)
                    self.page.go(f"/case/{self.case_id}/reserve/standard/{code}")
            
            controls.append(
                ListTile(
                    leading=Icon(Icons.ACCOUNT_BALANCE),
                    title=Text(f"{name} (銀行コード: {code})", weight=FontWeight.W_600),
                    trailing=ElevatedButton(
                        "来店予約へ進む",
                        icon=Icons.CALENDAR_MONTH,
                        on_click=open_bank_reserve_page,
                        data=code
                    ),
                    on_click=open_bank_reserve_page # リスト全体をクリックでも進める
                )
            )
        
        return ListView(controls=controls)