# src/views/client_register.py
import re
import datetime
from typing import Dict, List, Optional, Any

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
    Icon,
    Icons,
    Page,
    ProgressRing,
    Row,
    ScrollMode,
    SnackBar,
    Text,
    TextField,
    View,
    border,
    padding,
    ButtonStyle,
    alignment,
    dropdown,
    MainAxisAlignment,
    Control,
    Chip,
)

# 共通設定とモデル
from src.config import settings
from src.models.database import SessionLocal
from src.models.tables import Case

# サービス層
from src.services.deceased_service import (
    add_new_case_for_client_registration,
    get_all_users,
    get_case_id_by_deceased_id,
    get_next_case_number_service,
    update_case_folder_path,
    search_address_by_zip_api,
    search_zip_by_address_api,
    is_case_number_duplicate,
)
from src.services.ai_service import ai_service

# 日付ユーティリティ
from src.utils.date_utils import on_date_blur_handler

from src.components.business.contact_controls import (
    add_new_contact_row,
    collect_contacts,
    create_contact_input_row,
)


class ClientRegisterView(View):
    """新規案件（顧客）登録画面 View"""

    def __init__(self, page: Page) -> None:
        super().__init__(route="/client_register", scroll=ScrollMode.AUTO)
        self.page: Page = page
        
        # --- 初期データのロード ---
        try:
            self.user_map: Dict[int, str] = get_all_users()
        except Exception:
            self.user_map = {}

        # Dropdown用オプション生成
        self.user_options: List[dropdown.Option] = [
            dropdown.Option(str(uid), name) for uid, name in self.user_map.items()
        ]
        self.user_options.insert(0, dropdown.Option("", "未割当"))

        # --- UIコンポーネントの初期化 ---
        self._init_components()
        
        # --- レイアウト構築 ---
        self.appbar = AppBar(
            title=Text("✨ 新規案件登録"),
            bgcolor="surfaceVariant", # テーマ追従
            color="onSurfaceVariant",
        )

        self.controls = [
            Container(
                padding=padding.all(30),
                expand=True,
                content=Column(
                    controls=[
                        Text("新しい相続案件を登録します。", size=16, weight=FontWeight.BOLD),
                        
                        # 1. AI自動入力セクション
                        self._create_ai_section(),
                        Divider(height=20, color=Colors.TRANSPARENT),

                        # 2. 案件情報
                        Text("案件情報", weight=FontWeight.BOLD, size=18, color="primary"),
                        Row([self.case_number_field, self.manager_field, self.operator_field]),
                        Divider(),

                        # 3. 契約者情報
                        Text("👤 契約者（依頼者）情報 *", weight=FontWeight.BOLD, size=18, color="primary"),
                        Row([self.name_last_field, self.name_first_field]),
                        Row([self.kana_last_field, self.kana_first_field]),
                        Row([self.rel_field]),
                        Row([self.hometown_field]),
                        Divider(),

                        # 4. 連絡先情報
                        Text("📞 連絡先情報", weight=FontWeight.BOLD, size=18, color="primary"),
                        self._create_phone_section(),
                        self.phone_inputs_column,
                        self._create_email_section(),
                        self.email_inputs_column,
                        Divider(),

                        # 5. 現住所
                        Text("🏠 現住所", weight=FontWeight.BOLD, size=18, color="primary"),
                        # 住所貼り付けフィールド
                        self.paste_address_field,
                        # AI候補表示エリア
                        self.candidate_container,
                        
                        Row([self.zip_field, self.pref_field, self.city_field]),
                        Row([self.street_field, self.building_field]),
                        Divider(height=30),

                        # 6. フォルダパス
                        Text("📁 案件フォルダ設定", weight=FontWeight.BOLD, size=18, color="primary"),
                        Row([
                            self.path_field,
                            ElevatedButton(
                                "フォルダ選択",
                                icon=Icons.FOLDER_OPEN,
                                on_click=self.open_folder_dialog,
                                bgcolor="secondaryContainer",
                                color="onSecondaryContainer",
                            ),
                        ]),
                        
                        Divider(height=30, thickness=2),

                        # 7. 紹介・SOL連携情報
                        Container(
                            content=Column([
                                Row([
                                    Icon(Icons.NEW_RELEASES, color="tertiary"), 
                                    Text("紹介・SOL連携情報", weight=FontWeight.BOLD, size=18, color="onTertiaryContainer")
                                ]),
                                Row([self.sol_case_number, self.introduction_date, self.consent_date], wrap=True),
                                Row([self.sec_branch_name, self.sec_rep_name], wrap=True),
                            ], spacing=15),
                            padding=15,
                            bgcolor="tertiaryContainer",
                            border_radius=8,
                            border=border.all(1, "tertiary")
                        ),

                        Divider(height=30),

                        # 8. アクションボタン
                        Row(
                            controls=[
                                ElevatedButton(
                                    "キャンセル", 
                                    on_click=lambda e: self.page.go("/"),
                                    bgcolor="surfaceVariant",
                                    color="onSurfaceVariant",
                                ),
                                ElevatedButton(
                                    "保存して詳細へ進む",
                                    on_click=self.save_and_go_to_detail,
                                    icon=Icons.SAVE,
                                    style=ButtonStyle(
                                        bgcolor={"": "primary"},
                                        color={"": "onPrimary"},
                                        padding=20
                                    ),
                                ),
                            ],
                            alignment=MainAxisAlignment.END,
                            spacing=15,
                        ),
                    ],
                    scroll=ScrollMode.AUTO,
                    spacing=15,
                ),
            )
        ]

    def _init_components(self) -> None:
        """UIコンポーネントの定義"""
        self.file_picker = FilePicker(on_result=self.on_file_picked)
        self.folder_picker = FilePicker(on_result=self.get_directory_result)
        self.page.overlay.extend([self.file_picker, self.folder_picker])

        # 案件情報
        self.case_number_field = TextField(
            label="案件番号 *",
            width=200,
            value=get_next_case_number_service(),
            read_only=False,
        )

        # 担当者1の初期値設定
        default_manager_id = ""
        for uid, name in self.user_map.items():
            if "管理者 太郎" in name:
                default_manager_id = str(uid)
                break

        self.manager_field = Dropdown(
            label="担当者1", 
            width=200, 
            options=self.user_options,
            value=default_manager_id
        )
        self.operator_field = Dropdown(label="担当者2", width=200, options=self.user_options)

        # 契約者情報
        self.name_last_field = TextField(label="契約者氏名 (姓) *", width=150)
        self.name_first_field = TextField(label="契約者氏名 (名)", width=150)
        self.kana_last_field = TextField(label="ふりがな (姓)", width=150)
        self.kana_first_field = TextField(label="ふりがな (名)", width=150)
        self.rel_field = TextField(label="被相続人との続柄", width=200)
        self.hometown_field = TextField(label="本籍地 (契約者)")

        # 住所情報
        self.paste_address_field = TextField(
            label="📍 住所貼り付け (ここに入力すると自動分割されます)",
            width=600,
            on_change=self.parse_and_fill_address,
            text_size=13,
            color="onSecondaryContainer",
            bgcolor="secondaryContainer",
            border_color=Colors.TRANSPARENT,
            hint_text="都道府県がない場合、AIが補完します"
        )
        # AI候補表示エリア
        self.candidate_chips_row = Row(wrap=True, spacing=5)
        self.candidate_container = Container(
            content=Column([
                Text("💡 都道府県が見つかりませんでした。以下から選択してください:", size=12, color=Colors.ORANGE_900),
                self.candidate_chips_row
            ], spacing=5),
            visible=False,
            bgcolor=Colors.ORANGE_50,
            padding=10,
            border_radius=5,
            border=border.all(1, Colors.ORANGE_200)
        )

        self.zip_field = TextField(label="郵便番号", width=150, on_blur=self.search_address_by_zip)
        self.pref_field = TextField(label="都道府県", width=150, on_blur=self.search_zip_by_address)
        self.city_field = TextField(label="市区町村", width=200, on_blur=self.search_zip_by_address)
        self.street_field = TextField(label="番地", width=150, on_blur=self.search_zip_by_address)
        self.building_field = TextField(label="建物名・部屋番号")

        # フォルダパス
        self.path_field = TextField(label="フォルダ保存パス", width=500, value="")

        # 連絡先
        self.phone_inputs_column = Column(controls=[], spacing=5)
        self.email_inputs_column = Column(controls=[], spacing=5)
        self._add_initial_contacts(self.phone_inputs_column, is_email=False)
        self._add_initial_contacts(self.email_inputs_column, is_email=True)

        # SOL連携等
        self.sol_case_number = TextField(label="SOL案件No", hint_text="例: S12345", width=200)
        self.introduction_date = TextField(
            label="紹介日", 
            hint_text="YYYY-MM-DD", 
            width=200,
            on_blur=on_date_blur_handler
        )
        self.sec_branch_name = TextField(label="証券会社支店名", hint_text="例: 東京支店", width=250)
        self.sec_rep_name = TextField(label="証券会社担当者名", hint_text="例: 山田 太郎", width=250)
        self.consent_date = TextField(
            label="同意書日付", 
            hint_text="YYYY-MM-DD", 
            width=200,
            on_blur=on_date_blur_handler
        )

        # AIステータス用
        self.upload_indicator = ProgressRing(visible=False, width=20, height=20, color="secondary")
        self.upload_status_text = Text("", size=14, color="secondary")

    def _create_ai_section(self) -> Container:
        """AI自動入力エリアの作成"""
        return Container(
            content=Column(
                [
                    Row([
                        Icon(Icons.AUTO_AWESOME, color="outline"),
                        Text("AI自動入力 (無効)", size=16, weight=FontWeight.BOLD, color="outline"),
                    ]),
                    Text("現在、AI機能は利用できません。", size=14, color="outline"),
                    Row([
                        ElevatedButton(
                            "PDFファイルを選択",
                            icon=Icons.UPLOAD_FILE,
                            on_click=lambda _: self.page.open(SnackBar(Text("AI機能は現在無効化されています。"), bgcolor=Colors.GREY)),
                            style=ButtonStyle(
                                bgcolor="surfaceVariant",
                                color="onSurfaceVariant",
                            ),
                            disabled=True # 無効化
                        ),
                        self.upload_indicator,
                        self.upload_status_text,
                    ], vertical_alignment="center", spacing=10),
                ],
                spacing=5,
            ),
            padding=15,
            border=border.all(1, "outlineVariant"),
            border_radius=8,
            bgcolor="surfaceVariant",
        )

    def _create_phone_section(self) -> Row:
        return Row(
            [
                Text("電話番号", size=14, weight=FontWeight.W_500),
                ElevatedButton(
                    "追加",
                    icon=Icons.ADD,
                    on_click=lambda e: add_new_contact_row(e, self.phone_inputs_column, is_email=False),
                    bgcolor="secondaryContainer",
                    color="onSecondaryContainer",
                ),
            ],
            alignment=MainAxisAlignment.SPACE_BETWEEN,
        )

    def _create_email_section(self) -> Row:
        return Row(
            [
                Text("メールアドレス", size=14, weight=FontWeight.W_500),
                ElevatedButton(
                    "追加",
                    icon=Icons.ADD,
                    on_click=lambda e: add_new_contact_row(e, self.email_inputs_column, is_email=True),
                    bgcolor="secondaryContainer",
                    color="onSecondaryContainer",
                ),
            ],
            alignment=MainAxisAlignment.SPACE_BETWEEN,
        )

    def _add_initial_contacts(self, column: Column, is_email: bool) -> None:
        new_row, _ = create_contact_input_row(column, initial_value="", is_email=is_email)
        column.controls.append(new_row)

    # --- 住所自動分割ロジック ---
    def parse_and_fill_address(self, e):
        """住所貼り付けフィールドの変更時に自動分割してセットする"""
        full_address = self.paste_address_field.value
        if not full_address:
            self.candidate_container.visible = False
            self.page.update()
            return
        
        full_address = full_address.replace("　", " ").strip()

        # 1. 都道府県の抽出
        match_pref = re.match(r'(.*?([都道府県]))(.+)', full_address)
        if match_pref:
            # 都道府県がある場合：通常処理
            self.candidate_container.visible = False
            pref = match_pref.group(1)
            rest = match_pref.group(3).strip()
            self._fill_address_fields(pref, rest)
        else:
            # 都道府県がない場合：AI推測
            self._predict_prefecture_with_ai(full_address)

    def _fill_address_fields(self, pref: str, rest: str):
        """分割された住所情報をフィールドにセットする内部メソッド"""
        self.pref_field.value = pref
        
        # 2. 市区町村の抽出
        match_city = re.match(r'^(.+?[郡市区町村])(.+)', rest)
        if match_city:
            city = match_city.group(1)
            rest_street = match_city.group(2).strip()
            self.city_field.value = city
            
            # 3. 番地と建物の分離
            parts = rest_street.split(" ", 1)
            street = parts[0]
            building = parts[1] if len(parts) > 1 else ""
            self.street_field.value = street
            self.building_field.value = building
        else:
            self.city_field.value = ""
            self.street_field.value = rest
            self.building_field.value = ""
        
        # 4. 郵便番号の自動検索（非同期）
        self.page.run_thread(lambda: self._search_zip_async(pref, self.city_field.value, self.street_field.value))
        self.page.update()

    def _predict_prefecture_with_ai(self, address_fragment: str):
        """AIを使って都道府県を推測し、候補を表示または自動反映する"""
        self.page.open(SnackBar(Text("都道府県を検索中..."), bgcolor=Colors.BLUE_GREY_400))
        self.page.update()

        def task():
            try:
                candidates = ai_service.predict_prefectures_sync(address_fragment)
                
                if not candidates:
                    self.page.open(SnackBar(Text("都道府県を特定できませんでした。手動で入力してください。"), bgcolor=Colors.ORANGE))
                    self.candidate_container.visible = False
                elif len(candidates) == 1:
                    pref = candidates[0]
                    self.page.open(SnackBar(Text(f"「{pref}」を補完しました。"), bgcolor=Colors.GREEN))
                    self._fill_address_fields(pref, address_fragment)
                else:
                    self._show_candidates(candidates, address_fragment)
            except Exception as e:
                print(f"AI Predict Error: {e}")
                self.candidate_container.visible = False
            self.page.update()

        self.page.run_thread(task)

    def _show_candidates(self, candidates: List[str], rest_address: str):
        """候補チップを表示する"""
        self.candidate_chips_row.controls.clear()
        for cand in candidates:
            self.candidate_chips_row.controls.append(
                Chip(
                    label=Text(cand),
                    on_select=lambda e, p=cand: self._on_candidate_select(p, rest_address),
                    bgcolor=Colors.WHITE
                )
            )
        self.candidate_container.visible = True
        self.page.update()

    def _on_candidate_select(self, pref: str, rest: str):
        self.candidate_container.visible = False
        self._fill_address_fields(pref, rest)

    def _search_zip_async(self, pref: str, city: str, street: str):
        """
        非同期で郵便番号検索を行う。
        番地（数字）が含まれていると検索精度が落ちるため、町域のみでの検索を優先する。
        """
        try:
            from src.services.deceased_service import search_zip_by_address_api
            
            zip_code = None
            
            # 1. 町域レベルでの検索 (数字・ハイフンを除去)
            # 例: "緑町12-9" -> "緑町"
            if street:
                # 💡 修正: 全角数字(０-９)も区切り文字として認識させる
                match = re.match(r'^([^0-9\-\uFF10-\uFF19]+)', street)
                if match:
                    town_part = match.group(1).strip()
                    target = f"{pref}{city}{town_part}"
                    zip_code = search_zip_by_address_api(target)

            # 2. ヒットしなければフル住所 (番地なしの場合の保険)
            if not zip_code:
                full = f"{pref}{city}{street}"
                zip_code = search_zip_by_address_api(full)
            
            # 💡 修正: 「市レベルでのフォールバック」は削除しました。
            # "長崎市"だけで検索すると、代表番号やリスト先頭の番号(矢上町など)が返り、
            # 正しくない番号がセットされるリスクが高いためです。
            
            if zip_code:
                self.zip_field.value = zip_code
                self.page.update()
        except Exception as ex:
            print(f"Auto zip search failed: {ex}")

    # --- 住所自動入力ロジック ---
    def search_address_by_zip(self, e) -> None:
        zip_code = self.zip_field.value
        if not zip_code:
            return
            
        try:
            address_info = search_address_by_zip_api(zip_code)
            if address_info is None:
                self.pref_field.value = "通信エラー"
            elif address_info == {}:
                self.page.open(SnackBar(Text("住所が見つかりませんでした"), bgcolor=Colors.RED))
            else:
                self.pref_field.value = address_info.get("prefecture", "")
                self.city_field.value = address_info.get("city_ward_town", "")
                self.street_field.value = address_info.get("street_address", "")
                self.street_field.focus()
        except Exception as ex:
             self.page.open(SnackBar(Text(f"住所検索エラー: {ex}"), bgcolor=Colors.RED))
        self.page.update()

    def search_zip_by_address(self, e) -> None:
        """住所入力から郵便番号を検索"""
        pref = self.pref_field.value or ""
        city = self.city_field.value or ""
        street = self.street_field.value or ""
        
        if not pref or not city:
            return
        if self.zip_field.value:
            return

        self.page.run_thread(lambda: self._search_zip_async(pref, city, street))

    # --- フォルダ選択ロジック ---
    def get_directory_result(self, e: FilePickerResultEvent) -> None:
        self.path_field.value = e.path if e.path else ""
        self.page.update()

    def open_folder_dialog(self, e) -> None:
        self.folder_picker.get_directory_path(dialog_title="案件フォルダの保存先を選択")

    # --- AI処理ロジック (無効化) ---
    async def on_file_picked(self, e: FilePickerResultEvent) -> None:
        """AI機能は無効化されています"""
        self.page.open(SnackBar(Text("AI機能は現在利用できません。"), bgcolor=Colors.GREY))
        return

    async def _process_pdf_with_ai(self, file_path: str) -> None:
        """AI処理 (ダミー)"""
        pass

    def _parse_ai_response(self, text_response: str) -> Dict[str, Any]:
        return {}

    def _fill_form_with_data(self, data: Dict[str, Any]) -> None:
        pass

    def _reset_upload_ui(self) -> None:
        pass

    # --- 保存処理 ---
    def save_and_go_to_detail(self, e) -> None:
        case_num_input = self.case_number_field.value.strip()
        name_last_input = self.name_last_field.value.strip()
        new_path = self.path_field.value.strip()

        # 1. 必須項目チェック
        if not case_num_input or not name_last_input:
            self.page.open(SnackBar(Text("必須項目（案件番号、契約者氏名(姓)）を入力してください。"), bgcolor=Colors.RED))
            self.page.update()
            return

        # 2. 案件番号の重複チェック
        try:
            if is_case_number_duplicate(case_num_input):
                self.page.open(SnackBar(Text(f"案件番号 '{case_num_input}' は既に存在します。"), bgcolor=Colors.RED))
                self.page.update()
                return
        except Exception as ex:
             self.page.open(SnackBar(Text(f"DBエラー: {ex}"), bgcolor=Colors.RED))
             self.page.update()
             return

        # 3. 連絡先情報の収集
        collected_data = {
            "phone_contacts": collect_contacts(self.phone_inputs_column),
            "email_contacts": collect_contacts(self.email_inputs_column),
        }

        # 担当者ID取得ヘルパー
        def _get_id(val: Optional[str]) -> Optional[int]:
            if val and val not in ["", "未割当"]:
                return int(val)
            return None

        # 4. データベース登録
        try:
            new_deceased_id = add_new_case_for_client_registration(
                case_number=case_num_input,
                name=f"{name_last_input} {self.name_first_field.value.strip()}",
                kana_last=self.kana_last_field.value.strip(),
                kana_first=self.kana_first_field.value.strip(),
                rel=self.rel_field.value.strip(),
                hometown=self.hometown_field.value.strip(),
                zip_code=self.zip_field.value.strip(),
                pref=self.pref_field.value.strip(),
                city=self.city_field.value.strip(),
                street=self.street_field.value.strip(),
                building=self.building_field.value.strip(),
                dob=None,
                dod=None,
                manager_id=_get_id(self.manager_field.value),
                operator_id=_get_id(self.operator_field.value),
                phone_contacts=collected_data["phone_contacts"],
                email_contacts=collected_data["email_contacts"],
            )

            if new_deceased_id > 0:
                case_id = get_case_id_by_deceased_id(new_deceased_id)

                if case_id and new_path:
                    update_case_folder_path(case_id=case_id, folder_path=new_path)

                self._update_case_additional_info(case_id)

                self.page.open(SnackBar(Text("新規案件を登録しました。"), bgcolor=Colors.GREEN))
                self.page.go(f"/detail/{case_id}")
            else:
                raise Exception("データベース登録処理でIDが返されませんでした。")

        except Exception as ex:
            print(f"保存エラー: {ex}")
            self.page.open(SnackBar(Text(f"保存エラー: {str(ex)}"), bgcolor=Colors.RED))
            self.page.update()

    def _update_case_additional_info(self, case_id: int) -> None:
        if not case_id: return

        db = SessionLocal()
        try:
            case = db.query(Case).get(case_id)
            if case:
                case.sol_case_number = self.sol_case_number.value
                case.referral_sec_branch_name = self.sec_branch_name.value
                case.referral_sec_rep_name = self.sec_rep_name.value
                
                def parse_date(d_str: str) -> Optional[datetime.date]:
                    if not d_str: return None
                    try:
                        return datetime.strptime(d_str, "%Y-%m-%d").date()
                    except ValueError:
                        try:
                            from src.utils.date_utils import parse_all_flexible_date
                            return parse_all_flexible_date(d_str)
                        except:
                            return None

                case.introduction_date = parse_date(self.introduction_date.value)
                case.consent_date = parse_date(self.consent_date.value)
                
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"Additional Info Update Error: {e}")
        finally:
            db.close()

# --- 互換性のためのダミー関数 ---
def reset_all_global_fields():
    pass