# /components/pages/detail.py

import requests
from flet import (
    AlertDialog,
    AppBar,
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    Dropdown,
    ElevatedButton,
    FontWeight,
    IconButton,
    Icons,
    MainAxisAlignment,
    Page,
    Row,
    ScrollMode,
    Text,
    TextButton,
    TextField,
    View,
    border,
    dropdown,
)

from services import deceased_service
from services.db_setup import get_all_users
from services.deceased_service import get_address_info

# --- 1. モーダル編集で使用するフィールド定義 (DeceasedDetailView関数の外で定義) ---

# 氏名・基本情報
dialog_name_last_field = TextField(label="氏名 (姓)", width=150)
dialog_name_first_field = TextField(label="氏名 (名)", width=150)
dialog_kana_last_field = TextField(label="ふりがな (姓)", width=150)
dialog_kana_first_field = TextField(label="ふりがな (名)", width=150)
dialog_rel_field = TextField(label="続柄", width=200)

# 💡 追加: 担当者情報用のフィールド
# ユーザーリストを最初にロード
USER_MAP = get_all_users()
USER_OPTIONS = [dropdown.Option(str(id), name) for id, name in USER_MAP.items()]
USER_OPTIONS.insert(0, dropdown.Option(None, "未割当"))  # 未割当オプションを追加

dialog_manager_field = Dropdown(
    label="担当者1 (進捗管理)",
    width=200,
    options=USER_OPTIONS,
    # None (未割当) を許容するためデフォルトは None に近い値
    value=None,
)
dialog_operator_field = Dropdown(
    label="担当者2 (実務担当)", width=200, options=USER_OPTIONS, value=None
)

# 住所・本籍地
dialog_hometown_field = TextField(label="本籍地 (全体)")
dialog_zip_field = TextField(label="郵便番号", width=150)
dialog_pref_field = TextField(label="都道府県", width=150)
dialog_city_field = TextField(label="市区町村", width=200)
dialog_street_field = TextField(label="番地", width=150)
dialog_building_field = TextField(label="建物名・部屋番号")

# 日付
dialog_dob_field = TextField(label="生年月日 (YYYY-MM-DD)", width=180)
dialog_dod_field = TextField(label="死亡日 (YYYY-MM-DD)", width=180)

# タイトルコントロール
dialog_title_control = Text("情報編集", weight=FontWeight.BOLD)
# 追加: 案件番号入力フィールド
dialog_case_number_field = TextField(label="案件番号", width=250)


