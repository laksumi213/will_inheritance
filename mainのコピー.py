import flet as ft
from typing import List, Dict

# 銀行情報を格納するリスト（データの管理）
bank_data: List[Dict[str, str]] = []


def main(page: ft.Page):
    page.title = "動的な銀行口座フォーム"
    page.vertical_alignment = ft.MainAxisAlignment.START

    # フォームのセットを格納するコンテナ
    bank_fields_column = ft.Column(
        controls=[],
        spacing=10,
    )

    # ----------------------------------------------------
    # 各銀行のフォーム（ft.Row）を生成する関数
    # ----------------------------------------------------
    def create_bank_row(initial_name="", initial_account="", index=-1):
        """
        銀行名と口座番号の入力フィールド、削除ボタンを含むft.Rowを作成
        """

        # 入力フィールドの参照を保持するため、辞書として管理
        bank_name_field = ft.TextField(
            label="銀行名",
            value=initial_name,
            width=200,
            data={"index": index}  # どの要素に対応するかを識別するためのデータ
        )
        account_field = ft.TextField(
            label="口座番号",
            value=initial_account,
            width=200,
            data={"index": index}
        )

        def delete_bank_row(e):
            """削除ボタンのクリックイベントハンドラ"""
            row_to_remove = e.control.parent  # 削除対象のft.Rowを取得

            # 親コンテナからft.Rowを削除
            bank_fields_column.controls.remove(row_to_remove)

            # 内部データ（bank_data）からも削除する場合は、ここで処理を追加
            # 例: indexを使ってbank_dataを更新する

            bank_fields_column.update()

        return ft.Row(
            controls=[
                bank_name_field,
                account_field,
                ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_color=ft.Colors.RED_500,
                    on_click=delete_bank_row,
                )
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

    # ----------------------------------------------------
    # 「銀行を追加」ボタンのイベントハンドラ
    # ----------------------------------------------------
    def add_bank_row(e):
        """銀行を追加ボタンが押されたときの処理"""
        new_row = create_bank_row(index=len(bank_fields_column.controls))

        # 新しいフォームをコンテナのcontrolsリストに追加
        bank_fields_column.controls.append(new_row)

        # 画面を更新して新しいフォームを表示
        bank_fields_column.update()

    # ----------------------------------------------------
    # フォームのデータを取得するボタンのイベントハンドラ
    # ----------------------------------------------------
    def submit_form(e):
        """フォームに入力された全データを取得する処理"""
        global bank_data
        bank_data = []  # データをクリア

        # bank_fields_columnの子要素（ft.Row）をループ
        for row in bank_fields_column.controls:
            # ft.Rowのcontrolsから銀行名と口座番号のft.TextFieldを取得
            name_field = row.controls[0]
            account_field = row.controls[1]

            bank_data.append({
                "銀行名": name_field.value,
                "口座番号": account_field.value
            })

        # 結果を表示（デバッグ用）
        page.clean()  # 既存のコントロールを一旦クリア
        page.add(
            ft.Text("入力されたデータ:"),
            ft.Text(str(bank_data))
        )
        page.update()

    # 画面にコントロールを配置
    page.add(
        ft.Text("銀行口座情報", size=24),
        bank_fields_column,  # 動的なフォームが入るコンテナ
        ft.Row(
            controls=[
                ft.ElevatedButton(
                    text="銀行を追加",
                    icon=ft.Icons.ADD,
                    on_click=add_bank_row
                ),
                ft.ElevatedButton(
                    text="送信 (データ取得)",
                    on_click=submit_form
                )
            ],
            spacing=20
        )
    )


ft.app(target=main)