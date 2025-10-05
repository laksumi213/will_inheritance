# /components/pages/home.py

from flet import (
    AppBar,
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    IconButton,
    Icons,
    Page,
    Row,
    ScrollMode,
    Text,
    View,
    border,
)

# from components.common.custom_text import CustomText
from components.common.custom_elevatedbutton import CustomElevatedButton
from components.common.custom_textfield import CustomTextField
from services import deceased_service  # サービス層からデータ操作関数をインポート


# 被相続人一覧表示（メイン）ビュー
def DeceasedListView(page: Page):
    # UI要素の定義
    deceased_list_container = Column()
    new_deceased_name_field = CustomTextField(label="新しい被相続人名", width=250)
    new_deceased_dob_field = CustomTextField(label="生年月日(YYYY-MM-DD)", width=250)

    # UIリストを更新する関数
    def update_deceased_list_ui():
        deceased_list_container.controls.clear()

        # サービス層からデータを取得
        for deceased in deceased_service.get_all_deceased():
            # 詳細画面へ遷移するボタン
            detail_button = IconButton(
                Icons.ARROW_RIGHT,
                tooltip="詳細へ",
                on_click=lambda e, d_id=deceased.id: page.go(f"/detail/{d_id}"),
            )

            # 削除ボタン
            delete_button = IconButton(
                Icons.DELETE,
                icon_color=Colors.RED_500,
                data=deceased.id,
                on_click=delete_deceased,
            )

            deceased_list_container.controls.append(
                Row(
                    [
                        detail_button,
                        Text(
                            f"ID: {deceased.id} | 名前: {deceased.name} | 生年月日: {deceased.date_of_birth}"
                        ),
                        delete_button,
                    ],
                )
            )
        page.update()

    # 被相続人を追加する関数 (ロジックはサービス層へ)
    def add_deceased(e):
        name = new_deceased_name_field.value.strip()
        dob = new_deceased_dob_field.value.strip()

        if name:
            deceased_service.add_deceased(name, dob)  # サービスを呼び出す

            new_deceased_name_field.value = ""
            new_deceased_dob_field.value = ""

            update_deceased_list_ui()

    # 被相続人を削除する関数 (ロジックはサービス層へ)
    def delete_deceased(e):
        deceased_id_to_delete = e.control.data
        deceased_service.delete_deceased(deceased_id_to_delete)  # サービスを呼び出す
        update_deceased_list_ui()

    # 初期リストの表示
    update_deceased_list_ui()

    # View の定義
    return View(
        "/",
        [
            AppBar(
                title=Text("顧客管理システム (被相続人一覧)"),
                bgcolor=Colors.BLUE_GREY_900,
            ),
            Container(
                content=Column(
                    [
                        Text("👨‍🦳 新しい被相続人を追加", size=16),
                        Row(
                            [
                                new_deceased_name_field,
                                new_deceased_dob_field,
                                CustomElevatedButton("追加", on_click=add_deceased),
                            ]
                        ),
                        Divider(height=20),
                        Text("📋 登録済み被相続人", size=16),
                        Container(
                            content=deceased_list_container,
                            border=border.all(1, Colors.BLACK12),
                            padding=10,
                            width=page.width * 0.9,
                        ),
                    ],
                    horizontal_alignment=CrossAxisAlignment.START,
                ),
                padding=20,
            ),
        ],
        scroll=ScrollMode.AUTO,
    )
