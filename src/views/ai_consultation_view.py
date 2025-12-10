# views/ai_consultation_view.py
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
    FloatingActionButton,
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
    alignment,
    Control
)

# サービス層をインポート
from services.ai_service import ai_service

class AIConsultationView(View):
    """
    AIによる遺産整理相談チャット画面
    """

    def __init__(self, page: Page):
        super().__init__(route="/ai_consultation")
        self.page = page
        self.page.title = "AI 遺産整理アドバイザー"
        
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
            max_lines=3
        )
        self.send_button = IconButton(
            icon=Icons.SEND_ROUNDED,
            icon_color="primary",
            tooltip="送信",
            on_click=self.send_message
        )
        self.loading_indicator = Container(
            content=ProgressRing(width=20, height=20, stroke_width=2),
            visible=False,
            padding=padding.only(right=10)
        )

        # 画面レイアウトの構築
        self.controls = [
            AppBar(
                title=Text("遺産整理 AIアシスタント"),
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
                        # ユーザーは右寄せ、AIは左寄せの視覚効果（簡易実装）
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
        メッセージ送信処理
        Vertex AI呼び出し中のエラーハンドリングを含む
        """
        user_message = self.input_field.value
        if not user_message:
            return

        # UI更新: ユーザーメッセージ表示と入力クリア
        self._add_message_bubble(user_message, is_user=True)
        self.input_field.value = ""
        self.input_field.disabled = True
        self.send_button.disabled = True
        self.loading_indicator.visible = True
        self.page.update()

        try:
            # AIサービス呼び出し
            ai_response = await ai_service.generate_response(user_message)
            self._add_message_bubble(ai_response, is_user=False)

        except Exception as error:
            # エラー発生時の処理 (SnackBarで赤色通知)
            error_msg = f"エラーが発生しました: {str(error)}"
            
            # Flet 0.21+ 推奨の書き方
            self.page.open(
                SnackBar(
                    content=Text(error_msg, color=Colors.WHITE),
                    bgcolor=Colors.RED,
                    action="閉じる",
                    action_color=Colors.WHITE
                )
            )
            
            # ログにも出力
            print(f"[UI Error] {error_msg}")

        finally:
            # UI状態の復帰
            self.input_field.disabled = False
            self.send_button.disabled = False
            self.loading_indicator.visible = False
            self.input_field.focus()
            self.page.update()