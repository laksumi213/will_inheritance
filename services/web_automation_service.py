# /services/web_automation_service.py

import threading
from time import sleep
from flet import Page, SnackBar, Text, Colors
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, WebDriverException

# 既存のWeb操作クラスを使用
from components.utils.web_operation import Web 

class WebAutomationService:
    def __init__(self, page: Page = None):
        self.page = page
        self.proc = Web() # Web操作ヘルパーのインスタンス化
        self.driver = None

    def close(self):
        if self.proc and self.proc.driver:
            try:
                self.proc.driver.quit()
            except:
                pass

    def _show_snackbar(self, message, color=Colors.GREEN):
        if self.page:
            self.page.open(
                SnackBar(
                    content=Text(message, color=Colors.WHITE),
                    bgcolor=color,
                    duration=3000,
                )
            )
            self.page.update()
        else:
            print(message)

    # --- イオン銀行 自動化ロジック ---
    def run_aeon_automation(self, data: dict):
        target_url = "https://entry.aeonbank.co.jp/rm/W_CreateReservation?shopId=386"
        threading.Thread(target=self._aeon_task, args=(target_url, data)).start()

    def _aeon_task(self, url, data):
        try:
            self.proc.web_open(url)
            self.driver = self.proc.driver
            print(f"Opening: {url}")

            # フォームの入力項目（姓）が表示されるまで待機
            print("ユーザーの日付選択を待機中...")
            WebDriverWait(self.driver, 300).until(
                EC.presence_of_element_located((By.NAME, "page:form-pc:input-pageBlock-pc:j_id241"))
            )
            print("入力フォームを検知しました。自動入力を開始します。")

            # 1. ご予約内容
            try:
                visit_radio = self.driver.find_element(By.ID, "page:form-pc:pageBlock-pc:j_id163:0")
                self.driver.execute_script("arguments[0].click();", visit_radio)
            except:
                pass 

            try:
                consultation_select = self.driver.find_element(By.ID, "page:form-pc:pageBlock-pc:consultationPc")
                Select(consultation_select).select_by_value("a0g0o00000iC7jxAAC") 
            except:
                pass

            # 2. お客さま情報
            self.driver.find_element(By.NAME, "page:form-pc:input-pageBlock-pc:j_id241").send_keys(data.get("last_name", ""))
            self.driver.find_element(By.NAME, "page:form-pc:input-pageBlock-pc:j_id242").send_keys(data.get("first_name", ""))
            self.driver.find_element(By.NAME, "page:form-pc:input-pageBlock-pc:j_id247").send_keys(data.get("last_name_kana", ""))
            self.driver.find_element(By.NAME, "page:form-pc:input-pageBlock-pc:j_id248").send_keys(data.get("first_name_kana", ""))

            # 口座有無
            if data.get("has_account") == "yes":
                account_radio = self.driver.find_element(By.ID, "page:form-pc:input-pageBlock-pc:j_id253:0")
            else:
                account_radio = self.driver.find_element(By.ID, "page:form-pc:input-pageBlock-pc:j_id253:1")
            self.driver.execute_script("arguments[0].click();", account_radio)

            # 電話番号
            self.driver.find_element(By.NAME, "page:form-pc:input-pageBlock-pc:j_id258").send_keys(data.get("tel", ""))

            # 電話連絡希望
            if data.get("request_contact") == "yes":
                contact_radio = self.driver.find_element(By.ID, "page:form-pc:input-pageBlock-pc:j_id262:1")
            else:
                contact_radio = self.driver.find_element(By.ID, "page:form-pc:input-pageBlock-pc:j_id262:0")
            self.driver.execute_script("arguments[0].click();", contact_radio)

            # メールアドレス
            self.driver.find_element(By.ID, "page:form-pc:input-pageBlock-pc:input-mail").send_keys(data.get("email", ""))
            self.driver.find_element(By.NAME, "page:form-pc:input-pageBlock-pc:j_id269").send_keys(data.get("email_confirm", ""))
            self.driver.find_element(By.NAME, "page:form-pc:input-pageBlock-pc:j_id273").send_keys(data.get("other_content", ""))

            # 3. 同意事項
            try:
                agree_checkbox = self.driver.find_element(By.ID, "page:form-pc:input-pageBlock-pc:agree")
                if not agree_checkbox.is_selected():
                    self.driver.execute_script("arguments[0].click();", agree_checkbox)
            except:
                print("同意チェックボックスが見つかりませんでした")
            
            # 💡 修正: 画面を日時選択エリア（上部）へスクロール
            try:
                # 日時選択エリアのID (HTMLソースより)
                date_section = self.driver.find_element(By.ID, "page:form-pc:pageBlock-pc:dateTime-pc")
                self.driver.execute_script("arguments[0].scrollIntoView(true);", date_section)
                print("日時選択エリアへスクロールしました。")
            except:
                # 要素が見つからない場合はページトップへ
                self.driver.execute_script("window.scrollTo(0, 0);")
                print("ページトップへスクロールしました。")

            self._show_snackbar("イオン銀行: 自動入力が完了しました。内容を確認して進めてください。")

        except Exception as e:
            self._show_snackbar(f"イオン銀行 自動化エラー: {e}", Colors.RED)
            print(f"Aeon Automation Error: {e}")


    # ... (SBI新生銀行のコードは変更なし) ...
    def run_sbi_shinsei_automation(self, data: dict):
        target_url = "https://webforms.sbishinseibank.co.jp/reserve/input?type=inv_sfc&lid=temp_bran_btn_03&h=form&intcid=temp_bran_btn_03"
        threading.Thread(target=self._sbi_task, args=(target_url, data)).start()

    def _sbi_task(self, url, data):
        try:
            self.proc.web_open(url)
            self.driver = self.proc.driver
            print(f"Opening: {url}")

            print("ユーザーの日付選択を待機中...")
            WebDriverWait(self.driver, 300).until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, '姓') or contains(@name, 'last_name')]"))
            )
            print("入力フォームを検知しました。自動入力を開始します。")
            
            try:
                sei_input = self.driver.find_element(By.XPATH, "//input[contains(@placeholder, '姓') or contains(@name, 'last_name')]")
                sei_input.send_keys(data.get("last_name", ""))
                
                mei_input = self.driver.find_element(By.XPATH, "//input[contains(@placeholder, '名') or contains(@name, 'first_name')]")
                mei_input.send_keys(data.get("first_name", ""))
            except:
                print("Name fields not found.")

            try:
                sei_kana_input = self.driver.find_element(By.XPATH, "//input[contains(@placeholder, 'セイ') or contains(@name, 'last_name_kana')]")
                sei_kana_input.send_keys(data.get("last_name_kana", ""))
                mei_kana_input = self.driver.find_element(By.XPATH, "//input[contains(@placeholder, 'メイ') or contains(@name, 'first_name_kana')]")
                mei_kana_input.send_keys(data.get("first_name_kana", ""))
            except:
                print("Kana fields not found.")

            try:
                tel_input = self.driver.find_element(By.XPATH, "//input[contains(@type, 'tel') or contains(@name, 'tel')]")
                tel_input.send_keys(data.get("tel", ""))
            except:
                pass

            try:
                email_input = self.driver.find_element(By.XPATH, "//input[contains(@type, 'email') or contains(@name, 'mail')]")
                email_input.send_keys(data.get("email", ""))
            except:
                pass

            try:
                memo_input = self.driver.find_element(By.TAG_NAME, "textarea")
                memo_input.send_keys(data.get("other_content", ""))
            except:
                pass

            self._show_snackbar("SBI新生銀行: 自動入力が完了しました。")

        except Exception as e:
            self._show_snackbar(f"SBI新生銀行 自動化エラー: {e}", Colors.RED)
            print(f"SBI Shinsei Automation Error: {e}")