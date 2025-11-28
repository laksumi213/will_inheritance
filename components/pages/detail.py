# /components/pages/detail.py

import threading
import time
import os
from datetime import datetime

# 💡 追加: 自動化用ライブラリ
import pyautogui
import pyperclip
# import keyboard

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv
import tkinter as tk
from tkinter import messagebox

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
    FilePicker,
    FilePickerResultEvent,
    FontWeight,
    IconButton,
    Icons,
    MainAxisAlignment,
    Page,
    Row,
    ScrollMode,
    SnackBar,
    Text,
    TextButton,
    TextField,
    View,
    border,
    dropdown,
    ButtonStyle,
)

from components.utils.date_utils import convert_seireki_to_wareki
from components.utils.ui_utils import show_confirm_dialog
from services import deceased_service
from services.db_setup import get_all_users
from services.deceased_service import (
    get_address_by_id,
    parse_all_flexible_date,
    update_case_assignment,
    update_case_folder_path,
)

# --- グローバルな UI 定義 ---

USER_MAP = get_all_users()
USER_OPTIONS = [dropdown.Option(str(id), name) for id, name in USER_MAP.items()]
USER_OPTIONS.insert(0, dropdown.Option("", "未割当"))

dialog_manager_field = Dropdown(
    label="担当者1 (進捗管理)",
    width=200,
    options=USER_OPTIONS,
    value="",
    autofocus=True,
)
dialog_operator_field = Dropdown(
    label="担当者2 (実務担当)", width=200, options=USER_OPTIONS, value=""
)


def on_date_blur_handler(e, wareki_text: Text):
    input_value = e.control.value
    wareki_text.value = ""

    if not input_value:
        e.control.error_text = None
        wareki_text.update()
        e.control.update()
        return

    try:
        validated_date = parse_all_flexible_date(input_value)
        e.control.value = validated_date.isoformat()
        e.control.error_text = None
        wareki_text.value = convert_seireki_to_wareki(validated_date)

    except ValueError:
        e.control.error_text = "無効な日付形式です"
        wareki_text.value = ""

    wareki_text.update()
    e.control.update()


# --- モーダル編集で使用するフィールド定義 ---
dialog_name_last_field = TextField(label="氏名 (姓)", width=150, autofocus=True)
dialog_name_first_field = TextField(label="氏名 (名)", width=150)
dialog_kana_last_field = TextField(label="ふりがな (姓)", width=150)
dialog_kana_first_field = TextField(label="ふりがな (名)", width=150)
dialog_rel_field = TextField(label="続柄", width=200)

dialog_hometown_field = TextField(label="本籍地")
dialog_zip_field = TextField(label="郵便番号", width=150)
dialog_pref_field = TextField(label="都道府県", width=150)
dialog_city_field = TextField(label="市区町村", width=200)
dialog_street_field = TextField(label="番地", width=150)
dialog_building_field = TextField(label="建物名・部屋番号")

phone_inputs_column = Column(controls=[], spacing=5)
email_inputs_column = Column(controls=[], spacing=5)

dialog_dob_field = TextField(label="生年月日 (YYYY-MM-DD)", width=180)
wareki_dob_text = Text(value="", width=250, color=Colors.BLUE_GREY_600, weight=FontWeight.W_500)
dialog_dob_field.on_blur = lambda e: on_date_blur_handler(e, wareki_dob_text)

dialog_dod_field = TextField(label="死亡日 (YYYY-MM-DD)", width=180)
wareki_dod_text = Text(value="", width=250, color=Colors.BLUE_GREY_600, weight=FontWeight.W_500)
dialog_dod_field.on_blur = lambda e: on_date_blur_handler(e, wareki_dod_text)

dialog_title_control = Text("情報編集", weight=FontWeight.BOLD)
dialog_case_number_field = TextField(label="案件番号", width=250)


