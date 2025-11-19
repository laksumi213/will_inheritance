# /components/pages/mizuho_visit_reserve_view.py

from flet import (
    Colors,
    Column,
    Container,
    Divider,
    ElevatedButton,
    FontWeight,
    Icons,
    Page,
    Row,
    Text,
)

class MizuhoVisitReserveView(Column):
    """
    みずほ銀行の来店予約ページ (MizuhoBalanceDocViewと類似の構造)
    """

    def __init__(self, page: Page, case_id: int):
        super().__init__(
            expand=True,
            scroll="auto",
            spacing=20,
        )
        self.page = page
        self.case_id = case_id
        
        # 💡 ここで必要なデータ（銀行名、口座情報など）をサービス層からロードするロジックが入ります。
        
        self.controls = [
            Text(
                "🏦 みずほ銀行 来店予約",
                size=24,
                weight=FontWeight.BOLD,
            ),
            Divider(),
            Text(
                f"案件ID: {self.case_id} のみずほ銀行手続き用の来店予約資料を作成します。",
                size=16,
            ),
            
            # --- 作成ボタンエリア ---
            Container(
                padding=20,
                bgcolor=Colors.BLUE_GREY_50,
                border_radius=10,
                content=Column(
                    [
                        Text(
                            "来店予約資料の生成",
                            size=18,
                            weight=FontWeight.W_600,
                        ),
                        Row(
                            [
                                ElevatedButton(
                                    "来店予約依頼書を作成",
                                    icon=Icons.FILE_DOWNLOAD,
                                    on_click=self._create_document_action,
                                    bgcolor=Colors.BLUE_600,
                                    color=Colors.WHITE,
                                ),
                                # 予約日時確認ボタンなどを追加可能
                            ],
                            spacing=20
                        )
                    ],
                    spacing=15
                )
            ),
            
            # --- プレースホルダー/説明 ---
            Text(
                "※ この画面は、特定の銀行との来店予約に必要な書類作成や日時管理のために使用されます。",
                size=12,
                color=Colors.GREY_600
            )
        ]

    def _create_document_action(self, e):
        """来店予約依頼書を作成するアクション（PDF/Word生成を想定）"""
        # 実際には、ここでWordやPDF生成サービスを呼び出す
        
        self.page.open(
            SnackBar(
                content=Text("来店予約依頼書を生成しました。", color=Colors.WHITE),
                bgcolor=Colors.GREEN_700,
                duration=1500,
            )
        )
        self.page.update()