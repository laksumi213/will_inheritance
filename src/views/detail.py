# src/views/detail.py

import threading
import time
import os
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Dict, Any, List

# Flet Imports
from flet import (
    AlertDialog,
    ButtonStyle,
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
)

# Selenium / Automation Imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
from dotenv import load_dotenv

# Internal Imports
from src.utils.date_utils import (
    convert_seireki_to_wareki,
)
from src.utils.ui_utils import show_confirm_dialog

from src.services.deceased_service import (
    get_all_users,
    get_address_by_id,
    get_address_info,
    get_case_by_id,
    get_case_folder_path,
    get_contact_info,
    get_deceased_by_case_id,
    get_deceased_by_id,
    get_kintone_integration_data,
    update_case_assignment,
    update_case_folder_path,
    delete_case_and_all_related_data,
    delete_heir,
    update_case_number,  # 案件番号更新用
    normalize_folder_path, # パス正規化用
)


# ---------------------------------------------
# 💡 Kintone 自動化ロジック (Selenium版)
# ---------------------------------------------
def launch_kintone_automation(case_id: int) -> None:
    """
    Seleniumを使用してKintoneの案件登録画面を自動操作する。
    別スレッドで実行され、UIをブロックしない。
    """
    
    # 1. DBからデータ取得
    kintone_data = get_kintone_integration_data(case_id)
    if not kintone_data:
        print("エラー: データが見つかりませんでした")
        return

    load_dotenv()
    KINTONE_USER = os.getenv("KINTONE_USER")
    KINTONE_PASS = os.getenv("KINTONE_PASS")

    def show_manual_instruction(message: str) -> None:
        """ユーザーへの操作指示を表示 (Tkinter使用 - メインスレッド外で動作)"""
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            messagebox.showinfo("操作のお願い", message)
            root.destroy()
        except Exception as e:
            print(f"Dialog Error: {e}")

    def _run_browser() -> None:
        try:
            options = webdriver.ChromeOptions()
            options.add_experimental_option("detach", True)
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            driver.maximize_window()
            # ターゲットURL (環境に合わせて変更してください)
            target_url = "https://chester-tax.cybozu.com/k/242/edit"
            driver.get(target_url)
            
            wait = WebDriverWait(driver, 600)  # ログイン待ち
            action_wait = WebDriverWait(driver, 10)  # 操作待ち

            # --- A. ログイン処理 ---
            try:
                if "login" in driver.current_url:
                    print("ログイン画面検知。")
                    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, "username")))
                    if KINTONE_USER:
                        driver.find_element(By.NAME, "username").send_keys(KINTONE_USER)
                    if KINTONE_PASS:
                        driver.find_element(By.NAME, "password").send_keys(KINTONE_PASS)
                    
                    # Enterキーでログイン
                    driver.find_element(By.NAME, "password").send_keys(Keys.ENTER)
            except Exception:
                pass 

            # --- B. 編集画面ロード待ち ---
            print("編集画面のロードを待機中...")
            try:
                wait.until(EC.visibility_of_element_located((By.XPATH, "//button[contains(text(), '保存')]")))
                print("編集画面ロード完了")
                time.sleep(1.0)
            except TimeoutException:
                print("タイムアウト: 編集画面に到達できませんでした。")
                return

            driver.execute_script("document.body.style.zoom='80%'")
            time.sleep(0.5)

            # --- C. ヘルパー関数 ---
            def find_target_element(label: str, element_type: str = "input", xpath: str = "") -> Any:
                label_condition = f".//span[contains(@class, 'control-label-text-gaia') and normalize-space(text())='{label}']"
                target_inner = ""
                
                if element_type == "dropdown":
                    if xpath:
                        return action_wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                    else:
                        target_inner = ".//div[contains(@class, 'kintone-app-record-input-dropdown')]"
                elif element_type == "user":
                    target_inner = ".//input[contains(@class, 'kintone-app-record-input-user-select-input')]"
                else: 
                    # 通常のinput要素検索
                    label_xpath = f"//span[contains(@class, 'control-label-text-gaia') and contains(text(), '{label}')]"
                    container_xpath = f"({label_xpath})[1]/ancestor::div[contains(@class, 'control-gaia')][1]"
                    target_xpath = f"{container_xpath}//input[not(@type='hidden')]"
                    try:
                        return action_wait.until(EC.presence_of_element_located((By.XPATH, target_xpath)))
                    except Exception:
                        pass # 次の複合XPathへ

                xpath_combined = f"//div[contains(@class, 'control-gaia')][{label_condition}]{target_inner}"
                try:
                    elem = action_wait.until(EC.presence_of_element_located((By.XPATH, xpath_combined)))
                    return elem
                except TimeoutException:
                    print(f"    ❌ エラー: 「{label}」の {element_type} が見つかりません")
                    raise

            def input_text_keyboard(label: str, value: str, clear: bool = False) -> None:
                if not value: return
                try:
                    elem = find_target_element(label, "input")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                    driver.execute_script("arguments[0].click();", elem)
                    time.sleep(0.1)

                    if clear:
                        elem.send_keys(Keys.CONTROL, "a")
                        elem.send_keys(Keys.DELETE)
                    
                    if clear or not elem.get_attribute("value"):
                        elem.send_keys(value)
                        time.sleep(0.1)
                        elem.send_keys(Keys.TAB)
                    else:
                        print(f"    ℹ️ 入力スキップ(値あり): {label}")
                except Exception:
                    print(f"    ❌ エラー: {label}")

            def select_dropdown_arrow(label: str, down_count: int, div: str) -> None:
                try:
                    dropdown_div = driver.find_element(By.XPATH, div)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dropdown_div)
                    dropdown_div.click()
                    time.sleep(0.5)
                    for _ in range(down_count):
                        dropdown_div.send_keys(Keys.ARROW_DOWN)
                        time.sleep(0.1)
                    dropdown_div.send_keys(Keys.ENTER)
                    time.sleep(0.2)
                    dropdown_div.send_keys(Keys.TAB)
                except Exception as e:
                    print(f"    ❌ 選択エラー: {label} ({e})")

            def input_user_select_arrow(label: str, user_name: str, div: str) -> None:
                if not user_name: return
                try:
                    input_area = driver.find_element(By.XPATH, div)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", input_area)
                    driver.execute_script("arguments[0].click();", input_area)
                    input_area.clear()
                    input_area.send_keys(user_name)
                    time.sleep(2.0) 
                    input_area.send_keys(Keys.ARROW_DOWN)
                    time.sleep(0.2)
                    input_area.send_keys(Keys.ENTER)
                    time.sleep(0.2)
                    input_area.send_keys(Keys.TAB)
                except Exception as e:
                    print(f"    ❌ ユーザー選択エラー: {label} ({e})")

            # --- D. 実行フロー ---
            print("--- 基本情報 入力開始 ---")
            input_text_keyboard("顧客コード", kintone_data["case_number"])
            
            # ドロップダウン (XPathは環境依存の可能性があるため注意)
            select_dropdown_arrow("拠点", 5, "//div[./span[@id=':kf']]")
            select_dropdown_arrow("チーム", 3, "//div[./span[@id=':km']]")
            
            input_text_keyboard("担当者①", "森町")
            input_text_keyboard("担当者②", "森町")
            input_text_keyboard("面談対応者（MC）", "森町")
            
            # 行チェ通知先 (XPath修正が必要な場合あり)
            input_user_select_arrow("行チェ通知先", "森町", '//*[@id=":nsearch-:o-text"]')

            print("--- 顧客情報 ---")
            input_text_keyboard("郵便番号", kintone_data["client_zip"])
            input_text_keyboard("顧客名", kintone_data["client_name"])
            input_text_keyboard("被相続人名", kintone_data["deceased_name"])
            
            time.sleep(3.0) # 補完待ち
            
            input_text_keyboard("住所", kintone_data["client_addr"], clear=True)
            input_text_keyboard("顧客名(ふりがな)", kintone_data["client_kana"], clear=True)
            input_text_keyboard("被相続人名（ふりがな）", kintone_data["deceased_kana"], clear=True)
            
            input_text_keyboard("TEL", kintone_data["client_tel"])
            input_text_keyboard("メールアドレス", kintone_data["client_mail"])
            input_text_keyboard("相続開始日", kintone_data["inheritance_date"])

            print("--- 手動操作リクエスト ---")
            show_manual_instruction("【案件情報】タブをクリックして開いてください。\n\n切り替えが終わったら、このウィンドウの「OK」を押してください。")
            time.sleep(1.0)

            print("--- 案件情報 入力開始 ---")
            from datetime import datetime
            today_str = datetime.now().strftime("%Y-%m-%d")
            input_text_keyboard("紹介日", today_str)
            select_dropdown_arrow("◎登記", 2, "") 

            print("✅ 全項目の入力処理が完了しました。")

        except Exception as e:
            print(f"❌ Kintone Automation Error: {e}")

    threading.Thread(target=_run_browser, daemon=True).start()