# ---------------------------------------------
# 💡 Kintone 自動化ロジック (PyAutoGUI版)
# ---------------------------------------------
def launch_kintone_automation(case_id: int):
    """
    Seleniumでブラウザを開き、Kintoneにログイン後、
    PyAutoGUIを使ってキーボード操作で入力を行う
    """
    
    # DBからデータ取得
    kintone_data = deceased_service.get_kintone_integration_data(case_id)
    if not kintone_data:
        print("エラー: データが見つかりませんでした")
        return

    load_dotenv()
    KINTONE_USER = os.getenv("KINTONE_USER")
    KINTONE_PASS = os.getenv("KINTONE_PASS")

    # PyAutoGUIの設定
    pyautogui.PAUSE = 0.5  # 操作ごとの待機時間

    def show_manual_instruction(message):
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showinfo("操作のお願い", message)
        root.destroy()

    def _run_browser():
        keys_to_block = ['enter', 'tab', 'space', 'up', 'down', 'left', 'right']
        
        try:
            options = webdriver.ChromeOptions()
            options.add_experimental_option("detach", True)
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            driver.maximize_window()
            target_url = "https://chester-tax.cybozu.com/k/242/edit"
            driver.get(target_url)
            
            wait = WebDriverWait(driver, 600)
            action_wait = WebDriverWait(driver, 5)

            # --- A. ログイン処理 ---
            try:
                if "login" in driver.current_url:
                    print("ログイン画面検知。")
                    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, "username")))
                    if KINTONE_USER:
                        driver.find_element(By.NAME, "username").send_keys(KINTONE_USER)
                    if KINTONE_PASS:
                        driver.find_element(By.NAME, "password").send_keys(KINTONE_PASS)
                    driver.find_element(By.NAME, "password").send_keys(Keys.ENTER)
            except Exception:
                pass 

            # --- B. 編集画面ロード待ち ---
            print("編集画面のロードを待機中...")
            try:
                # 「保存」ボタンが見えるまで待機
                wait.until(EC.visibility_of_element_located((By.XPATH, "//button[contains(text(), '保存')]")))
                print("編集画面ロード完了")
                time.sleep(1.0)
            except TimeoutException:
                print("タイムアウト: 編集画面に到達できませんでした。")
                return

            driver.execute_script("document.body.style.zoom='80%'")
            time.sleep(0.5)

            # ヘルパー関数: ラベルから要素を探す (Selenium)
            def find_target_element(label):
                label_xpath = f"//span[contains(@class, 'control-label-text-gaia') and normalize-space(text())='{label}']"
                container_xpath = f"({label_xpath})[1]/ancestor::div[contains(@class, 'control-gaia')][1]"
                target_xpath = f"{container_xpath}//input[not(@type='hidden')]"
                return action_wait.until(EC.presence_of_element_located((By.XPATH, target_xpath)))
            
            # ヘルパー関数: PyAutoGUIでの下キー選択
            def select_with_arrow(down_count):
                if down_count > 0:
                    time.sleep(0.3)
                    pyautogui.press('down', presses=down_count)
                pyautogui.press('enter')

            # --- C. 自動入力フロー開始 ---
            print("--- 自動入力を開始します。キーボード操作は無効化されます ---")

            # ユーザーの誤操作を防ぐためにキー入力をブロック
            # for k in keys_to_block:
            #     keyboard.block_key(k)

            # 1. 【顧客コード】フィールドをSeleniumで特定してクリック（フォーカスセット）
            # これにより、以降のPyAutoGUIの入力がブラウザに対して行われるようにする
            code_elem = find_target_element("顧客コード")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", code_elem)
            code_elem.click()
            time.sleep(0.5)

            # -----------------------------------------------------
            # 🔥 ここから純粋なキーボード操作フロー 🔥
            # -----------------------------------------------------

            # 1. 顧客コード入力
            pyautogui.write(kintone_data["case_number"])
            time.sleep(0.5)

            # 2. 【拠点フィールド】 (Tab x1 -> 下 x2 -> Enter)
            pyautogui.press('tab')
            select_with_arrow(2)

            # 3. 【チームフィールド】 (Tab x1 -> 下 x3 -> Enter)
            pyautogui.press('tab')
            select_with_arrow(3)

            # 4. 【担当者①など】 (既存のSeleniumロジックを活用して確実に入力)
            # ※ Tabだけで移動し続けるとズレる可能性があるため、確実に要素を指定できるSeleniumも併用
            
            # 一旦キーブロック解除 (Selenium操作中は不要かもだが念のため)
            # for k in keys_to_block: keyboard.unblock_key(k)

            def input_selenium_text(label, value):
                if not value: return
                try:
                    elem = find_target_element(label)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                    elem.click()
                    elem.send_keys(Keys.CONTROL, "a") # 全選択
                    elem.send_keys(Keys.DELETE)      # 削除
                    elem.send_keys(value)
                    time.sleep(0.2)
                    elem.send_keys(Keys.TAB)
                except Exception:
                    pass

            # 担当者入力 (Seleniumで指定)
            input_selenium_text("担当者①", "森町")
            input_selenium_text("担当者②", "森町")
            input_selenium_text("面談対応者（MC）", "森町")

            # 5. 【行チェ通知先】 (森町ペースト -> 下 x1 -> Enter)
            # まず通知先フィールドにフォーカスを当てる (Selenium)
            notify_elem = find_target_element("行チェ通知先") # ユーザー選択フィールドのInputを探す
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", notify_elem)
            notify_elem.click()
            time.sleep(0.5)

            # クリップボード操作 (PyAutoGUI)
            pyperclip.copy("森町")
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(.5) # 検索候補が出るのを待つ
            select_with_arrow(1) # 下1回 -> Enter

            # 6. その他の情報入力 (Seleniumで安全に)
            input_selenium_text("郵便番号", kintone_data["client_zip"])
            input_selenium_text("顧客名", kintone_data["client_name"])
            input_selenium_text("被相続人名", kintone_data["deceased_name"])
            
            time.sleep(1.0) # 自動補完待ち

            input_selenium_text("住所", kintone_data["client_addr"])
            input_selenium_text("顧客名(ふりがな)", kintone_data["client_kana"])
            input_selenium_text("被相続人名（ふりがな）", kintone_data["deceased_kana"])
            input_selenium_text("TEL", kintone_data["client_tel"])
            input_selenium_text("メールアドレス", kintone_data["client_mail"])
            input_selenium_text("相続開始日", kintone_data["inheritance_date"])

            print("✅ 入力完了")

            # 手動操作のためにブロック解除
            # for k in keys_to_block:
            #     keyboard.unblock_key(k)

            # --- 手動タブ切り替え指示 ---
            show_manual_instruction("【案件情報】タブをクリックして開いてください。\n\n切り替えが終わったら、このウィンドウの「OK」を押してください。")
            time.sleep(1.0)

            # 案件情報タブの内容
            today_str = datetime.now().strftime("%Y-%m-%d")
            input_selenium_text("紹介日", today_str)

        except Exception as e:
            print(f"❌ 自動化エラー: {e}")
        # finally:
        #     # エラー終了時も必ずロック解除
        #     try:
        #         for k in keys_to_block:
        #             keyboard.unblock_key(k)
        #     except:
        #         pass

    threading.Thread(target=_run_browser, daemon=True).start()