def DeceasedDetailView(page: Page, deceased_id: int):
    # --- サービス層からデータを取得 ---
    deceased = deceased_service.get_deceased_by_id(deceased_id)

    # 💡 案件情報を取得（担当者IDを取得するため）
    # deceasedオブジェクトがcaseへのリレーション（deceased.case）を持つと仮定
    case = None
    if deceased and deceased.case:
        case = deceased.case

    # 💡 新規モードのフラグを定義
    is_new_client_case = deceased_id == -1  # 新規案件（契約者登録）モード
    is_new_deceased = deceased_id == 0  # 被相続人単独の新規登録モード

    if is_new_client_case or is_new_deceased or deceased is None:
        # 新規登録の場合のデフォルト値
        full_name = "【未登録】新規登録が必要です"
        dob_str = "N/A"
        dod_str = "N/A"
        # モーダルを開くためにダミーのオブジェクトを使用（deceasedがNoneの場合もこれで安全になる）
        deceased = type(
            "DummyDeceased",
            (object,),
            {
                "name_last": "",
                "name_first": "",
                "name_last_kana": "",
                "name_first_kana": "",
                "date_of_birth": None,
                "date_of_death": None,
                "relationship_type": "本人",
                "hometown": "",
                "heirs": [],  # 相続人リストは空にしておく
                # 💡 注意: 他の箇所でアクセスされる可能性のある必要な属性を全て追加してください
            },
        )()

    else:
        full_name = f"{deceased.name_last} {deceased.name_first}"
        dob_str = str(deceased.date_of_birth) if deceased.date_of_birth else ""
        dod_str = str(deceased.date_of_death) if deceased.date_of_death else "未登録"
        # is_new_deceased は deceased_id=0 で処理

    # elif is_new_client_case or is_new_deceased:
    #     # 新規登録の場合のデフォルト値
    #     full_name = "【未登録】新規登録が必要です"
    #     dob_str = "N/A"
    #     dod_str = "N/A"
    #     # モーダルを開くためにダミーのオブジェクトを使用（モーダル内でデータは空でロードされる）
    #     deceased = type(
    #         "DummyDeceased",
    #         (object,),
    #         {
    #             "name_last": "",
    #             "name_first": "",
    #             "name_last_kana": "",
    #             "name_first_kana": "",
    #             "date_of_birth": None,
    #             "date_of_death": None,
    #             "relationship_type": "本人",
    #             "hometown": "",
    #             "heirs": [],  # 相続人リストは空にしておく
    #         },
    #     )()

    # else:
    #     # deceased_id が存在しない、かつ新規モードではない場合（通常は発生しない）
    #     # エラー処理やリダイレクトを追加することも可能
    #     pass

    heirs_controls = Column()
    new_heir_name_field = TextField(label="相続人名 (姓 名)", width=200)
    new_heir_rel_field = TextField(label="続柄", width=150)

    # --- 共通モーダル定義 ---
    def create_edit_dialog(is_deceased: bool):
        # 続柄フィールドは被相続人（本人）の場合は表示しない (簡易的なUI制御)
        rel_row = Row([dialog_rel_field])
        if is_deceased:
            rel_row.visible = False

        date_rows = [Row([dialog_dob_field])]
        if is_deceased:
            date_rows.append(Row([dialog_dod_field]))

        # 案件番号フィールドを相続人の基本情報の上に配置
        case_num_row = Row([dialog_case_number_field])
        if is_deceased:
            # 被相続人編集時は案件番号は表示しない（登録済みのため）
            case_num_row.visible = False

        # 💡 追加: 担当者選択行
        assignment_row = Row([dialog_manager_field, dialog_operator_field])

        # 被相続人情報編集時のみ表示（案件情報のため）
        if not is_deceased:
            # 相続人編集時は担当者情報は編集しない（案件情報のため）
            assignment_row.visible = False

        return AlertDialog(
            modal=True,
            title=dialog_title_control,
            content=Container(
                content=Column(
                    [
                        case_num_row,
                        assignment_row,
                        Divider(),
                        Text("基本情報", weight=FontWeight.BOLD),
                        Row([dialog_name_last_field, dialog_name_first_field]),
                        Row([dialog_kana_last_field, dialog_kana_first_field]),
                        rel_row,
                        *date_rows,
                        Divider(),
                        Text("住所情報", weight=FontWeight.BOLD),
                        Row([dialog_zip_field, dialog_pref_field, dialog_city_field]),
                        Row([dialog_street_field, dialog_building_field]),
                        Divider(),
                        dialog_hometown_field,
                        Text(
                            f"【タイプ: {'被相続人' if is_deceased else '相続人'}】",
                            color=Colors.BLUE_500,
                        ),
                    ],
                    scroll=ScrollMode.AUTO,
                    tight=True,
                    spacing=10,
                ),
                width=650,
                height=550,
            ),
            actions=[
                TextButton("キャンセル", on_click=lambda e: close_dialog()),
                ElevatedButton("保存", on_click=lambda e: save_dialog(is_deceased)),
            ],
            actions_alignment=MainAxisAlignment.END,
        )

    # モーダルインスタンスを生成
    heir_edit_dialog = create_edit_dialog(is_deceased=False)
    deceased_edit_dialog = create_edit_dialog(is_deceased=True)

    # --- モーダル制御関数 ---
    def close_dialog():
        # if page.dialog:
        if deceased_edit_dialog.open:
            deceased_edit_dialog.open = False
        elif heir_edit_dialog.open:
            heir_edit_dialog.open = False
        page.update()

    def save_dialog(is_deceased: bool):
        # 画面上のフィールドから値を取得 (簡易)
        case_number = dialog_case_number_field.value.strip()
        name = f"{dialog_name_last_field.value.strip()} {dialog_name_first_field.value.strip()}"
        kana_last = dialog_kana_last_field.value.strip()
        kana_first = dialog_kana_first_field.value.strip()
        zip_code = dialog_zip_field.value.strip()
        pref = dialog_pref_field.value.strip()
        city = dialog_city_field.value.strip()
        street = dialog_street_field.value.strip()
        building = dialog_building_field.value.strip()
        dob_value = dialog_dob_field.value.strip()
        dod_value = dialog_dod_field.value.strip()
        rel = dialog_rel_field.value.strip()
        hometown = dialog_hometown_field.value.strip()

        # 💡 追加: 担当者IDの取得
        # Dropdownの値がNone, "" (空文字), または "None" (文字列) の場合はNoneに変換
        manager_id = (
            int(dialog_manager_field.value)
            if dialog_manager_field.value
            and dialog_manager_field.value not in ("", "None")
            else None
        )
        operator_id = (
            int(dialog_operator_field.value)
            if dialog_operator_field.value
            and dialog_operator_field.value not in ("", "None")
            else None
        )

        if is_new_client_case:
            # 1. 契約者登録用の新規IDを発行 (deceased_id が実際のDB IDに更新される)
            # 💡 サービス関数は修正済みと仮定し、担当者IDを渡す
            new_deceased_id = deceased_service.add_new_case_for_client_registration(
                case_number=case_number,
                name=name,
                kana_last=kana_last,
                kana_first=kana_first,
                hometown=hometown,
                zip_code=zip_code,
                pref=pref,
                city=city,
                street=street,
                building=building,
                dob=dob_value,
                dod=dod_value,
                manager_id=manager_id,  # 💡 新規案件登録時に担当者IDを保存
                operator_id=operator_id,  # 💡 新規案件登録時に担当者IDを保存
            )

            # 新しいdeceased_idでリダイレクトし直す
            page.go(f"/detail/{new_deceased_id}")
            return  # ここで処理を終了

        # 2. 被相続人の情報保存 (is_deceased=True かつ 既存または単独新規(ID=0))
        elif is_deceased:
            # 💡 既存の被相続人更新、または単独の新規被相続人登録（deceased_id=0の時）

            current_deceased = deceased_service.get_deceased_by_id(deceased_id)

            # 既存案件の場合のみ、担当者情報を更新
            if current_deceased and current_deceased.case_id and deceased_id != 0:
                # 💡 追加: 案件の担当者情報を更新
                deceased_service.update_case_assignment(
                    case_id=current_deceased.case_id,
                    manager_id=manager_id,
                    operator_id=operator_id,
                )

            deceased_service.update_deceased(
                deceased_id,
                name,
                dob=dob_value,
                dod=dod_value,
                kana_last=kana_last,
                kana_first=kana_first,
                zip_code=zip_code,
                pref=pref,
                city=city,
                street=street,
                building=building,
            )

        # 3. 通常の相続人の情報保存 (is_deceased=False)
        else:
            heir_id = heir_edit_dialog.data

            # 💡 修正: heir_id が None の場合は新規追加として add_heir を呼び出す
            if heir_id is None:
                # 新規追加: 最新の add_heir 関数（全フィールド対応）を使用
                deceased_service.add_heir(
                    deceased_id=deceased_id,
                    name=name,
                    rel=rel,
                    kana_last=kana_last,
                    kana_first=kana_first,
                    dob=dob_value,
                    hometown=hometown,  # H_AddressHistory用
                    zip_code=zip_code,
                    pref=pref,
                    city=city,
                    street=street,
                    building=building,
                )
            else:
                # 既存の相続人更新
                deceased_service.update_heir(
                    heir_id,
                    name,
                    rel,
                    kana_last=kana_last,
                    kana_first=kana_first,
                    zip_code=zip_code,
                    pref=pref,
                    city=city,
                    street=street,
                    building=building,
                )

        close_dialog()

        # メイン画面の被相続人情報表示を更新するため、画面全体を再読み込み (または page.go(page.route))
        page.go(f"/detail/{deceased_id}")

    def open_deceased_dialog(e):
        """被相続人または新規案件（契約者）情報編集モーダルを開き、フィールドをロードする"""

        # サービスの関数を呼び出して最新の deceased オブジェクトを取得し、
        # CaseリレーションもEager Loadされる（前回の修正）
        current_deceased = deceased_service.get_deceased_by_id(deceased_id)

        # 案件情報オブジェクト
        case = (
            current_deceased.case
            if current_deceased and current_deceased.case
            else None
        )

        # 1. タイトルと新規モードの制御
        if is_new_client_case:
            dialog_title_control.value = "新規案件登録 (契約者情報)"
            dialog_case_number_field.visible = True  # 案件番号の入力
        elif is_new_deceased:
            dialog_title_control.value = "新規被相続人情報 登録"
            dialog_case_number_field.visible = (
                False  # 案件番号は不要 (CaseはID=0で後ほど生成)
            )
        else:
            dialog_title_control.value = "被相続人情報 編集"
            dialog_case_number_field.visible = False  # 既存案件では案件番号は表示しない

        # 2. 基本情報フィールドのロード
        # 新規登録時は空欄、既存の場合はデータを設定
        dialog_name_last_field.value = getattr(current_deceased, "name_last", "") or ""
        dialog_name_first_field.value = (
            getattr(current_deceased, "name_first", "") or ""
        )
        dialog_kana_last_field.value = (
            getattr(current_deceased, "name_last_kana", "") or ""
        )
        dialog_kana_first_field.value = (
            getattr(current_deceased, "name_first_kana", "") or ""
        )

        # 続柄フィールドは被相続人の編集時（is_deceased=True）には非表示
        # ※ create_edit_dialog 内で制御されているため、ここでは値のみ設定
        dialog_rel_field.value = getattr(current_deceased, "relationship_type", "本人")
        dialog_hometown_field.value = getattr(current_deceased, "hometown", "") or ""

        # 日付フィールド
        dialog_dob_field.value = (
            str(current_deceased.date_of_birth)
            if current_deceased.date_of_birth
            else ""
        )
        dialog_dod_field.value = (
            str(current_deceased.date_of_death)
            if current_deceased.date_of_death
            else ""
        )

        # 3. 担当者フィールド（Dropdown）の制御

        # 担当者行の可視性を取得（create_edit_dialogで定義されていると仮定）
        # モーダルのコンテンツ構造に依存するが、ここでは簡易的にモーダルインスタンスからアクセスすると仮定
        # (ただし、これはUI層の密結合となるため、is_deceasedフラグで制御が理想)

        is_deceased_edit_mode = (
            not is_new_client_case
        )  # 被相続人編集/単独新規モードの場合

        if is_deceased_edit_mode and case:
            # 既存案件の編集: 案件情報から担当者IDをロード
            dialog_manager_field.value = (
                str(case.manager_id) if case.manager_id else None
            )
            dialog_operator_field.value = (
                str(case.operator_id) if case.operator_id else None
            )

        elif is_new_client_case:
            # 新規契約者登録モード: 初期値は None
            dialog_manager_field.value = None
            dialog_operator_field.value = None

            # 案件番号フィールドを空にする (新規登録用)
            dialog_case_number_field.value = ""

        else:
            # その他（例えば deceased_id=0 の新規被相続人単独登録）
            dialog_manager_field.value = None
            dialog_operator_field.value = None

        # 4. 住所データをロード
        address_info = (
            get_address_info("deceased", deceased_id) if deceased_id > 0 else {}
        )
        dialog_zip_field.value = address_info.get("zip_code", "")
        dialog_pref_field.value = address_info.get("prefecture", "")
        dialog_city_field.value = address_info.get("city_ward_town", "")
        dialog_street_field.value = address_info.get("street_address", "")
        dialog_building_field.value = address_info.get("building_name", "")

        # 5. モーダルを開く
        page.open(deceased_edit_dialog)
        page.update()

        # # 被相続人データをロード
        # dialog_title_control.value = "被相続人情報 編集"

        # dialog_name_last_field.value = deceased.name_last
        # dialog_name_first_field.value = deceased.name_first
        # dialog_kana_last_field.value = getattr(deceased, "name_last_kana", "") or ""
        # dialog_kana_first_field.value = getattr(deceased, "name_first_kana", "") or ""
        # dialog_dob_field.value = (
        #     str(deceased.date_of_birth) if deceased.date_of_birth else ""
        # )
        # dialog_dod_field.value = (
        #     str(deceased.date_of_death) if deceased.date_of_death else ""
        # )
        # dialog_rel_field.value = getattr(deceased, "relationship_type", "本人")
        # dialog_hometown_field.value = getattr(deceased, "hometown", "") or ""

        # # 💡 追加: 担当者ドロップダウンの初期値を設定
        # case = deceased_service.get_deceased_by_id(
        #     deceased_id
        # ).case  # Caseオブジェクトの再取得 (リレーションがない場合を考慮)

        # if case:
        #     # IDを文字列に変換して設定 (Dropdownは文字列のvalueを期待)
        #     dialog_manager_field.value = (
        #         str(case.manager_id) if case.manager_id else None
        #     )
        #     dialog_operator_field.value = (
        #         str(case.operator_id) if case.operator_id else None
        #     )
        # else:
        #     # 新規案件/ケースなしの場合
        #     dialog_manager_field.value = None
        #     dialog_operator_field.value = None

        # # ★ 住所データを取得し、フィールドを更新 ★
        # address_info = (
        #     get_address_info("deceased", deceased_id) if not is_new_deceased else {}
        # )
        # dialog_zip_field.value = address_info.get("zip_code", "")
        # dialog_pref_field.value = address_info.get("prefecture", "")
        # dialog_city_field.value = address_info.get("city_ward_town", "")
        # dialog_street_field.value = address_info.get("street_address", "")
        # dialog_building_field.value = address_info.get("building_name", "")

        # page.open(deceased_edit_dialog)
        # page.update()

    def _on_mount(e):
        # 💡 修正箇所: 新規モードのロジックを優先順位でチェックする
        if is_new_client_case:
            # 1. 新規案件（契約者登録）モードの場合
            open_heir_dialog_for_new_client(None)
        elif is_new_deceased:
            # 2. 被相続人単独の新規登録モードの場合
            open_deceased_dialog(None)

        page.update()  # ページ更新を追加

    # 契約者（相続人）として新規登録するためのダイアログオープン関数
    def open_heir_dialog_for_new_client(e):
        """新規案件登録ボタンから呼ばれる、契約者情報入力用のモーダルを開く"""

        heir_edit_dialog.data = None  # 既存のIDがないことを示す
        dialog_title_control.value = "新規案件登録 (契約者情報)"

        # フィールドを空に設定
        dialog_case_number_field.value = ""
        dialog_name_last_field.value = ""
        dialog_name_first_field.value = ""
        dialog_kana_last_field.value = ""
        dialog_kana_first_field.value = ""
        # 続柄を「配偶者」など、デフォルトとして設定可能。ここでは空欄。
        dialog_rel_field.value = ""
        # 被相続人編集と共通のダイアログを使用するため、続柄フィールドを表示
        rel_row = heir_edit_dialog.content.content.controls[3]
        rel_row.visible = True

        # 住所フィールドも空に
        dialog_zip_field.value = ""
        dialog_pref_field.value = ""
        dialog_city_field.value = ""
        dialog_street_field.value = ""
        dialog_building_field.value = ""

        # 日付フィールドは被相続人の日付用
        dialog_dob_field.value = ""
        # 死亡日フィールドは非表示にしておく (被相続人情報ではないため)
        if len(heir_edit_dialog.content.content.controls[4].controls) > 1:
            heir_edit_dialog.content.content.controls[4].controls[1].visible = False

        page.open(heir_edit_dialog)
        page.update()

    def open_heir_dialog(e, heir_id: int):
        current_deceased = deceased_service.get_deceased_by_id(deceased_id)
        heir_to_edit = next(
            (h for h in current_deceased.heirs if h.id == heir_id), None
        )

        if heir_to_edit:
            heir_edit_dialog.data = heir_id
            dialog_title_control.value = (
                f"相続人情報 編集 ({heir_to_edit.name_last} {heir_to_edit.name_first})"
            )

            dialog_name_last_field.value = heir_to_edit.name_last
            dialog_name_first_field.value = heir_to_edit.name_first
            dialog_kana_last_field.value = heir_to_edit.name_last_kana or ""
            dialog_kana_first_field.value = heir_to_edit.name_first_kana or ""
            dialog_rel_field.value = heir_to_edit.relationship_type
            dialog_dob_field.value = (
                str(heir_to_edit.date_of_birth) if heir_to_edit.date_of_birth else ""
            )
            dialog_hometown_field.value = heir_to_edit.hometown or ""

            # ★ 住所データを取得し、フィールドを更新 ★
            address_info = get_address_info("heir", heir_id)
            dialog_zip_field.value = address_info.get("zip_code", "")
            dialog_pref_field.value = address_info.get("prefecture", "")
            dialog_city_field.value = address_info.get("city_ward_town", "")
            dialog_street_field.value = address_info.get("street_address", "")
            dialog_building_field.value = address_info.get("building_name", "")

            page.open(heir_edit_dialog)
            page.update()

    # --- 住所自動入力ロジック ---
    def search_address_by_zip(e):
        zip_code = dialog_zip_field.value.replace("-", "").strip()
        if len(zip_code) == 7 and zip_code.isdigit():
            try:
                api_url = f"https://zipcloud.ibsnet.co.jp/api/search?zipcode={zip_code}"
                response = requests.get(api_url)
                data = response.json()
                if data and data.get("results"):
                    address_data = data["results"][0]
                    dialog_pref_field.value = address_data["address1"]
                    dialog_city_field.value = address_data["address2"]
                    dialog_street_field.value = address_data["address3"]
                    page.update()
                else:
                    dialog_pref_field.value = "住所が見つかりません"
                    dialog_city_field.value = ""
                    dialog_street_field.value = ""
                    page.update()
            except Exception as ex:
                print(f"APIエラー: {ex}")
        dialog_street_field.focus()

    dialog_zip_field.on_blur = search_address_by_zip

    # --- 3. 相続人リストの表示ロジック ---
    def update_heirs_list():
        heirs_controls.controls.clear()
        current_deceased = deceased_service.get_deceased_by_id(deceased_id)

        if current_deceased is None:
            # 被相続人が存在しない（新規モード）場合、相続人リストは更新せずに終了
            page.update()
            return

        for heir in current_deceased.heirs:
            heir_full_name = f"{heir.name_last} {heir.name_first}"

            heirs_controls.controls.append(
                Row(
                    [
                        Text(f"ID:{heir.id}", width=50),
                        Text(f"名前: {heir_full_name}", width=200),
                        Text(f"続柄: {heir.relationship_type}", width=150),
                        IconButton(
                            Icons.EDIT,
                            icon_color=Colors.BLUE_500,
                            data=heir.id,
                            on_click=lambda e, h_id=heir.id: open_heir_dialog(e, h_id),
                        ),
                        IconButton(
                            Icons.DELETE,
                            icon_color=Colors.RED_500,
                            data=heir.id,
                            on_click=delete_heir,
                        ),
                    ],
                    alignment=MainAxisAlignment.START,
                )
            )
        page.update()

    # --- 4. 追加/削除ロジック ---
    def add_heir(e):
        name = new_heir_name_field.value.strip()
        rel = new_heir_rel_field.value.strip()
        if name:
            deceased_service.add_heir(deceased_id, name, rel)
            new_heir_name_field.value = ""
            new_heir_rel_field.value = ""
            update_heirs_list()

    def delete_heir(e):
        heir_id_to_delete = e.control.data
        deceased_service.delete_heir(heir_id_to_delete)
        update_heirs_list()

    # 初期リストの表示
    update_heirs_list()

    # View の定義
    view_controls = [
        AppBar(title=Text("被相続人 詳細/相続人管理"), bgcolor=Colors.BLUE_GREY_700),
        Container(
            content=Column(
                [
                    Row(
                        [
                            Text(
                                "👤 被相続人情報 ✏️ ",
                                size=18,
                                weight=FontWeight.BOLD,
                            ),
                            Text(
                                "【新規登録モード】",
                                size=16,
                                color=Colors.RED_500,
                                visible=is_new_deceased,
                            ),
                        ]
                    ),
                    Row(
                        [
                            Text(
                                f"名前: {full_name}",
                                weight=FontWeight.BOLD,
                                size=16,
                                width=200,
                            ),
                            Text(f"生年月日: {dob_str}", size=14, width=150),
                            Text(f"死亡日: {dod_str}", size=14, width=150),
                            IconButton(
                                Icons.EDIT,
                                icon_color=Colors.BLUE_500,
                                tooltip="被相続人を編集",
                                on_click=open_deceased_dialog,
                            ),
                        ],
                        alignment=MainAxisAlignment.START,
                    ),
                    Divider(),
                    # 被相続人未登録の場合は相続人セクションを非表示にする
                    Column(
                        [
                            Text(
                                "👨‍👩‍👧‍👦 相続人リスト (編集ボタンで全詳細情報モーダルが開きます)",
                                size=16,
                            ),
                            Container(
                                content=heirs_controls,
                                border=border.all(1, Colors.BLACK12),
                                padding=10,
                                width=page.width * 0.8,
                            ),
                            Divider(),
                            Text("新しい相続人の追加", size=16),
                            Row(
                                [
                                    new_heir_name_field,
                                    new_heir_rel_field,
                                    ElevatedButton(
                                        "追加", on_click=lambda e: add_heir(e)
                                    ),
                                ]
                            ),
                        ],
                        # visible=not is_new_deceased,  # 新規登録時は非表示
                        # 新規案件モード（-1）または単独新規被相続人モード（0）では非表示
                        visible=not is_new_deceased and not is_new_client_case,
                    ),
                    Divider(),
                    ElevatedButton("👈 一覧へ戻る", on_click=lambda e: page.go("/")),
                ],
                horizontal_alignment=CrossAxisAlignment.START,
            ),
            padding=20,
        ),
    ]

    view = View(
        f"/detail/{deceased_id}",
        view_controls,
        scroll=ScrollMode.AUTO,
    )

    # ページがマウントされた時に自動でモーダルを開く設定
    view.on_view_show = _on_mount

    # 💡 追加: 新規登録時、on_view_showが遅延またはスキップされる場合に備えて、
    #         手動で_on_mountを起動し、モーダルを開く処理を強制実行する。
    if is_new_client_case or is_new_deceased:
        _on_mount(None)

    # 初期リストの表示 (新規の場合、heirs_controlsは空のまま)
    if (
        not is_new_deceased and not is_new_client_case
    ):  # 💡 修正: 新規モードの場合はリスト更新をスキップ
        update_heirs_list()

    return view
