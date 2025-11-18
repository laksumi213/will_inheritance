# components/pages/client_register.py

from flet import (
    AppBar,
    Colors,
    Column,
    Container,
    Divider,
    Dropdown,
    ElevatedButton,
    FilePicker,
    FilePickerResultEvent,
    FontWeight,
    Icons,
    MainAxisAlignment,
    Page,
    Row,
    ScrollMode,
    SnackBar,
    Text,
    TextField,
    View,
    dropdown,
)

# ★ 共通コントロールをインポート ★
from components.utils.contact_controls import (
    add_new_contact_row,
    collect_contacts,
    create_contact_input_row,
)
from services import deceased_service
from services.db_setup import get_all_users
from services.deceased_service import (
    add_new_case_for_client_registration,
    get_case_id_by_deceased_id,
    get_next_case_number_service,
    update_case_folder_path,
)

# --- グローバルな UI 定義 ---

USER_MAP = get_all_users()
USER_OPTIONS = [dropdown.Option(str(id), name) for id, name in USER_MAP.items()]
USER_OPTIONS.insert(0, dropdown.Option("", "未割当"))

# --- フォームコントロールの定義 ---

# 案件情報
case_number_field = TextField(
    label="案件番号 *",
    width=200,
    value=get_next_case_number_service(),  # サービスラッパーを使用
    read_only=False,  # 編集可能
)
manager_field = Dropdown(label="担当者1", width=200, options=USER_OPTIONS)
operator_field = Dropdown(label="担当者2", width=200, options=USER_OPTIONS)

# 契約者情報 (Heirとして登録)
name_last_field = TextField(label="契約者氏名 (姓) *", width=150, autofocus=True)
name_first_field = TextField(label="契約者氏名 (名)", width=150)
kana_last_field = TextField(label="ふりがな (姓)", width=150)
kana_first_field = TextField(label="ふりがな (名)", width=150)
rel_field = TextField(label="被相続人との続柄", width=200)  # 必須チェックから除外済み
hometown_field = TextField(label="本籍地 (契約者)")

# 住所情報
zip_field = TextField(label="郵便番号", width=150)
pref_field = TextField(label="都道府県", width=150)
city_field = TextField(label="市区町村", width=200)
street_field = TextField(label="番地", width=150)
building_field = TextField(label="建物名・部屋番号")

# 💡 フォルダパス入力フィールド
path_field = TextField(
    label="フォルダ保存パス",
    width=500,
    read_only=True,
    value="",
)


# 連絡先入力の初期化ヘルパー (create_contact_input_row に依存)
def initialize_contact_column(is_email: bool) -> Column:
    column = Column(controls=[], spacing=5)
    # デフォルトで空の入力行を1つ追加 (共通関数を使用)
    new_row, _ = create_contact_input_row(column, initial_value="", is_email=is_email)
    column.controls.append(new_row)
    return column


# 💡 グローバルスコープで Column を初期化
phone_inputs_column = initialize_contact_column(is_email=False)
email_inputs_column = initialize_contact_column(is_email=True)


# --- メインの View 関数 ---