def copy_to_clipboard_and_notify(e, page: Page, content: str):
    """クリックされたテキストをクリップボードにコピーし、SnackBarで通知する"""
    text_to_copy = content.strip()
    if not text_to_copy or text_to_copy == "N/A":
        return

    page.set_clipboard(text_to_copy)

    page.open(
        SnackBar(
            content=Text(
                f"'{text_to_copy[:30].strip()}' をクリップボードにコピーしました。📋",
                color=Colors.WHITE,
            ),
            bgcolor=Colors.BLUE_GREY_700,
            duration=1500,
        )
    )
    page.update()


def DeceasedDetailView(page: Page, case_id: int):
    # --- FilePickerの初期化とオーバーレイへの追加 ---
    file_picker = FilePicker(on_result=lambda e: page.update())
    if file_picker not in page.overlay:
        page.overlay.append(file_picker)

    # --- サービス層からデータを取得 ---
    case = deceased_service.get_case_by_id(case_id)
    # deceased = deceased_service.get_deceased_by_id(case_id)
    deceased = deceased_service.get_deceased_by_case_id(case_id)

    is_new_client_case = case_id == -1
    is_new_deceased = case_id == 0
    deceased_id = deceased.id if deceased else case_id

    # 最後の住所情報を取得
    last_address = None
    if deceased and deceased.last_address_id:
        last_address = get_address_by_id(deceased.last_address_id)

    display_deceased_address = "未登録"
    copyable_full_address = "未登録"

    if last_address:
        address_parts = [
            last_address.prefecture,
            last_address.city_ward_town,
            last_address.street_address,
        ]
        raw_deceased_address = "".join(filter(None, address_parts))
        building = last_address.building_name if last_address.building_name else ""
        zip_code = last_address.zip_code if last_address.zip_code else ""

        if raw_deceased_address:
            display_deceased_address = raw_deceased_address
            if building:
                display_deceased_address += f" ({building})"
        elif building:
            display_deceased_address = f"建物名: {building}"
        else:
            display_deceased_address = "未登録"

        copyable_full_address = (
            f"〒{zip_code} {raw_deceased_address} {building}" if raw_deceased_address else "未登録"
        ).strip()

    # 案件情報を取得
    case = deceased.case if deceased and deceased.case else None

    if deceased and not is_new_client_case:
        full_name = f"{deceased.name_last} {deceased.name_first}"
        dob_date_obj = deceased.date_of_birth
        if dob_date_obj:
            seireki_dob = dob_date_obj.strftime("%Y/%m/%d")
            wareki_dob = convert_seireki_to_wareki(dob_date_obj)
            dob_display_str = f"{seireki_dob} ({wareki_dob})"
        else:
            dob_display_str = "未登録"

        dod_date_obj = deceased.date_of_death
        if dod_date_obj:
            seireki_dod = dod_date_obj.strftime("%Y/%m/%d")
            wareki_dod = convert_seireki_to_wareki(dod_date_obj)
            dod_display_str = f"{seireki_dod} ({wareki_dod})"
        else:
            dod_display_str = "未登録"

    elif is_new_client_case or is_new_deceased or deceased is None:
        full_name = "【未登録】新規登録が必要です"
        dob_str = "N/A"
        dod_str = "N/A"
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
                "heirs": [],
                "case": None,
                "case_id": None,
                "last_address_id": None, # ダミー追加
            },
        )()
        case = None

    heirs_controls = Column()

    path_field = TextField(
        label="フォルダ保存パス",
        width=1000,
        read_only=False,
        value="",
    )

    def save_path_on_blur(e):
        current_input = path_field.value.strip()

        if current_input == "パス設定をキャンセルしました":
            return

        if case and case.case_id:
            path_to_save = current_input if current_input else None

            if path_to_save != deceased_service.get_case_folder_path(case.case_id):
                success = deceased_service.update_case_folder_path(
                    case_id=case.case_id,
                    folder_path=path_to_save,
                )

                if success:
                    page.open(
                        SnackBar(
                            content=Text("フォルダパスを更新しました。", color=Colors.WHITE),
                            bgcolor=Colors.BLUE_700,
                            duration=1500,
                        )
                    )
                else:
                    page.open(
                        SnackBar(
                            content=Text(
                                "エラー: フォルダパスの保存に失敗しました。",
                                color=Colors.WHITE,
                            ),
                            bgcolor=Colors.RED_700,
                            duration=3000,
                        )
                    )
        page.update()

    def get_directory_result_detail(e: FilePickerResultEvent):
        path_field.value = e.path if e.path else "パス設定をキャンセルしました"
        save_path_on_blur(e)
        page.update()

    def open_folder_dialog_detail(e):
        file_picker.on_result = get_directory_result_detail
        file_picker.get_directory_path(dialog_title="案件フォルダの保存先を選択")

    path_field.on_blur = lambda e: save_path_on_blur(e)

    def create_delete_confirm_dialog(case_num: str):
        def confirm_delete_case(e):
            try:
                success = deceased_service.delete_case_and_all_related_data(case_num)
                if success:
                    print(f"案件 {case_num} の削除が完了しました。")
                    page.go("/")
                else:
                    page.open(
                        SnackBar(
                            content=Text(
                                f"案件 {case_num} の削除に失敗しました。",
                                color=Colors.WHITE,
                            ),
                            bgcolor=Colors.RED_700,
                            duration=2000,
                        )
                    )
            except Exception as ex:
                page.open(
                    SnackBar(
                        content=Text(f"削除中にエラーが発生しました: {ex}", color=Colors.WHITE),
                        bgcolor=Colors.RED_700,
                        duration=2000,
                    )
                )
            delete_confirm_dialog.open = False
            page.update()

        def close_delete_dialog(e):
            delete_confirm_dialog.open = False
            page.update()

        delete_confirm_dialog = AlertDialog(
            modal=True,
            title=Text("案件削除の確認", weight=FontWeight.BOLD, color=Colors.RED_700),
            content=Text(
                f"案件番号 {case_num} に紐づく全ての情報（被相続人、相続人、財産、タスク等）を完全に削除します。よろしいですか？",
                size=14,
            ),
            actions=[
                TextButton("キャンセル", on_click=close_delete_dialog),
                ElevatedButton(
                    "完全に削除",
                    on_click=confirm_delete_case,
                    color=Colors.WHITE,
                    bgcolor=Colors.RED_600,
                ),
            ],
            actions_alignment=MainAxisAlignment.END,
        )
        return delete_confirm_dialog

    def create_assignment_dialog():
        return AlertDialog(
            modal=True,
            title=Text("案件担当者 編集", weight=FontWeight.BOLD),
            content=Container(
                content=Column(
                    [
                        Text(
                            f"案件番号: {case.case_number if case else 'N/A'}",
                            weight=FontWeight.W_500,
                        ),
                        Divider(),
                        Row([dialog_manager_field, dialog_operator_field]),
                    ],
                    tight=True,
                    spacing=15,
                ),
                width=450,
                height=200,
            ),
            actions=[
                TextButton("キャンセル", on_click=lambda e: close_dialog()),
                ElevatedButton("保存", on_click=lambda e: save_assignment_dialog(), data="submit"),
            ],
            actions_alignment=MainAxisAlignment.END,
        )

    assignment_edit_dialog = create_assignment_dialog()
    delete_confirm_dialog = create_delete_confirm_dialog(case.case_number if case else "N/A")

    def close_dialog():
        if assignment_edit_dialog.open:
            assignment_edit_dialog.open = False
            page.update()

    def save_assignment_dialog():
        if not case:
            close_dialog()
            return

        def _get_id_from_dropdown(value):
            if value is None or value in ("", "None", "未割当"):
                return None
            try:
                return int(value)
            except ValueError:
                return None

        manager_id = _get_id_from_dropdown(dialog_manager_field.value)
        operator_id = _get_id_from_dropdown(dialog_operator_field.value)
        
        update_case_assignment(
            case_id=case.case_id,
            manager_id=manager_id,
            operator_id=operator_id,
        )
        close_dialog()
        case.manager_id = manager_id
        case.operator_id = operator_id
        page.update()

    def open_assignment_dialog(e):
        if not case:
            page.open(
                SnackBar(
                    content=Text(
                        "⚠️ 案件情報がないため、担当者を編集できません。",
                        color=Colors.WHITE,
                    ),
                    bgcolor=Colors.RED_700,
                    duration=2000,
                )
            )
            page.update()
            return

        dialog_manager_field.value = str(case.manager_id) if case.manager_id else ""
        dialog_operator_field.value = str(case.operator_id) if case.operator_id else ""
        page.open(assignment_edit_dialog)
        page.update()

    def go_to_deceased_edit_page(e):
        id_to_pass = deceased.id if deceased else case_id
        page.go(f"/deceased_edit/{id_to_pass}")

    def go_to_new_heir_page(e):
        id_to_pass = deceased.id if deceased else case_id
        page.go(f"/heir_edit/new?deceased_id={id_to_pass}")

    def go_to_heir_edit_page(e):
        heir_id = e.control.data
        id_to_pass = deceased.id if deceased else case_id
        page.go(f"/heir_edit/{heir_id}?deceased_id={id_to_pass}")

    def update_heirs_list():
        heirs_controls.controls.clear()
        current_deceased = deceased_service.get_deceased_by_id(deceased_id)

        if current_deceased is None or not current_deceased.heirs:
            page.update()
            return

        if case:
            current_path = deceased_service.get_case_folder_path(case.case_id) or ""
            path_field.value = current_path
        else:
            path_field.value = ""

        for heir in current_deceased.heirs:
            heir_full_name = f"{heir.name_last}　{heir.name_first}"
            is_contracting = getattr(heir, "is_contracting_party", False)
            contract_mark = "【契約者】" if is_contracting else ""

            contacts = deceased_service.get_contact_info("heir", heir.id)
            address_info = deceased_service.get_address_info("heir", heir.id)

            primary_phone = "N/A"
            priority_sub_types = ["Primary", "携帯", "自宅"]

            for sub_type in priority_sub_types:
                found_phone = next(
                    (
                        c["value"]
                        for c in contacts
                        if c["type"] == "PHONE" and c["sub_type"] == sub_type
                    ),
                    None,
                )
                if found_phone:
                    primary_phone = found_phone
                    break

            if primary_phone == "N/A":
                found_any_phone = next((c["value"] for c in contacts if c["type"] == "PHONE"), None)
                if found_any_phone:
                    primary_phone = found_any_phone

            display_phone_value = "未登録" if primary_phone == "N/A" else primary_phone

            addr_parts = [
                address_info.get("prefecture", ""),
                address_info.get("city_ward_town", ""),
                address_info.get("street_address", ""),
            ]
            raw_address = "".join(filter(None, addr_parts))
            primary_address = raw_address or "未登録"

            building = address_info.get("building_name", "")
            if building:
                primary_address += f" ({building})"

            display_relationship = heir.relationship_type.strip() if heir.relationship_type else ""
            if not display_relationship:
                display_relationship = "未登録"

            heirs_controls.controls.append(
                Row(
                    [
                        Text(f"ID:{heir.id}", width=50),
                        Container(
                            content=Text(
                                f"名前: {heir_full_name} {contract_mark}",
                                width=200,
                            ),
                            on_click=lambda e, name=heir_full_name: copy_to_clipboard_and_notify(
                                e, page, name.strip()
                            ),
                            data=heir_full_name.strip(),
                            tooltip="クリックして氏名をコピー",
                        ),
                        Text(f"続柄: {display_relationship}", width=100),
                        Container(
                            content=Text(f"電話: {display_phone_value}", width=150, size=12),
                            on_click=lambda e, phone=primary_phone: copy_to_clipboard_and_notify(
                                e, page, phone
                            ),
                            data=primary_phone,
                            tooltip="クリックして電話番号をコピー",
                        ),
                        Container(width=10),
                        Container(
                            content=Text(f"住所: {primary_address}", width=350, size=12),
                            on_click=lambda e, addr=raw_address: copy_to_clipboard_and_notify(
                                e, page, addr
                            ),
                            data=raw_address,
                            tooltip="クリックして住所をコピー",
                        ),
                        IconButton(
                            Icons.EDIT,
                            icon_color=Colors.BLUE_500,
                            data=heir.id,
                            on_click=go_to_heir_edit_page,
                            tooltip="相続人を編集",
                        ),
                        IconButton(
                            Icons.DELETE,
                            icon_color=Colors.RED_500,
                            data=heir.id,
                            on_click=lambda e, name=heir_full_name: open_heir_delete_confirm(
                                e, heir.id, name
                            ),
                        ),
                    ],
                    alignment=MainAxisAlignment.START,
                )
            )
        page.update()

    def open_heir_delete_confirm(e, heir_id_to_delete: int, heir_full_name: str):
        def perform_delete(e):
            try:
                deceased_service.delete_heir(heir_id_to_delete)
                page.open(
                    SnackBar(
                        content=Text(
                            f"{heir_full_name} さんの情報を削除しました。",
                            color=Colors.WHITE,
                        ),
                        bgcolor=Colors.GREEN_700,
                        duration=1500,
                    )
                )
                update_heirs_list()
            except Exception as ex:
                page.open(
                    SnackBar(
                        content=Text(f"削除中にエラーが発生しました: {ex}", color=Colors.WHITE),
                        bgcolor=Colors.RED_700,
                        duration=3000,
                    )
                )

        show_confirm_dialog(
            page=page,
            title="相続人削除の確認",
            message=f"【{heir_full_name}】の相続人情報を削除します。この操作は元に戻せません。よろしいですか？",
            confirm_text="削除する",
            on_confirm=perform_delete,
            confirm_color=Colors.RED_600,
        )

    if not is_new_deceased and not is_new_client_case:
        update_heirs_list()

    manager_field = Text(
        f"担当1 (進捗): {USER_MAP.get(case.manager_id, '未割当')}"
        if case is not None and case.manager_id is not None
        else "担当1 (進捗): 未割当",
        size=14,
        width=250,
    )

    operator_field = Text(
        f"担当2 (実務): {USER_MAP.get(case.operator_id, '未割当')}"
        if case is not None and case.operator_id is not None
        else "担当2 (実務): 未割当",
        size=14,
        width=250,
    )

    view_controls = [
        AppBar(title=Text("被相続人 詳細/相続人管理"), bgcolor=Colors.BLUE_GREY_700),
        Container(
            content=Column(
                [
                    Container(
                        content=Column(
                            [
                                Row(
                                    [
                                        Container(
                                            content=Text(
                                                f"案件番号: {case.case_number if case and case.case_number else 'N/A (未登録)'}",
                                                size=18,
                                                weight=FontWeight.BOLD,
                                            ),
                                            on_click=lambda e,
                                            content=(
                                                case.case_number
                                                if case and case.case_number
                                                else ""
                                            ): copy_to_clipboard_and_notify(e, page, content),
                                            tooltip="クリックして案件番号をコピー",
                                        ),
                                        ElevatedButton(
                                            "Kintone入力",
                                            icon=Icons.CLOUD_UPLOAD,
                                            on_click=lambda e: launch_kintone_automation(case.case_id) if case else None,
                                            style=ButtonStyle(
                                                bgcolor=Colors.AMBER_100,
                                                color=Colors.BROWN_900,
                                            ),
                                            tooltip="Kintoneを開き、詳細情報を自動入力します"
                                        ),
                                        Container(width=10),
                                        ElevatedButton(
                                            "案件を完全に削除",
                                            on_click=lambda e: page.open(delete_confirm_dialog),
                                            icon=Icons.DELETE_FOREVER,
                                            icon_color=Colors.RED,
                                            bgcolor=Colors.BLUE_50,
                                            color=Colors.BLUE_800,
                                        ),
                                    ],
                                    alignment=MainAxisAlignment.SPACE_BETWEEN,
                                    vertical_alignment=CrossAxisAlignment.CENTER,
                                ),
                                Divider(height=10, color=Colors.TRANSPARENT),
                                Row(
                                    [
                                        Text(
                                            "👥 担当者情報",
                                            size=18,
                                            weight=FontWeight.BOLD,
                                        ),
                                        IconButton(
                                            Icons.EDIT,
                                            icon_color=Colors.BLUE_500,
                                            tooltip="案件担当者を編集",
                                            on_click=open_assignment_dialog,
                                        ),
                                    ],
                                    alignment=MainAxisAlignment.START,
                                ),
                                Row(
                                    [manager_field, operator_field],
                                    alignment=MainAxisAlignment.START,
                                ),
                            ]
                        ),
                        visible=not is_new_client_case and not is_new_deceased and case is not None,
                    ),
                    Divider(
                        visible=not is_new_client_case and not is_new_deceased and case is not None
                    ),
                    Row(
                        [
                            Text(
                                "👤 被相続人情報",
                                size=18,
                                weight=FontWeight.BOLD,
                            ),
                            Text(
                                "【新規登録モード】",
                                size=16,
                                color=Colors.RED_500,
                                visible=is_new_deceased or is_new_client_case,
                            ),
                            IconButton(
                                Icons.EDIT,
                                icon_color=Colors.BLUE_500,
                                tooltip="被相続人を編集 (別ページへ遷移)",
                                on_click=go_to_deceased_edit_page,
                            ),
                        ]
                    ),
                    Row(
                        [
                            Container(
                                content=Text(
                                    f"名前: {full_name}",
                                    weight=FontWeight.BOLD,
                                    size=16,
                                    width=200,
                                ),
                                on_click=lambda e, content=full_name: copy_to_clipboard_and_notify(
                                    e, page, content
                                ),
                                tooltip="クリックして氏名をコピー",
                            ),
                            Column(
                                [
                                    Container(
                                        content=Text(
                                            f"生年月日（西暦）: {dob_date_obj.isoformat() if dob_date_obj else '未登録'}",
                                            size=14,
                                            width=250,
                                        ),
                                        on_click=lambda e,
                                        content=(
                                            dob_date_obj.isoformat() if dob_date_obj else "未登録"
                                        ): copy_to_clipboard_and_notify(e, page, content),
                                        tooltip="クリックして西暦をコピー",
                                    ),
                                    Text(
                                        f"生年月日（和暦）: {convert_seireki_to_wareki(dob_date_obj) if dob_date_obj else '未登録'}",
                                        size=12,
                                        color=Colors.BLUE_GREY_600,
                                    ),
                                ],
                                spacing=2,
                            ),
                            Column(
                                [
                                    Container(
                                        content=Text(
                                            f"死亡日（西暦）: {dod_date_obj.isoformat() if dod_date_obj else '未登録'}",
                                            size=14,
                                            width=250,
                                        ),
                                        on_click=lambda e,
                                        content=(
                                            dod_date_obj.isoformat() if dod_date_obj else "未登録"
                                        ): copy_to_clipboard_and_notify(e, page, content),
                                        tooltip="クリックして西暦をコピー",
                                    ),
                                    Text(
                                        f"死亡日（和暦）: {convert_seireki_to_wareki(dod_date_obj) if dod_date_obj else '未登録'}",
                                        size=12,
                                        color=Colors.BLUE_GREY_600,
                                    ),
                                ],
                                spacing=2,
                            ),
                        ],
                        alignment=MainAxisAlignment.START,
                    ),
                    Row(
                        [
                            Container(
                                content=Text(
                                    f"最後の住所: {display_deceased_address}",
                                    size=14,
                                    width=600,
                                ),
                                on_click=lambda e,
                                content=copyable_full_address: copy_to_clipboard_and_notify(
                                    e, page, content
                                ),
                                tooltip="クリックして現住所をコピー",
                            ),
                        ],
                        alignment=MainAxisAlignment.START,
                        visible=not is_new_client_case and not is_new_deceased,
                    ),
                    Divider(),
                    Column(
                        [
                            Row(
                                [
                                    Text(
                                        "👨‍👩‍👧‍👦 相続人リスト",
                                        size=16,
                                    ),
                                    ElevatedButton(
                                        "新しい相続人を追加",
                                        icon=Icons.ADD,
                                        on_click=go_to_new_heir_page,
                                    ),
                                ],
                                vertical_alignment=CrossAxisAlignment.CENTER,
                            ),
                            Container(
                                content=heirs_controls,
                                border=border.all(1, Colors.BLACK12),
                                padding=10,
                                width=page.width * 0.8,
                            ),
                        ],
                        visible=not is_new_deceased and not is_new_client_case,
                    ),
                    Divider(),
                    Container(
                        content=Column(
                            [
                                Text(
                                    "📁 案件フォルダ保存パス",
                                    weight=FontWeight.BOLD,
                                    size=18,
                                ),
                                Row(
                                    [
                                        path_field,
                                        ElevatedButton(
                                            "フォルダ選択",
                                            icon=Icons.FOLDER_OPEN,
                                            on_click=open_folder_dialog_detail,
                                        ),
                                    ]
                                ),
                                Text(
                                    "※フォルダを選択するとパスが即座に保存されます。",
                                    size=12,
                                    color=Colors.BLUE_GREY_400,
                                ),
                            ]
                        ),
                        width=page.width * 0.8,
                        visible=case is not None,
                    ),
                    Divider(),
                    Row(
                        [
                            ElevatedButton("👈 一覧へ戻る", on_click=lambda e: page.go("/")),
                        ],
                        spacing=20,
                    ),
                ],
                horizontal_alignment=CrossAxisAlignment.START,
            ),
            padding=20,
        ),
    ]

    def on_view_show_handler(e):
        page.update()

        if is_new_client_case:
            page.go("/deceased_edit/-1")
            return
        elif is_new_deceased:
            page.go("/deceased_edit/0")
            return

        if not is_new_deceased and not is_new_client_case:
            update_heirs_list()

        if case:
            current_path = deceased_service.get_case_folder_path(case.case_id) or ""
            path_field.value = current_path
        else:
            path_field.value = ""

        page.update()

    view = View(
        f"/detail/{case_id}",
        view_controls,
        scroll=ScrollMode.AUTO,
    )

    view.on_view_show = on_view_show_handler
    return view