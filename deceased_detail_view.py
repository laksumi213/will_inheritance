# deceased_detail_view.py

import flet as ft
from sqlalchemy.orm import Session
from database import Engine, Deceased, Heir


def DeceasedDetailView(page: ft.Page, deceased_id: int):
    # データベースセッションの開始
    session = Session(bind=Engine)
    deceased = session.query(Deceased).get(deceased_id)

    if not deceased:
        # データがない場合の処理
        return ft.View(
            "/detail",
            [
                ft.AppBar(title=ft.Text("エラー"), bgcolor=ft.Colors.BLUE_GREY_900),
                ft.Text("指定された被相続人が見つかりません。", size=16),
                ft.ElevatedButton("一覧に戻る", on_click=lambda e: page.go("/")),
            ]
        )

    # UI要素の準備
    heirs_controls = ft.Column()
    new_heir_name_field = ft.TextField(label="相続人名", width=200)
    new_heir_rel_field = ft.TextField(label="続柄", width=150)

    # 相続人リストを更新する関数
    def update_heirs_list():
        heirs_controls.controls.clear()

        # データベースから最新の相続人を取得
        current_deceased = session.query(Deceased).get(deceased_id)

        for heir in current_deceased.heirs:
            heirs_controls.controls.append(
                ft.Row(
                    [
                        ft.Text(f"名前: {heir.name}, 続柄: {heir.relationship_name}"),
                        ft.IconButton(
                            ft.Icons.DELETE,
                            icon_color=ft.Colors.RED_500,
                            data=heir.id,
                            on_click=delete_heir
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                )
            )
        page.update()

    # 相続人を追加する関数
    def add_heir(e):
        name = new_heir_name_field.value.strip()
        rel = new_heir_rel_field.value.strip()

        if name:
            new_heir = Heir(name=name, relationship_name=rel, deceased_id=deceased_id)
            session.add(new_heir)
            session.commit()

            new_heir_name_field.value = ""
            new_heir_rel_field.value = ""

            update_heirs_list()  # リストを更新

    # 相続人を削除する関数
    def delete_heir(e):
        heir_id_to_delete = e.control.data
        heir_to_delete = session.query(Heir).get(heir_id_to_delete)
        if heir_to_delete:
            session.delete(heir_to_delete)
            session.commit()
            update_heirs_list()  # リストを更新

    # 初期リストの表示
    update_heirs_list()

    # Fletのビュー構成
    return ft.View(
        f"/detail/{deceased_id}",
        [
            ft.AppBar(title=ft.Text("被相続人 詳細/相続人管理"), bgcolor=ft.Colors.BLUE_GREY_700),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(f"被相続人名: {deceased.name}", weight=ft.FontWeight.BOLD, size=18),
                        ft.Text(f"生年月日: {deceased.date_of_birth}"),
                        ft.Divider(),
                        ft.Text("👨‍👩‍👧‍👦 相続人リスト", size=16),
                        ft.Container(
                            content=heirs_controls,
                            border=ft.border.all(1, ft.Colors.BLACK12),
                            padding=10,
                            width=page.width * 0.8
                        ),

                        ft.Divider(),
                        ft.Text("新しい相続人の追加", size=16),
                        ft.Row(
                            [
                                new_heir_name_field,
                                new_heir_rel_field,
                                ft.ElevatedButton("追加", on_click=add_heir),
                            ]
                        ),
                        ft.Divider(),
                        ft.ElevatedButton("👈 一覧へ戻る", on_click=lambda e: page.go("/")),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=20
            ),
        ],
        scroll=ft.ScrollMode.AUTO
    )