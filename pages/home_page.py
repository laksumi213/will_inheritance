# --- 修正後の pages/home_page.py ---

import flet as ft
from sqlalchemy.orm import Session
from db_config import get_db
from models import Decedent


class HomePage(ft.View):
    def __init__(self, page: ft.Page):
        super().__init__(
            "/",
            [
                ft.AppBar(title=ft.Text("被相続人一覧 (ホーム)", size=20, weight=ft.FontWeight.BOLD)),
                ft.Container(
                    ft.Text("新規被相続人を登録", color=ft.Colors.BLUE_600),
                    on_click=lambda e: page.go("/detail/new"),
                    padding=10,
                ),
                ft.Divider(),
                ft.Column(
                    controls=[
                        # 初回は空にしておき、main.pyのroute_changeでロードする
                    ],
                    scroll=ft.ScrollMode.ADAPTIVE,
                    expand=True,
                    key="decedent_list_container"
                    # key="main_content"
                )
            ],
            scroll=ft.ScrollMode.ADAPTIVE
        )
        self.page = page

        # ❌ 削除する行: self.page.add_handler("on_route_change", self.on_view_load)

    # ❌ 削除するメソッド: on_view_load(self, e): ...

    def load_decedents_list(self):
        """データベースから被相続人一覧を取得し、UIを更新する"""
        decedents = None
        try:
            db: Session
            for db in get_db():
                decedents = db.query(Decedent).all()
                break # ジェネレーターからセッションを取得したらbreak
        except Exception as err:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"DB読み込みエラー: {err}"))
            self.page.snack_bar.open = True
            self.page.update()
            return

        list_controls = []
        if not decedents:
            list_controls.append(ft.Text("被相続人の登録がありません。", italic=True))
        else:
            for decedent in decedents:
                # 一覧の各行（Container）を作成
                row = ft.Container(
                    content=ft.Row(
                        [
                            ft.Text(f"ID: {decedent.id}"),
                            ft.VerticalDivider(),
                            ft.Text(f"被相続人: {decedent.name}", expand=True, size=16, weight=ft.FontWeight.BOLD),
                            ft.Text(f"没年月日: {decedent.death_date or '未登録'}"),
                            ft.Icon(ft.Icons.CHEVRON_RIGHT)
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    on_click=lambda e, did=decedent.id: self.page.go(f"/detail/{did}"),
                    padding=15,
                    border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.BLACK12)),
                    ink=True,
                )
                list_controls.append(row)

        # 修正: キーを使用してリストコンテナのColumnを検索して取得する
        list_column = self.page.get_control("decedent_list_container")

        if not list_column:
            # 万が一キーで見つからなかった場合のエラー回避
            print("Error: Decedent list container not found!")
            return

        # 取得したColumnのcontrolsを更新
        list_column.controls.clear()
        list_column.controls.extend(list_controls)

        # self.page.update() は main.py の route_change で呼び出されているため、
        # ここでは冗長になる可能性がありますが、明示的に呼び出しておきます。
        self.page.update()