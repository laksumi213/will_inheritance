# /components/utils/ui_utils.py

from flet import (
    AlertDialog,
    Colors,
    ElevatedButton,
    MainAxisAlignment,
    Page,
    Text,
    TextButton,
)


def show_confirm_dialog(
    page: Page,
    title: str,
    message: str,
    confirm_text: str,
    on_confirm: callable,  # 実行するコールバック関数
    confirm_color=Colors.RED_600,
):
    """汎用的な確認ダイアログを表示する"""

    # ダイアログを閉じる関数
    def close_dialog(e):
        page.close(dialog)
        page.update()

    # 確認アクション実行関数
    def handle_confirm(e):
        close_dialog(e)
        on_confirm(e)  # コールバック関数を実行

    dialog = AlertDialog(
        modal=True,
        title=Text(title, weight="bold", color=confirm_color),
        content=Text(message, size=14),
        actions=[
            TextButton("キャンセル", on_click=close_dialog),
            ElevatedButton(
                confirm_text,
                on_click=handle_confirm,
                color=Colors.WHITE,
                bgcolor=confirm_color,
            ),
        ],
        actions_alignment=MainAxisAlignment.END,
    )

    page.open(dialog)
    dialog.open = True
    page.update()