def ClientRegisterView(page: Page):
    # 【★ FilePicker の定義とオーバーレイへの追加 ★】
    # 案件全体で一つあれば良い
    file_picker = FilePicker(on_result=lambda e: page.update())
    if file_picker not in page.overlay:
        page.overlay.append(file_picker)
    page.update()

    # ----------------------------------------------------
    # FilePicker 結果ハンドラ
    # ----------------------------------------------------
    def get_directory_result(e: FilePickerResultEvent):
        # 結果を path_field (グローバル変数) に反映
        path_field.value = e.path if e.path else "パス設定をキャンセルしました"
        page.update()

    # フォルダ選択ダイアログを開く
    def open_folder_dialog(e):
        file_picker.on_result = get_directory_result
        file_picker.get_directory_path(dialog_title="案件フォルダの保存先を選択")

    # 担当者IDの取得ヘルパー
    def _get_id_from_dropdown(value):
        if value is None or value in ("", "None", "未割当"):
            return None
        try:
            return int(value)
        except ValueError:
            return None

    # 住所自動入力ロジック
    def search_address_by_zip(e):
        zip_code = zip_field.value
        address_info = deceased_service.search_address_by_zip_api(zip_code)

        if address_info is None:
            pref_field.value = "通信エラー"
            city_field.value = ""
            street_field.value = ""
        elif address_info == {}:
            pref_field.value = "住所が見つかりません"
            city_field.value = ""
            street_field.value = ""
        else:
            pref_field.value = address_info.get("prefecture", "")
            city_field.value = address_info.get("city_ward_town", "")
            street_field.value = address_info.get("street_address", "")

        page.update()
        street_field.focus()

    zip_field.on_blur = search_address_by_zip

    # --- 保存処理 ---
    def save_and_go_to_detail(e):
        case_num_input = case_number_field.value.strip()
        name_last_input = name_last_field.value.strip()
        new_path = path_field.value.strip()

        # 1. 必須項目チェック (案件番号, 契約者氏名(姓))
        if not case_num_input or not name_last_input:
            page.open(
                SnackBar(
                    content=Text(
                        "必須項目（案件番号、契約者氏名(姓)）を入力してください。",
                        color=Colors.WHITE,
                    ),
                    bgcolor=Colors.RED_700,
                    duration=3000,
                )
            )
            page.update()
            return

        # 2. 案件番号の重複チェック
        if deceased_service.is_case_number_duplicate(case_num_input):
            page.open(
                SnackBar(
                    content=Text(
                        f"案件番号 '{case_num_input}' は既に存在しますので、次の番号を自動で入力しました。",
                        color=Colors.WHITE,
                    ),
                    bgcolor=Colors.RED_700,
                    duration=3000,
                )
            )
            case_number_field.value = get_next_case_number_service()
            case_number_field.focus()
            page.update()
            return

        # 3. 連絡先情報の収集
        collected_data = {
            "phone_contacts": collect_contacts(phone_inputs_column),
            "email_contacts": collect_contacts(email_inputs_column),
        }

        # 4. サービス層呼び出しとデータベース登録
        try:
            new_deceased_id = add_new_case_for_client_registration(
                case_number=case_num_input,
                name=f"{name_last_input} {name_first_field.value.strip()}",
                kana_last=kana_last_field.value.strip(),
                kana_first=kana_first_field.value.strip(),
                rel=rel_field.value.strip(),
                hometown=hometown_field.value.strip(),
                zip_code=zip_field.value.strip(),
                pref=pref_field.value.strip(),
                city=city_field.value.strip(),
                street=street_field.value.strip(),
                building=building_field.value.strip(),
                dob=None,
                dod=None,
                manager_id=_get_id_from_dropdown(manager_field.value),
                operator_id=_get_id_from_dropdown(operator_field.value),
                phone_contacts=collected_data["phone_contacts"],
                email_contacts=collected_data["email_contacts"],
            )

            if new_deceased_id > 0:
                case_id_for_path = get_case_id_by_deceased_id(new_deceased_id)

                # 4-1. フォルダパスの更新
                if (
                    case_id_for_path
                    and new_path
                    and new_path != "パス設定をキャンセルしました"
                ):
                    path_to_save = new_path if new_path else None
                    update_case_folder_path(
                        case_id=case_id_for_path,
                        folder_path=path_to_save,
                    )

                # 5. 成功通知と画面遷移
                page.open(
                    SnackBar(
                        content=Text("新規案件を登録しました。", color=Colors.WHITE),
                        bgcolor=Colors.GREEN_700,
                        duration=1500,
                    )
                )
                page.go(f"/detail/{new_deceased_id}")
            else:
                raise Exception(
                    "データベース登録に失敗しました。（サービス関数が負のIDを返しました）"
                )

        except Exception as ex:
            print(f"保存エラー: {ex}")
            page.open(
                SnackBar(
                    content=Text(
                        f"保存中にエラーが発生しました: {ex}", color=Colors.WHITE
                    ),
                    bgcolor=Colors.RED_700,
                    duration=3000,
                )
            )
            page.update()

    # --- UI レイアウト構築 ---
    return View(
        "/client_register",
        [
            AppBar(
                title=Text("✨ 新規案件登録 (契約者情報のみ)"),
                bgcolor=Colors.BLUE_GREY_700,
            ),
            Container(
                padding=30,
                content=Column(
                    [
                        Text("案件情報", weight=FontWeight.BOLD, size=18),
                        Row([case_number_field, manager_field, operator_field]),
                        Divider(),
                        Text(
                            "👤 契約者（依頼者）情報 *", weight=FontWeight.BOLD, size=18
                        ),
                        Row([name_last_field, name_first_field]),
                        Row([kana_last_field, kana_first_field]),
                        Row([rel_field]),
                        Row([hometown_field]),
                        Divider(),
                        Text("📞 連絡先情報", weight=FontWeight.BOLD, size=18),
                        # 電話番号の追加セクション
                        Row(
                            [
                                Text("電話番号", size=14, weight=FontWeight.W_500),
                                ElevatedButton(
                                    "追加",
                                    icon=Icons.ADD,
                                    on_click=lambda e: add_new_contact_row(
                                        e, phone_inputs_column, is_email=False
                                    ),
                                ),
                            ],
                            alignment=MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        phone_inputs_column,
                        # メールアドレスの追加セクション
                        Row(
                            [
                                Text(
                                    "メールアドレス", size=14, weight=FontWeight.W_500
                                ),
                                ElevatedButton(
                                    "追加",
                                    icon=Icons.ADD,
                                    on_click=lambda e: add_new_contact_row(
                                        e, email_inputs_column, is_email=True
                                    ),
                                ),
                            ],
                            alignment=MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        email_inputs_column,
                        Divider(),
                        Text("🏠 現住所", weight=FontWeight.BOLD, size=18),
                        Row([zip_field, pref_field, city_field]),
                        Row([street_field, building_field]),
                        Divider(height=30),
                        # 【★ フォルダパス設定 UI の組み込み ★】
                        Text("📁 案件フォルダ設定", weight=FontWeight.BOLD, size=18),
                        Row(
                            [
                                path_field,
                                ElevatedButton(
                                    "フォルダ選択",
                                    icon=Icons.FOLDER_OPEN,
                                    on_click=open_folder_dialog,
                                ),
                            ]
                        ),
                        Divider(height=30),
                        Row(
                            [
                                ElevatedButton(
                                    "キャンセル", on_click=lambda e: page.go("/")
                                ),
                                ElevatedButton(
                                    "保存して詳細へ進む",
                                    on_click=save_and_go_to_detail,
                                    icon=Icons.SAVE,
                                    bgcolor=Colors.BLUE_600,
                                ),
                            ],
                            alignment=MainAxisAlignment.END,
                            spacing=15,
                        ),
                    ]
                ),
            ),
        ],
        scroll=ScrollMode.AUTO,
    )

def reset_all_global_fields():
    """ホーム画面からの遷移時に、全てのグローバルな入力フィールドとリストをクリアする"""
    
    # 案件情報フィールドのリセット (案件番号はサービスから最新のものを再取得)
    case_number_field.value = get_next_case_number_service()
    manager_field.value = ""
    operator_field.value = ""
    
    # 契約者情報フィールドのリセット
    name_last_field.value = ""
    name_first_field.value = ""
    kana_last_field.value = ""
    kana_first_field.value = ""
    rel_field.value = ""
    hometown_field.value = ""
    
    # 住所情報フィールドのリセット
    zip_field.value = ""
    pref_field.value = ""
    city_field.value = ""
    street_field.value = ""
    building_field.value = ""
    
    # フォルダパスのリセット
    path_field.value = ""
    
    # 連絡先リストをクリアし、デフォルトの空の行を1つ再追加
    # NOTE: UI上から controls を削除するだけでは、リストをきれいに初期化できないため、
    # 既存の initialize_contact_column ロジックを流用し、リストを再構築します。
    
    # 既存の Column オブジェクト自体をクリアし、新しいコントロールで上書き
    phone_inputs_column.controls.clear()
    new_row_p, _ = create_contact_input_row(phone_inputs_column, initial_value="", is_email=False)
    phone_inputs_column.controls.append(new_row_p)
    
    email_inputs_column.controls.clear()
    new_row_e, _ = create_contact_input_row(email_inputs_column, initial_value="", is_email=True)
    email_inputs_column.controls.append(new_row_e)