def copy_to_clipboard_and_notify(e, page: Page, content: str) -> None:
    """クリックされたテキストをクリップボードにコピーし、SnackBarで通知する"""
    text_to_copy = str(content).strip()
    if not text_to_copy or text_to_copy in ["N/A", "未登録", "None", "〒未登録"]:
        return
    page.set_clipboard(text_to_copy)
    page.open(
        SnackBar(
            content=Text(f"'{text_to_copy[:30]}' をコピーしました。", color=Colors.ON_INVERSE_SURFACE),
            bgcolor=Colors.INVERSE_SURFACE,
            duration=1500,
        )
    )
    page.update()


def DeceasedDetailView(page: Page, case_id: int) -> View:
    # --- UI 初期化 ---
    file_picker = FilePicker(on_result=lambda e: page.update())
    if file_picker not in page.overlay:
        page.overlay.append(file_picker)

    # データの取得
    case = get_case_by_id(case_id)
    # ケースIDから被相続人を取得（存在しない場合はNone）
    deceased = get_deceased_by_case_id(case_id)

    is_new_client_case = case_id == -1
    is_new_deceased = case_id == 0
    # 被相続人IDの特定（新規の場合は0または-1）
    deceased_id = deceased.id if deceased else case_id

    # 💡 新規作成モードの場合のリダイレクト処理
    if is_new_client_case:
        page.run_thread(lambda: page.go("/deceased_edit/-1"))
        return View(f"/detail/{case_id}", controls=[]) # リダイレクト中に表示する空のView

    if is_new_deceased:
        page.run_thread(lambda: page.go("/deceased_edit/0"))
        return View(f"/detail/{case_id}", controls=[]) # リダイレクト中に表示する空のView

    # ユーザーリストの取得（リロードごとに最新化）
    user_map = get_all_users()
    user_options = [dropdown.Option(str(uid), name) for uid, name in user_map.items()]
    user_options.insert(0, dropdown.Option("", "未割当"))

    # 担当者ドロップダウン定義
    dialog_manager_field = Dropdown(
        label="担当者1 (進捗管理)",
        width=200,
        options=user_options,
        value="",
    )
    dialog_operator_field = Dropdown(
        label="担当者2 (実務担当)", 
        width=200, 
        options=user_options, 
        value=""
    )

    # 最後の住所取得
    last_address = None
    if deceased and deceased.last_address_id:
        last_address = get_address_by_id(deceased.last_address_id)

    display_deceased_address = "未登録"
    copyable_full_address = "未登録"
    deceased_zip_code = "〒未登録"

    if last_address:
        address_parts = [
            last_address.prefecture,
            last_address.city_ward_town,
            last_address.street_address,
        ]
        raw_deceased_address = "".join(filter(None, address_parts))
        building = last_address.building_name if last_address.building_name else ""
        zip_code = last_address.zip_code if last_address.zip_code else ""
        deceased_zip_code = f"〒{zip_code}"

        if raw_deceased_address:
            display_deceased_address = raw_deceased_address
            if building:
                display_deceased_address += f" ({building})"
        elif building:
            display_deceased_address = f"建物名: {building}"

        copyable_full_address = (
            f"〒{zip_code} {raw_deceased_address} {building}" if raw_deceased_address else "未登録"
        ).strip()

    # 案件オブジェクトの再確認（被相続人経由で取得できている場合）
    case = deceased.case if deceased and deceased.case else case

    # 表示用文字列の生成
    if deceased and not is_new_client_case:
        full_name = f"{deceased.name_last} {deceased.name_first}"
        dob_date_obj = deceased.date_of_birth
        dob_display_str = (
            f"{dob_date_obj.strftime('%Y/%m/%d')} ({convert_seireki_to_wareki(dob_date_obj)})"
            if dob_date_obj else "未登録"
        )
        dod_date_obj = deceased.date_of_death
        dod_display_str = (
            f"{dod_date_obj.strftime('%Y/%m/%d')} ({convert_seireki_to_wareki(dod_date_obj)})"
            if dod_date_obj else "未登録"
        )
    elif is_new_client_case or is_new_deceased or deceased is None:
        full_name = "【未登録】"
        dob_display_str = "N/A"
        dod_display_str = "N/A"
        # ダミーオブジェクト生成
        deceased = type("Dummy", (object,), {
            "id": 0, "name_last": "", "name_first": "", "heirs": [], "case": None, "last_address_id": None
        })()
        case = None

    # --- 案件番号インライン編集ロジック ---
    case_number_container = Container()
    edit_case_number_field = TextField(
        label="案件番号", width=200, height=40, content_padding=10, text_size=14, autofocus=True
    )

    def save_case_number_inline(e):
        new_num = edit_case_number_field.value.strip()
        if not new_num:
            page.open(SnackBar(Text("案件番号は必須です"), bgcolor=Colors.ERROR))
            return
        # 重複チェック＆更新
        if case and update_case_number(case.case_id, new_num):
            page.open(SnackBar(Text("案件番号を更新しました"), bgcolor=Colors.GREEN))
            case.case_number = new_num # メモリ上の値を更新
            render_view_mode()
        else:
            page.open(SnackBar(Text("更新失敗: 案件番号が重複しているか、エラーが発生しました"), bgcolor=Colors.ERROR))

    def render_edit_mode(e=None):
        if not case: return
        edit_case_number_field.value = case.case_number
        case_number_container.content = Row([
            edit_case_number_field,
            IconButton(Icons.CHECK, icon_color=Colors.GREEN, on_click=save_case_number_inline, tooltip="保存"),
            IconButton(Icons.CLOSE, icon_color=Colors.RED, on_click=lambda _: render_view_mode(), tooltip="キャンセル"),
        ])
        case_number_container.update()

    def render_view_mode(e=None):
        current_num = case.case_number if case else "New"
        case_number_container.content = Row([
            Container(
                content=Text(f"案件番号: {current_num}", size=20, weight=FontWeight.BOLD, color=Colors.PRIMARY),
                on_click=lambda e: copy_to_clipboard_and_notify(e, page, current_num),
                tooltip="クリックしてコピー"
            ),
            IconButton(Icons.EDIT, icon_color=Colors.PRIMARY, tooltip="案件番号を編集", on_click=render_edit_mode)
        ])
        if case_number_container.page:
            case_number_container.update()

    # 初期描画設定
    render_view_mode()

    # --- フォルダパス設定 ---
    path_field = TextField(
        label="フォルダ保存パス", 
        width=600, 
        value=""
    )
    
    def save_path_on_blur(e):
        """
        フォーカス外れ、またはEnterキー押下時にパスを保存する。
        """
        # 1. 値の取得（前後の空白除去）
        current_input = path_field.value.strip()
        print(f"DEBUG: Path save requested. Input='{current_input}', CaseID={case_id}")

        # 2. CaseIDの検証（View引数のcase_idを使用）
        if not case_id or case_id <= 0:
             print("DEBUG: Invalid CaseID, skipping save.")
             return

        # 3. 入力が空の場合は元の値を復元
        if not current_input:
            saved_path = get_case_folder_path(case_id)
            path_field.value = saved_path or ""
            path_field.update()
            return

        # 4. パスの正規化と保存
        # 引用符が含まれている場合は除去（Windowsのパスをコピペした時用）
        clean_input = current_input.strip('"').strip("'")
        
        # 保存実行
        success = update_case_folder_path(case_id, clean_input)
        
        if success:
            # 入力フィールドを更新（正規化された結果を表示したい場合は再取得推奨だが、ここでは入力を維持）
            path_field.value = clean_input
            path_field.update()
            page.open(SnackBar(Text(f"フォルダパスを保存しました", color=Colors.WHITE), bgcolor=Colors.GREEN_700))
        else:
            page.open(SnackBar(Text("フォルダパスの保存に失敗しました。", color=Colors.WHITE), bgcolor=Colors.RED_700))
        
    # イベントハンドラ登録
    path_field.on_blur = save_path_on_blur
    path_field.on_submit = save_path_on_blur # Enterキー対応
    
    def open_folder_dialog_detail(e):
        # フォルダ選択後に即時保存
        def on_result(e: FilePickerResultEvent):
            if e.path:
                path_field.value = e.path
                path_field.update()
                save_path_on_blur(e)
        
        file_picker.on_result = on_result
        file_picker.get_directory_path(dialog_title="案件フォルダの保存先を選択")

    # --- 削除確認ダイアログ ---
    def create_delete_confirm_dialog(case_num: str):
        def confirm_delete_case(e):
            if delete_case_and_all_related_data(case_num):
                page.go("/")
            else:
                page.open(SnackBar(Text("削除処理に失敗しました"), bgcolor=Colors.ERROR))
            delete_confirm_dialog.open = False
            page.update()

        delete_confirm_dialog = AlertDialog(
            modal=True,
            title=Text("案件削除の確認", weight=FontWeight.BOLD, color=Colors.ERROR),
            content=Text(f"案件 {case_num} を完全に削除しますか？\n被相続人、相続人、タスクなど全ての情報が削除され、元に戻せません。"),
            actions=[
                TextButton("キャンセル", on_click=lambda e: setattr(delete_confirm_dialog, 'open', False) or page.update()),
                ElevatedButton("完全に削除", on_click=confirm_delete_case, bgcolor=Colors.ERROR, color=Colors.WHITE),
            ],
            actions_alignment=MainAxisAlignment.END,
        )
        return delete_confirm_dialog

    delete_confirm_dialog = create_delete_confirm_dialog(case.case_number if case else "N/A")

    # --- 担当者編集ダイアログ ---
    def create_assignment_dialog():
        return AlertDialog(
            modal=True,
            title=Text("案件担当者 編集"),
            content=Container(
                content=Column([
                    Text(f"案件: {case.case_number if case else ''}"), 
                    Divider(), 
                    dialog_manager_field, 
                    dialog_operator_field
                ], tight=True),
                height=200, width=400
            ),
            actions=[
                TextButton("キャンセル", on_click=lambda e: close_dialog()),
                ElevatedButton("保存", on_click=lambda e: save_assignment_dialog()),
            ],
        )

    assignment_edit_dialog = create_assignment_dialog()

    def close_dialog():
        assignment_edit_dialog.open = False
        page.update()

    def save_assignment_dialog():
        if not case: return close_dialog()
        
        m_id = int(dialog_manager_field.value) if dialog_manager_field.value else None
        o_id = int(dialog_operator_field.value) if dialog_operator_field.value else None
        
        update_case_assignment(case.case_id, m_id, o_id)
        
        # メモリ更新
        case.manager_id = m_id
        case.operator_id = o_id
        
        close_dialog()
        page.open(SnackBar(Text("担当者情報を更新しました"), bgcolor=Colors.GREEN))
        page.update()

    def open_assignment_dialog(e):
        if not case: return
        dialog_manager_field.value = str(case.manager_id) if case.manager_id else ""
        dialog_operator_field.value = str(case.operator_id) if case.operator_id else ""
        page.open(assignment_edit_dialog)
        page.update()

    # --- 相続人リスト構築 ---
    heirs_controls = Column()

    def update_heirs_list():
        """相続人一覧リストを更新する（ID削除、郵便番号追加、コピー機能強化）"""
        heirs_controls.controls.clear()
        # 確実に最新のデータを取得
        current_deceased = get_deceased_by_id(deceased_id)
        
        if not current_deceased or not current_deceased.heirs:
            heirs_controls.controls.append(Text("相続人は登録されていません"))
            page.update()
            return
        
        if case:
            # フォルダパスをDBから最新化
            normalized_path = get_case_folder_path(case.case_id)
            path_field.value = normalized_path or ""

        for heir in current_deceased.heirs:
            heir_name = f"{heir.name_last} {heir.name_first}"
            mark = "【契約者】" if getattr(heir, "is_contracting_party", False) else ""
            
            # 連絡先・住所取得ロジック
            contacts = get_contact_info("heir", heir.id)
            address_info = get_address_info("heir", heir.id)
            
            # 電話番号
            phone = "未登録"
            for sub in ["Primary", "携帯", "自宅"]:
                found = next((c["value"] for c in contacts if c["type"] == "PHONE" and c["sub_type"] == sub), None)
                if found:
                    phone = found
                    break
            if phone == "未登録":
                found = next((c["value"] for c in contacts if c["type"] == "PHONE"), None)
                if found: phone = found
            
            # 郵便番号
            zip_code_val = address_info.get("zip_code", "")
            zip_str = f"〒{zip_code_val}" if zip_code_val else "〒未登録"

            # 住所
            addr_str = f"{address_info.get('prefecture', '')}{address_info.get('city_ward_town', '')}{address_info.get('street_address', '')}"
            if address_info.get("building_name"):
                addr_str += f" ({address_info.get('building_name')})"
            
            # --- 表示用行の作成 ---
            heirs_controls.controls.append(
                Row([
                    # IDは削除しました
                    
                    # 氏名
                    Container(
                        content=Text(f"{heir_name} {mark}", width=180, weight=FontWeight.BOLD),
                        on_click=lambda e, t=heir_name: copy_to_clipboard_and_notify(e, page, t),
                        tooltip="氏名をコピー"
                    ),
                    # 続柄
                    Text(heir.relationship_type or "-", width=60),
                    
                    # 電話番号
                    Container(
                        content=Text(f"📞 {phone}", width=130, size=13),
                        on_click=lambda e, t=phone: copy_to_clipboard_and_notify(e, page, t),
                        tooltip="電話番号をコピー"
                    ),
                    
                    # 💡 郵便番号 (追加)
                    Container(
                        content=Text(zip_str, width=90, size=13),
                        on_click=lambda e, t=zip_str: copy_to_clipboard_and_notify(e, page, t),
                        tooltip="郵便番号をコピー"
                    ),

                    # 住所
                    Container(
                        content=Text(f"🏠 {addr_str or '未登録'}", width=300, size=13, no_wrap=True, overflow="ellipsis"),
                        on_click=lambda e, t=addr_str: copy_to_clipboard_and_notify(e, page, t),
                        tooltip=addr_str
                    ),
                    
                    # アクションボタン
                    Row([
                        IconButton(
                            Icons.EDIT, 
                            icon_color=Colors.PRIMARY, 
                            tooltip="編集",
                            on_click=lambda e, hid=heir.id: page.go(f"/heir_edit/{hid}?deceased_id={deceased_id}")
                        ),
                        IconButton(
                            Icons.DELETE, 
                            icon_color=Colors.ERROR, 
                            tooltip="削除",
                            on_click=lambda e, hid=heir.id, hn=heir_name: open_heir_delete_confirm(hid, hn)
                        )
                    ], spacing=0)
                ])
            )
        page.update()

    def open_heir_delete_confirm(heir_id, name):
        def perform_delete(e):
            delete_heir(heir_id)
            update_heirs_list()
            page.open(SnackBar(Text(f"{name} さんの情報を削除しました"), bgcolor=Colors.GREEN))

        show_confirm_dialog(page, "相続人削除", f"【{name}】の情報を削除しますか？\nこの操作は元に戻せません。", "削除", perform_delete, Colors.ERROR)

    # 画面描画時にデータを最新化
    if not is_new_deceased and not is_new_client_case:
        update_heirs_list()
        
    if case: 
        # 初期表示時にも正規化されたパスを表示
        normalized_path = get_case_folder_path(case.case_id)
        path_field.value = normalized_path or ""

    # --- View Main Structure ---
    return View(
        f"/detail/{case_id}",
        [
            Container(
                content=Column([
                    # Header Section (Case Info & Actions)
                    Row([
                        case_number_container, # Inline Edit Component
                        Row([
                            ElevatedButton(
                                "Kintone入力", 
                                icon=Icons.CLOUD_UPLOAD, 
                                style=ButtonStyle(bgcolor=Colors.AMBER_100, color=Colors.BROWN_900),
                                on_click=lambda e: launch_kintone_automation(case.case_id) if case else None,
                                tooltip="Seleniumでブラウザを自動操作し、Kintoneに入力します"
                            ),
                            Container(width=10),
                            ElevatedButton(
                                "案件削除", 
                                icon=Icons.DELETE_FOREVER,
                                style=ButtonStyle(bgcolor=Colors.RED_50, color=Colors.RED_900),
                                on_click=lambda e: page.open(delete_confirm_dialog)
                            )
                        ])
                    ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                    
                    Divider(height=20, color=Colors.TRANSPARENT),

                    # Manager Info
                    Row([
                        Text("👥 担当者情報", size=18, weight=FontWeight.BOLD), 
                        IconButton(Icons.EDIT, icon_color=Colors.PRIMARY, on_click=open_assignment_dialog)
                    ]),
                    Row([
                        Text(f"担当1 (進捗): {user_map.get(case.manager_id, '未割当') if case else '-'}", width=250),
                        Text(f"担当2 (実務): {user_map.get(case.operator_id, '未割当') if case else '-'}", width=250),
                    ]),
                    
                    Divider(),

                    # Deceased Info
                    Row([
                        Text("👤 被相続人情報", size=18, weight=FontWeight.BOLD),
                        IconButton(
                            Icons.EDIT, 
                            icon_color=Colors.PRIMARY, 
                            on_click=lambda e: page.go(f"/deceased_edit/{deceased.id}") if deceased else None
                        )
                    ]),
                    Row([
                        Container(
                            content=Text(f"氏名: {full_name}", size=16, weight=FontWeight.BOLD), 
                            on_click=lambda e: copy_to_clipboard_and_notify(e, page, full_name),
                            tooltip="クリックして氏名をコピー"
                        ),
                        Column([
                            Text(f"生年月日: {dob_display_str}", size=12), 
                            Text(f"死亡日: {dod_display_str}", size=12)
                        ]),
                    ]),
                    Row([
                        Container(
                            content=Text(deceased_zip_code, weight=FontWeight.BOLD, color=Colors.PRIMARY), 
                            on_click=lambda e: copy_to_clipboard_and_notify(e, page, deceased_zip_code),
                            tooltip="クリックして郵便番号をコピー"
                        ),
                        Container(
                            content=Text(f"住所: {display_deceased_address}"), 
                            on_click=lambda e: copy_to_clipboard_and_notify(e, page, copyable_full_address),
                            tooltip="クリックして住所をコピー"
                        )
                    ]),

                    Divider(),

                    # Heirs List
                    Row([
                        Text("👨‍👩‍👧‍👦 相続人リスト", size=16, weight=FontWeight.BOLD),
                        ElevatedButton(
                            "追加", 
                            icon=Icons.ADD, 
                            on_click=lambda e: page.go(f"/heir_edit/new?deceased_id={deceased.id}") if deceased else None
                        )
                    ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                    
                    Container(
                        content=heirs_controls, 
                        padding=10, 
                        border=border.all(1, Colors.OUTLINE_VARIANT), 
                        border_radius=8
                    ),

                    Divider(),

                    # Folder Path
                    Text("📁 案件フォルダ", weight=FontWeight.BOLD),
                    Row([
                        path_field, 
                        ElevatedButton("選択", icon=Icons.FOLDER_OPEN, on_click=open_folder_dialog_detail)
                    ]),
                    
                    Divider(),
                    
                    # Back Button
                    ElevatedButton("👈 一覧へ戻る", on_click=lambda e: page.go("/"))
                    
                ], scroll=ScrollMode.AUTO),
                padding=20
            )
        ],
        scroll=ScrollMode.AUTO,
    )