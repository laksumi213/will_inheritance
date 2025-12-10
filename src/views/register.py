# src/views/register.py
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List

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
    is_case_number_duplicate,
)

# AIサービス
try:
    from services.ai_service import ai_service
except ImportError:
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
                        Text("案件情報", weight=FontWeight.BOLD, size=18),
                        Row([self.case_number_field, self.manager_field, self.operator_field]),
                        Divider(),

                        # 3. 契約者情報
                        Text("👤 契約者（依頼者）情報 *", weight=FontWeight.BOLD, size=18),
                        Row([self.name_last_field, self.name_first_field]),
                        Row([self.kana_last_field, self.kana_first_field]),
                        Row([self.rel_field]),
                        Row([self.hometown_field]),
                        Divider(),

                        # 4. 連絡先情報
                        Text("📞 連絡先情報", weight=FontWeight.BOLD, size=18),
                        self._create_phone_section(),
                        self.phone_inputs_column,
                        self._create_email_section(),
                        self.email_inputs_column,
                        Divider(),

                        # 5. 現住所
                        Text("🏠 現住所", weight=FontWeight.BOLD, size=18),
                        Row([self.zip_field, self.pref_field, self.city_field]),
                        Row([self.street_field, self.building_field]),
                        Divider(height=30),

                        # 6. フォルダパス
                        Text("📁 案件フォルダ設定", weight=FontWeight.BOLD, size=18),
                        Row([
                            self.path_field,
                            ElevatedButton(
                                "フォルダ選択",
                                icon=Icons.FOLDER_OPEN,
                                on_click=self.open_folder_dialog,
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
                                    on_click=lambda e: self.page.go("/")
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
        self.manager_field = Dropdown(label="担当者1", width=200, options=self.user_options)
        self.operator_field = Dropdown(label="担当者2", width=200, options=self.user_options)

        # 契約者情報
        self.name_last_field = TextField(label="契約者氏名 (姓) *", width=150)
        self.name_first_field = TextField(label="契約者氏名 (名)", width=150)
        self.kana_last_field = TextField(label="ふりがな (姓)", width=150)
        self.kana_first_field = TextField(label="ふりがな (名)", width=150)
        self.rel_field = TextField(label="被相続人との続柄", width=200)
        self.hometown_field = TextField(label="本籍地 (契約者)")

        # 住所情報
        self.zip_field = TextField(label="郵便番号", width=150, on_blur=self.search_address_by_zip)
        self.pref_field = TextField(label="都道府県", width=150)
        self.city_field = TextField(label="市区町村", width=200)
        self.street_field = TextField(label="番地", width=150)
        self.building_field = TextField(label="建物名・部屋番号")

        # フォルダパス
        self.path_field = TextField(label="フォルダ保存パス", width=500, value="")

        # 連絡先
        self.phone_inputs_column = Column(controls=[], spacing=5)
        self.email_inputs_column = Column(controls=[], spacing=5)
        self._add_initial_contacts(self.phone_inputs_column, is_email=False)
        self._add_initial_contacts(self.email_inputs_column, is_email=True)

        # SOL連携等
        # 💡 on_blur ハンドラを追加
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
        self.upload_indicator = ProgressRing(visible=False, width=20, height=20)
        self.upload_status_text = Text("", size=14, color="secondary")

    def _create_ai_section(self) -> Container:
        """AI自動入力エリアの作成"""
        return Container(
            content=Column(
                [
                    Row([
                        Icon(Icons.AUTO_AWESOME, color="primary"),
                        Text("AI自動入力 (任意)", size=16, weight=FontWeight.BOLD, color="onSecondaryContainer"),
                    ]),
                    Text("顧客紹介連絡票(PDF)を選択すると、下部のフォームに情報を自動入力します。", size=14, color="onSecondaryContainer"),
                    Row([
                        ElevatedButton(
                            "PDFファイルを選択",
                            icon=Icons.UPLOAD_FILE,
                            on_click=lambda _: self.file_picker.pick_files(
                                allow_multiple=False, allowed_extensions=["pdf"]
                            ),
                            style=ButtonStyle(
                                bgcolor="surface",
                                color="primary",
                            )
                        ),
                        self.upload_indicator,
                        self.upload_status_text,
                    ], vertical_alignment="center", spacing=10),
                ],
                spacing=5,
            ),
            padding=15,
            border=border.all(1, "secondaryContainer"),
            border_radius=8,
            bgcolor="secondaryContainer",
        )

    def _create_phone_section(self) -> Row:
        return Row(
            [
                Text("電話番号", size=14, weight=FontWeight.W_500),
                ElevatedButton(
                    "追加",
                    icon=Icons.ADD,
                    on_click=lambda e: add_new_contact_row(e, self.phone_inputs_column, is_email=False),
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
                ),
            ],
            alignment=MainAxisAlignment.SPACE_BETWEEN,
        )

    def _add_initial_contacts(self, column: Column, is_email: bool) -> None:
        new_row, _ = create_contact_input_row(column, initial_value="", is_email=is_email)
        column.controls.append(new_row)

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
                self.page.open(SnackBar(Text("住所が見つかりませんでした"), bgcolor="error"))
            else:
                self.pref_field.value = address_info.get("prefecture", "")
                self.city_field.value = address_info.get("city_ward_town", "")
                self.street_field.value = address_info.get("street_address", "")
                self.street_field.focus()

        except Exception as ex:
             self.page.open(SnackBar(Text(f"住所検索エラー: {ex}"), bgcolor="error"))
        
        self.page.update()

    # --- フォルダ選択ロジック ---
    def get_directory_result(self, e: FilePickerResultEvent) -> None:
        self.path_field.value = e.path if e.path else ""
        self.page.update()

    def open_folder_dialog(self, e) -> None:
        self.folder_picker.get_directory_path(dialog_title="案件フォルダの保存先を選択")

    # --- AI処理ロジック (非同期対応) ---
    async def on_file_picked(self, e: FilePickerResultEvent) -> None:
        """
        ファイル選択時のハンドラ
        非同期 (async) にしてUIフリーズを回避
        """
        if e.files:
            file_obj = e.files[0]
            self.upload_status_text.value = f"解析中: {file_obj.name}"
            self.upload_indicator.visible = True
            self.page.update()
            
            # 非同期で処理を実行
            await self._process_pdf_with_ai(file_obj.path)
        else:
            self.upload_status_text.value = ""
            self.page.update()

    async def _process_pdf_with_ai(self, file_path: str) -> None:
        try:
            # 1. ファイル読み込み
            with open(file_path, "rb") as f:
                pdf_bytes = f.read()

            # 2. プロンプト定義
            prompt_text = """
            あなたは相続業務の専門アシスタントです。
            添付された顧客紹介連絡票(PDF)から、以下の情報を抽出し、JSON形式で出力してください。
            値が存在しない場合は空文字にしてください。

            出力キー:
            - client_phone_home (顧客電話番号: 自宅)
            - client_phone_mobile (顧客電話番号: 携帯電話)
            - client_email (顧客メールアドレス)
            - introduction_date (紹介日: YYYY-MM-DD)
            - sec_branch (証券会社の支店名)
            - sec_rep (証券会社の担当者名)
            - sol_case_no (SOL案件No)
            - consent_date (同意書日付: YYYY-MM-DD)
            """

            # 3. 共通AIサービスを呼び出し (JSONモード有効)
            json_str = await ai_service.generate_from_pdf(
                prompt=prompt_text,
                pdf_bytes=pdf_bytes,
                json_mode=True
            )

            # 4. データ抽出とフォームへの反映
            extracted_data = self._parse_ai_response(json_str)
            
            if extracted_data:
                self._fill_form_with_data(extracted_data)
                self.page.open(SnackBar(Text("AI解析完了: データを自動入力しました"), bgcolor="green"))
            else:
                self.page.open(SnackBar(Text("データ抽出に失敗しました (空の応答)"), bgcolor="orange"))

        except Exception as ex:
            print(f"AI Process Error: {ex}")
            self.page.open(SnackBar(Text(f"解析エラー: {ex}"), bgcolor=Colors.RED))
        finally:
            self._reset_upload_ui()
            self.page.update()

    def _parse_ai_response(self, text_response: str) -> Dict[str, Any]:
        """AIの応答テキストをJSONオブジェクトに変換"""
        try:
            clean_text = text_response
            if "```json" in clean_text:
                clean_text = clean_text.replace("```json", "").replace("```", "")
            return json.loads(clean_text)
        except json.JSONDecodeError:
            print("JSON Parse Error")
            return {}

    def _fill_form_with_data(self, data: Dict[str, Any]) -> None:
        """抽出データを各フィールドに入力"""
        self.zip_field.value = data.get("client_zip") or ""
        self.city_field.value = data.get("client_address", "") or ""
        
        # 新規フィールド
        self.sol_case_number.value = data.get("sol_case_no") or ""
        self.introduction_date.value = data.get("introduction_date") or ""
        self.sec_branch_name.value = data.get("sec_branch") or ""
        self.sec_rep_name.value = data.get("sec_rep") or ""
        self.consent_date.value = data.get("consent_date") or ""

        # 電話番号
        phone_val = data.get("client_phone_home") or data.get("client_phone_mobile")
        if phone_val and self.phone_inputs_column.controls:
            row = self.phone_inputs_column.controls[0]
            if row.controls and isinstance(row.controls[0], TextField):
                row.controls[0].value = phone_val

        # メールアドレス
        email_val = data.get("client_email")
        if email_val and self.email_inputs_column.controls:
            row = self.email_inputs_column.controls[0]
            if row.controls and isinstance(row.controls[0], TextField):
                row.controls[0].value = email_val

    def _reset_upload_ui(self) -> None:
        self.upload_status_text.value = "解析完了"
        self.upload_indicator.visible = False

    # --- 保存処理 ---
    def save_and_go_to_detail(self, e) -> None:
        case_num_input = self.case_number_field.value.strip()
        name_last_input = self.name_last_field.value.strip()
        new_path = self.path_field.value.strip()

        # 1. 必須項目チェック
        if not case_num_input or not name_last_input:
            self.page.open(SnackBar(Text("必須項目（案件番号、契約者氏名(姓)）を入力してください。"), bgcolor="error"))
            self.page.update()
            return

        # 2. 案件番号の重複チェック
        try:
            if is_case_number_duplicate(case_num_input):
                self.page.open(SnackBar(Text(f"案件番号 '{case_num_input}' は既に存在します。"), bgcolor="error"))
                self.page.update()
                return
        except Exception as ex:
             self.page.open(SnackBar(Text(f"DBエラー: {ex}"), bgcolor="error"))
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

                self.page.open(SnackBar(Text("新規案件を登録しました。"), bgcolor="green"))
                self.page.go(f"/detail/{case_id}")
            else:
                raise Exception("データベース登録処理でIDが返されませんでした。")

        except Exception as ex:
            print(f"保存エラー: {ex}")
            self.page.open(SnackBar(Text(f"保存エラー: {str(ex)}"), bgcolor="error"))
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
                            # 万が一手入力で不正な形式が残っていた場合のフェイルセーフ
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