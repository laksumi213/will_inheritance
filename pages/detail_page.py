import flet as ft
from sqlalchemy.orm import Session
from db_config import get_db
from models import Decedent, Heir
from typing import Optional


class DetailPage(ft.View):
    def __init__(self, page: ft.Page):
        self.page = page
        self.decedent_id: Optional[int] = None
        self.decedent: Optional[Decedent] = None

        # 入力フォームコントロールの定義
        self.name_input = ft.TextField(label="被相続人名", autofocus=True)
        self.death_date_input = ft.TextField(label="没年月日 (YYYY-MM-DD)")
        self.heirs_list_column = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, expand=True)

        self.save_button = ft.ElevatedButton("登録/更新", on_click=self.save_data)
        self.delete_button = ft.ElevatedButton(
            "被相続人を削除",
            on_click=self.delete_decedent,
            style=ft.ButtonStyle(color=ft.Colors.RED),
            visible=False
        )

        super().__init__(
            "/detail/:id",
            [
                ft.AppBar(
                    title=ft.Text("被相続人 詳細/編集", size=20, weight=ft.FontWeight.BOLD),
                    leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: page.go("/")),
                ),
                ft.Container(
                    ft.Column(
                        [
                            self.name_input,
                            self.death_date_input,
                            ft.Divider(),
                            ft.Text("相続人情報", size=18, weight=ft.FontWeight.BOLD),
                            ft.Container(
                                ft.Text("＋ 相続人を追加", color=ft.Colors.GREEN_600),
                                on_click=self.open_heir_dialog,
                                padding=5,
                            ),
                            self.heirs_list_column,
                            ft.Row([self.save_button, self.delete_button], alignment=ft.MainAxisAlignment.CENTER),
                        ],
                        scroll=ft.ScrollMode.ADAPTIVE,
                        expand=True
                    ),
                    padding=10,
                    expand=True
                )
            ]
        )
        # self.page.add_handler("on_route_change", self.on_view_load)

    def on_view_load(self, e):
        """ルート変更時にデータを読み込む"""
        route_parts = e.route.split("/")
        if len(route_parts) >= 3 and route_parts[1] == "detail":
            id_param = route_parts[2]
            if id_param == "new":
                self.decedent_id = None
                self.load_data(is_new=True)
            elif id_param.isdigit():
                self.decedent_id = int(id_param)
                self.load_data()

    def load_data(self, is_new=False):
        """被相続人データと相続人一覧を読み込み、フォームを更新"""
        self.heirs_list_column.controls.clear()

        if is_new:
            self.decedent = None
            self.name_input.value = ""
            self.death_date_input.value = ""
            self.save_button.text = "新規登録"
            self.delete_button.visible = False
            # self.page.update()
            self.update()
            return

        db: Session
        for db in get_db():
            self.decedent = db.query(Decedent).get(self.decedent_id)
            break

        if self.decedent:
            self.name_input.value = self.decedent.name
            self.death_date_input.value = self.decedent.death_date
            self.save_button.text = "更新"
            self.delete_button.visible = True

            # 相続人一覧の描画
            for heir in self.decedent.heirs:
                self.add_heir_row(heir)
        else:
            # データが見つからない場合の処理 (例: ホームに戻る)
            self.page.snack_bar = ft.SnackBar(ft.Text("被相続人データが見つかりませんでした。"))
            self.page.snack_bar.open = True
            self.page.go("/")

        self.page.update()

    def save_data(self, e):
        """被相続人の情報をデータベースに保存/更新する"""
        if not self.name_input.value:
            self.page.snack_bar = ft.SnackBar(ft.Text("被相続人名を入力してください。", bgcolor=ft.Colors.RED_600))
            self.page.snack_bar.open = True
            self.page.update()
            return

        db: Session
        for db in get_db():
            if self.decedent_id is None:
                # 新規作成
                new_decedent = Decedent(
                    name=self.name_input.value,
                    death_date=self.death_date_input.value
                )
                db.add(new_decedent)
                db.commit()
                db.refresh(new_decedent)
                self.decedent_id = new_decedent.id

                # 新規作成後は詳細画面にリダイレクト
                self.page.go(f"/detail/{self.decedent_id}")
                return

            else:
                # 更新
                decedent = db.query(Decedent).get(self.decedent_id)
                if decedent:
                    decedent.name = self.name_input.value
                    decedent.death_date = self.death_date_input.value
                    db.commit()
                    self.page.snack_bar = ft.SnackBar(ft.Text("被相続人情報を更新しました。"))
                    self.page.snack_bar.open = True
                    self.page.update()
                    self.load_data()  # 最新の情報を再読み込み
                    return

    def delete_decedent(self, e):
        """被相続人（と関連する相続人）を削除する"""
        if self.decedent_id is None:
            return

        db: Session
        for db in get_db():
            decedent = db.query(Decedent).get(self.decedent_id)
            if decedent:
                db.delete(decedent)  # cascade="all, delete-orphan" により相続人も削除
                db.commit()
                self.page.snack_bar = ft.SnackBar(ft.Text(f"{decedent.name}を削除しました。", bgcolor=ft.Colors.RED_600))
                self.page.snack_bar.open = True
                self.page.go("/")  # 削除後、ホーム画面へ遷移
                return

    # --- 相続人 (Heir) 関連の処理 ---

    def add_heir_row(self, heir: Heir):
        """相続人の情報を一覧に追加する"""
        # 相続人編集ボタン
        edit_button = ft.IconButton(
            icon=ft.icons.EDIT,
            # 修正点: 編集画面へページ遷移
            on_click=lambda e: self.page.go(f"/heir/{self.decedent_id}/{heir.id}"),
            tooltip="編集"
        )
        # 相続人削除ボタン（削除は削除画面で行うため、ここでは削除します）
        # -> 相続人リストの Row から削除ボタンを削除します

        heir_row = ft.Row(
            [
                ft.Text(f"名前: {heir.name}", expand=True),
                ft.VerticalDivider(),
                # models.pyの修正に合わせて relationship_name を表示
                ft.Text(f"続柄: {heir.relationship_name}", width=150),
                edit_button,
                # delete_button, # 削除
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            padding=ft.padding.only(left=15, right=5, top=5, bottom=5),
            border=ft.border.only(bottom=ft.border.BorderSide(0.5, ft.colors.BLACK12)),

        )
        self.heirs_list_column.controls.append(heir_row)

    def open_heir_dialog(self, e, heir: Optional[Heir] = None):
        """相続人の追加処理を画面遷移に変更"""
        if self.decedent_id is None:
            self.page.snack_bar = ft.SnackBar(ft.Text("まず被相続人を登録してください。"))
            self.page.snack_bar.open = True
            self.page.update()
            return

        # 修正点: 新規登録画面へページ遷移
        self.page.go(f"/heir/{self.decedent_id}/new")

        def save_heir(e):
            """ダイアログから相続人情報を保存/更新する"""
            if not heir_name_input.value or not heir_relationship_input.value:
                e.control.page.snack_bar = ft.SnackBar(
                    ft.Text("名前と続柄を入力してください。", bgcolor=ft.Colors.RED_400))
                e.control.page.snack_bar.open = True
                e.control.page.update()
                return

            db: Session
            for db in get_db():
                if is_new:
                    # 新規作成
                    new_heir = Heir(
                        decedent_id=self.decedent_id,
                        name=heir_name_input.value,
                        relationship=heir_relationship_input.value
                    )
                    db.add(new_heir)
                    db.commit()
                    message = "相続人を追加しました。"
                else:
                    # 更新
                    heir_to_update = db.query(Heir).get(heir.id)
                    if heir_to_update:
                        heir_to_update.name = heir_name_input.value
                        heir_to_update.relationship = heir_relationship_input.value
                        db.commit()
                        message = "相続人情報を更新しました。"

            self.page.dialog.open = False
            self.page.snack_bar = ft.SnackBar(ft.Text(message))
            self.page.snack_bar.open = True
            self.page.update()
            self.load_data()  # 最新の相続人一覧を再読み込み

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("相続人 新規/編集"),
            content=ft.Column(
                [
                    heir_name_input,
                    heir_relationship_input
                ],
                tight=True
            ),
            actions=[
                ft.TextButton("キャンセル", on_click=lambda e: (
                setattr(e.control.page.dialog, "open", False), e.control.page.update())),
                ft.TextButton("保存", on_click=save_heir),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog.open = True
        self.page.update()