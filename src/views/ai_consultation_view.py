# src/views/ai_consultation_view.py
import asyncio
from flet import (
    View,
    Page,
    AppBar,
    Text,
    Column,
    Row,
    TextField,
    IconButton,
    Container,
    ListView,
    SnackBar,
    ProgressRing,
    Icons,
    Colors,
    MainAxisAlignment,
    CrossAxisAlignment,
    padding,
    border_radius,
)

# AIサービスインポートを削除
# from services.ai_service import ai_service

class AIConsultationView(View):
    """
    AIによる遺産整理相談チャット画面 (AI無効化版)
    """

    def __init__(self, page: Page):
        super().__init__(route="/ai_consultation")
        self.page = page
        self.page.title = "AI 遺産整理アドバイザー (Offline)"
        
        # UIコンポーネントの初期化
        self.chat_history = ListView(
            expand=True,
            spacing=10,
            auto_scroll=True,
            padding=20
        )
        self.input_field = TextField(
            hint_text="相続や遺産整理について質問してください...",
            expand=True,
            border_radius=20,
            shift_enter=True,
            on_submit=self.send_message,
            multiline=True,
            max_lines=3,
            disabled=True # AI無効のため入力不可にする場合
        )
        self.send_button = IconButton(
            icon=Icons.SEND_ROUNDED,
            icon_color="grey",
            tooltip="送信",
            on_click=self.send_message,
            disabled=True
        )
        self.loading_indicator = Container(
            content=ProgressRing(width=20, height=20, stroke_width=2),
            visible=False,
            padding=padding.only(right=10)
        )

        # 画面レイアウトの構築
        self.controls = [
            AppBar(
                title=Text("遺産整理 AIアシスタント (無効)"),
                bgcolor="surfaceVariant",
                color="onSurfaceVariant"
            ),
            Container(
                content=Column(
                    controls=[
                        # チャット履歴エリア
                        Container(
                            content=self.chat_history,
                            expand=True,
                            bgcolor="surface",
                            border_radius=10,
                        ),
                        # 入力エリア
                        Container(
                            content=Row(
                                controls=[
                                    self.input_field,
                                    self.loading_indicator,
                                    self.send_button
                                ],
                                alignment=MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=CrossAxisAlignment.END,
                            ),
                            padding=padding.symmetric(horizontal=10, vertical=10),
                            bgcolor="secondaryContainer",
                            border_radius=border_radius.only(top_left=15, top_right=15)
                        )
                    ],
                    spacing=0,
                ),
                expand=True
            )
        ]
        
        # 初期メッセージ
        self._add_message_bubble("現在、AI機能は無効化されています。管理者にお問い合わせください。", is_user=False)

    def _add_message_bubble(self, message: str, is_user: bool) -> None:
        """チャットバブルを画面に追加するヘルパー関数"""
        self.chat_history.controls.append(
            Row(
                controls=[
                    Container(
                        content=Text(
                            message,
                            color=Colors.WHITE if is_user else "onSurfaceVariant",
                            selectable=True
                        ),
                        bgcolor="primary" if is_user else "surfaceVariant",
                        padding=15,
                        border_radius=border_radius.all(15),
                        width=None,
                        margin=padding.only(
                            left=50 if is_user else 0,
                            right=0 if is_user else 50
                        )
                    )
                ],
                alignment=MainAxisAlignment.END if is_user else MainAxisAlignment.START
            )
        )
        self.page.update()

    async def send_message(self, e) -> None:
        """
        メッセージ送信処理 (ダミー応答)
        """
        user_message = self.input_field.value
        if not user_message:
            return

        self._add_message_bubble(user_message, is_user=True)
        self.input_field.value = ""
        self.page.update()

        # ダミー応答
        await asyncio.sleep(0.5)
        self._add_message_bubble("AI機能は現在利用できません。", is_user=False)