# main.py

import flet as ft
import re
from sqlalchemy.orm import Session
from database import init_db, add_initial_data, Engine, Deceased
from deceased_detail_view import DeceasedDetailView

# データベースの初期化とテストデータの追加
init_db()
add_initial_data()


# 被相続人一覧表示（メイン）ビュー
def DeceasedListView(page: ft.Page):
    # データベースから全被相続人を取得
    def get_deceased_list():
        with Session(bind=Engine) as session:
            return session.query(Deceased).all()

    # 被相続人一覧のUIコンテナ
    deceased_list_container = ft.Column()

    # 被相続人の追加フィールド
    new_deceased_name_field = ft.TextField(label="新しい被相続人名", width=300)
    new_deceased_dob_field = ft.TextField(label="生年月日(YYYY-MM-DD)", width=200)

    # UIリストを更新する関数
    def update_deceased_list_ui():
        deceased_list_container.controls.clear()

        for deceased in get_deceased_list():
            # 詳細画面へ遷移するボタン
            detail_button = ft.IconButton(
                ft.Icons.ARROW_RIGHT,
                tooltip="詳細へ",
                on_click=lambda e, d_id=deceased.id: page.go(f"/detail/{d_id}")
            )

            # 削除ボタン
            delete_button = ft.IconButton(
                ft.Icons.DELETE,
                icon_color=ft.Colors.RED_500,
                data=deceased.id,
                on_click=delete_deceased
            )

            deceased_list_container.controls.append(
                ft.Row(
                    [
                        detail_button,
                        ft.Text(f"ID: {deceased.id} | 名前: {deceased.name} | 生年月日: {deceased.date_of_birth}"),
                        delete_button,
                    ],
                    # alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                )
            )
        page.update()

    # 被相続人を追加する関数
    def add_deceased(e):
        name = new_deceased_name_field.value.strip()
        dob = new_deceased_dob_field.value.strip()

        if name:
            new_deceased = Deceased(name=name, date_of_birth=dob)
            with Session(bind=Engine) as session:
                session.add(new_deceased)
                session.commit()

            new_deceased_name_field.value = ""
            new_deceased_dob_field.value = ""

            update_deceased_list_ui()

    # 被相続人を削除する関数
    def delete_deceased(e):
        deceased_id_to_delete = e.control.data
        with Session(bind=Engine) as session:
            # 相続人も含めてカスケード削除される (database.pyでcascade="all, delete-orphan"設定済み)
            deceased_to_delete = session.query(Deceased).get(deceased_id_to_delete)
            if deceased_to_delete:
                session.delete(deceased_to_delete)
                session.commit()

        update_deceased_list_ui()

    # 初期リストの表示
    update_deceased_list_ui()

    return ft.View(
        "/",
        [
            ft.AppBar(title=ft.Text("顧客管理システム (被相続人一覧)"), bgcolor=ft.Colors.BLUE_GREY_900),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("👨‍🦳 新しい被相続人を追加", size=16),
                        ft.Row(
                            [
                                new_deceased_name_field,
                                new_deceased_dob_field,
                                ft.ElevatedButton("追加", on_click=add_deceased),
                            ]
                        ),
                        ft.Divider(height=20),
                        ft.Text("📋 登録済み被相続人", size=16),
                        ft.Container(
                            content=deceased_list_container,
                            border=ft.border.all(1, ft.Colors.BLACK12),
                            padding=10,
                            width=page.width * 0.9
                        )
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.START
                ),
                padding=20
            ),
        ],
        scroll=ft.ScrollMode.AUTO
    )


def main(page: ft.Page):
    page.title = "顧客管理システム"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # ルーティングの処理
    def route_change(route):
        page.views.clear()

        # 1. メイン画面 (被相続人一覧)
        if page.route == "/":
            page.views.append(DeceasedListView(page))

        # 2. 詳細画面 (被相続人詳細/相続人管理)
        elif re.match(r"^/detail/(\d+)$", page.route):
            # URLからIDを抽出
            match = re.match(r"^/detail/(\d+)$", page.route)
            deceased_id = int(match.group(1))
            page.views.append(DeceasedDetailView(page, deceased_id))

        page.update()

    # 画面遷移時のイベントハンドラを設定
    page.on_route_change = route_change

    # ウィンドウの「戻る」ボタンなどが押されたときの処理 (Fletの標準的なルーティング設定)
    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_view_pop = view_pop

    # 初期画面へ移動
    page.go(page.route)


if __name__ == '__main__':
    ft.app(target=main)

