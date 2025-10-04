import flet as ft
from sqlalchemy.orm import Session
from db_config import get_db
from models import Heir, Decedent
from typing import Optional


class HeirDetailPage(ft.View):
    def __init__(self, page: ft.Page):
        self.page = page
        self.heir_id: Optional[int] = None
        self.decedent_id: Optional[int] = None
        self.decedent_name: str = "読み込み中"

        # UIコントロール
        self.decedent_info = ft.Text("被相続人:", size=16, weight=ft.FontWeight.BOLD)
        self.name_input = ft.TextField(label="相続人名", autofocus=True)
        self.relationship_input = ft.TextField(label="続柄")  # models.pyでrelationship_nameに変更済
        self.save_button = ft.ElevatedButton("登録/更新", on_click=self.save_heir)
        self.delete_button = ft.ElevatedButton(
            "相続人を削除",
            on_click=self.delete_heir,
            style=ft.ButtonStyle(color=ft.Colors.RED),
            visible=False
        )

        super().__init__(
            "/heir/:did/:hid",  # did: Decedent ID, hid: Heir ID
            [
                ft.AppBar(
                    title=ft.Text("相続人 詳細/編集", size=20, weight=ft.FontWeight.BOLD),
                    leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=self.go_back),
                ),
                ft.Container(
                    ft.Column(
                        [
                            self.decedent_info,
                            ft.Divider(),
                            self.name_input,
                            self.relationship_input,
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
        # self.page.add_handler("on_route_change", self.on_view_load)  # main.pyで呼び出すためのダミー

    def go_back(self, e):
        """詳細画面に戻る"""
        if self.decedent_id:
            self.page.go(f"/detail/{self.decedent_id}")
        else:
            self.page.go("/")

    def on_view_load(self, route_event):
        """ルート変更時にデータを読み込む"""
        # ルートからIDを抽出
        route_parts = self.page.route.split("/")
        if len(route_parts) < 4 or route_parts[1] != "heir":
            return

        did_param = route_parts[2]
        hid_param = route_parts[3]

        self.decedent_id = int(did_param) if did_param.isdigit() else None
        self.heir_id = int(hid_param) if hid_param.isdigit() else None

        if not self.decedent_id:
            self.page.snack_bar = ft.SnackBar(ft.Text("被相続人IDが無効です。"))
            self.page.snack_bar.open = True
            self.page.go("/")
            return

        self.load_data()

    def load_data(self):
        """被相続人情報と相続人データを読み込み、フォームを更新"""
        db: Session
        for db in get_db():
            # 被相続人情報の取得
            decedent = db.query(Decedent).get(self.decedent_id)
            if decedent:
                self.decedent_info.value = f"被相続人: {decedent.name}"
            else:
                self.decedent_info.value = "被相続人: (データなし)"

            if self.heir_id is None:
                # 新規作成
                self.name_input.value = ""
                self.relationship_input.value = ""
                self.save_button.text = "新規登録"
                self.delete_button.visible = False
            else:
                # 編集
                heir = db.query(Heir).get(self.heir_id)
                if heir and heir.decedent_id == self.decedent_id:
                    self.name_input.value = heir.name
                    self.relationship_input.value = heir.relationship_name
                    self.save_button.text = "更新"
                    self.delete_button.visible = True
                else:
                    self.page.snack_bar = ft.SnackBar(ft.Text("相続人データが見つかりませんでした。"))
                    self.page.snack_bar.open = True
                    self.go_back(None)

            break

        self.page.update()

    def save_heir(self, e):
        """相続人の情報をデータベースに保存/更新する"""
        if not self.name_input.value or not self.relationship_input.value:
            self.page.snack_bar = ft.SnackBar(ft.Text("名前と続柄を入力してください。", bgcolor=ft.Colors.RED_600))
            self.page.snack_bar.open = True
            self.page.update()
            return

        db: Session
        for db in get_db():
            if self.heir_id is None:
                # 新規作成
                new_heir = Heir(
                    decedent_id=self.decedent_id,
                    name=self.name_input.value,
                    relationship_name=self.relationship_input.value
                )
                db.add(new_heir)
                db.commit()
                message = "相続人を追加しました。"
            else:
                # 更新
                heir_to_update = db.query(Heir).get(self.heir_id)
                if heir_to_update:
                    heir_to_update.name = self.name_input.value
                    heir_to_update.relationship_name = self.relationship_input.value
                    db.commit()
                    message = "相続人情報を更新しました。"
            break

        self.page.snack_bar = ft.SnackBar(ft.Text(message))
        self.page.snack_bar.open = True
        self.page.update()
        self.go_back(None)  # 編集後、被相続人の詳細画面に戻る

    def delete_heir(self, e):
        """相続人を削除する"""
        if self.heir_id is None:
            return

        db: Session
        for db in get_db():
            heir_to_delete = db.query(Heir).get(self.heir_id)
            if heir_to_delete:
                db.delete(heir_to_delete)
                db.commit()
                self.page.snack_bar = ft.SnackBar(ft.Text(f"{heir_to_delete.name}を削除しました。"))
                self.page.snack_bar.open = True
            break

        self.page.update()
        self.go_back(None)  # 削除後、被相続人の詳細画面に戻る