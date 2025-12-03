import flet as ft

def main(page: ft.Page):
    # (1) AlertDialogのインスタンスを作成
    # on_dismissはダイアログが閉じられたときに実行される関数を設定できます
    alert_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("確認"),
        content=ft.Text("操作を実行しますか？"),
        actions=[
            ft.TextButton("はい", on_click=lambda e: print("はいがクリックされました")),
            ft.TextButton("いいえ", on_click=lambda e: print("いいえがクリックされました")),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def open_dlg(e):
        page.open(alert_dialog)
        # page.dialog = alert_dialog
        # alert_dialog.open = True
        page.update()

    page.add(
        ft.ElevatedButton("ダイアログを開く", on_click=open_dlg)
    )

if __name__ == "__main__":
    ft.app(target=main)