# # main.py
#
# import flet as ft
# import re
# from sqlalchemy.orm import Session
# from database import init_db, add_initial_data, Engine, Deceased
# from deceased_detail_view import DeceasedDetailView
#
# # データベースの初期化とテストデータの追加
# init_db()
# add_initial_data()
#
#
# # 被相続人一覧表示（メイン）ビュー
# def DeceasedListView(page: ft.Page):
#     # データベースから全被相続人を取得
#     def get_deceased_list():
#         with Session(bind=Engine) as session:
#             return session.query(Deceased).all()
#
#     # 被相続人一覧のUIコンテナ
#     deceased_list_container = ft.Column()
#
#     # 被相続人の追加フィールド
#     new_deceased_name_field = ft.TextField(label="新しい被相続人名", width=300)
#     new_deceased_dob_field = ft.TextField(label="生年月日(YYYY-MM-DD)", width=200)
#
#     # UIリストを更新する関数
#     def update_deceased_list_ui():
#         deceased_list_container.controls.clear()
#
#         for deceased in get_deceased_list():
#             # 詳細画面へ遷移するボタン
#             detail_button = ft.IconButton(
#                 ft.Icons.ARROW_RIGHT,
#                 tooltip="詳細へ",
#                 on_click=lambda e, d_id=deceased.id: page.go(f"/detail/{d_id}")
#             )
#
#             # 削除ボタン
#             delete_button = ft.IconButton(
#                 ft.Icons.DELETE,
#                 icon_color=ft.Colors.RED_500,
#                 data=deceased.id,
#                 on_click=delete_deceased
#             )
#
#             deceased_list_container.controls.append(
#                 ft.Row(
#                     [
#                         ft.Text(f"ID: {deceased.id} | 名前: {deceased.name} | 生年月日: {deceased.date_of_birth}"),
#                         detail_button,
#                         delete_button,
#                     ],
#                     alignment=ft.MainAxisAlignment.SPACE_BETWEEN
#                 )
#             )
#         page.update()
#
#     # 被相続人を追加する関数
#     def add_deceased(e):
#         name = new_deceased_name_field.value.strip()
#         dob = new_deceased_dob_field.value.strip()
#
#         if name:
#             new_deceased = Deceased(name=name, date_of_birth=dob)
#             with Session(bind=Engine) as session:
#                 session.add(new_deceased)
#                 session.commit()
#
#             new_deceased_name_field.value = ""
#             new_deceased_dob_field.value = ""
#
#             update_deceased_list_ui()
#
#     # 被相続人を削除する関数
#     def delete_deceased(e):
#         deceased_id_to_delete = e.control.data
#         with Session(bind=Engine) as session:
#             # 相続人も含めてカスケード削除される (database.pyでcascade="all, delete-orphan"設定済み)
#             deceased_to_delete = session.query(Deceased).get(deceased_id_to_delete)
#             if deceased_to_delete:
#                 session.delete(deceased_to_delete)
#                 session.commit()
#
#         update_deceased_list_ui()
#
#     # 初期リストの表示
#     update_deceased_list_ui()
#
#     return ft.View(
#         "/",
#         [
#             ft.AppBar(title=ft.Text("顧客管理システム (被相続人一覧)"), bgcolor=ft.Colors.BLUE_GREY_900),
#             ft.Container(
#                 content=ft.Column(
#                     [
#                         ft.Text("👨‍🦳 新しい被相続人を追加", size=16),
#                         ft.Row(
#                             [
#                                 new_deceased_name_field,
#                                 new_deceased_dob_field,
#                                 ft.ElevatedButton("追加", on_click=add_deceased),
#                             ]
#                         ),
#                         ft.Divider(height=20),
#                         ft.Text("📋 登録済み被相続人", size=16),
#                         ft.Container(
#                             content=deceased_list_container,
#                             border=ft.border.all(1, ft.Colors.BLACK12),
#                             padding=10,
#                             width=page.width * 0.9
#                         )
#                     ],
#                     horizontal_alignment=ft.CrossAxisAlignment.START
#                 ),
#                 padding=20
#             ),
#         ],
#         scroll=ft.ScrollMode.AUTO
#     )
#
#
# def main(page: ft.Page):
#     page.title = "顧客管理システム"
#     page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
#
#     # ルーティングの処理
#     def route_change(route):
#         page.views.clear()
#
#         # 1. メイン画面 (被相続人一覧)
#         if page.route == "/":
#             page.views.append(DeceasedListView(page))
#
#         # 2. 詳細画面 (被相続人詳細/相続人管理)
#         elif re.match(r"^/detail/(\d+)$", page.route):
#             # URLからIDを抽出
#             match = re.match(r"^/detail/(\d+)$", page.route)
#             deceased_id = int(match.group(1))
#             page.views.append(DeceasedDetailView(page, deceased_id))
#
#         page.update()
#
#     # 画面遷移時のイベントハンドラを設定
#     page.on_route_change = route_change
#
#     # ウィンドウの「戻る」ボタンなどが押されたときの処理 (Fletの標準的なルーティング設定)
#     def view_pop(view):
#         page.views.pop()
#         top_view = page.views[-1]
#         page.go(top_view.route)
#
#     page.on_view_pop = view_pop
#
#     # 初期画面へ移動
#     page.go(page.route)
#
#
# if __name__ == '__main__':
#     ft.app(target=main)