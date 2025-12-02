# /components/pages/mizuho_visit_reserve_process.py

import threading
from time import sleep
from flet import Page, SnackBar, Text, Colors
from components.utils.web_operation import Web
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, WebDriverException
import mojimoji 
from services.deceased_service import get_financial_asset_automation_data

# 実行中のMizuhoReservationインスタンスを保持する辞書
_active_reservations = {}

# ----------------------------------------------------------------------------------
# メインプロセス関数
# ----------------------------------------------------------------------------------

def start_mizuho_reservation(page: Page, case_id: int, selected_branch: str, selected_procedure: str):
    """
    みずほ銀行の来店予約Web自動化処理を別スレッドで開始する。（ステップ1：日時選択前まで）
    """
    
    # データベースから必要なデータを取得
    target_bank_code = "0001"
    data = get_financial_asset_automation_data(case_id, target_bank_code)
    
    if not data:
        page.open(
            SnackBar(
                content=Text(f"エラー: データベースからみずほ銀行（{target_bank_code}）の予約に必要なデータが見つかりませんでした。", color=Colors.WHITE),
                bgcolor=Colors.RED_700
            )
        )
        page.update()
        return

    # 既に予約プロセスが進行中の場合は、クリーンアップして再開
    if case_id in _active_reservations:
        old_instance = _active_reservations[case_id]
        old_instance.cleanup() 
        del _active_reservations[case_id]
        
        page.open(SnackBar(
            content=Text("過去のWebセッションをリセットしました。新しい予約プロセスを開始します。", color=Colors.WHITE),
            bgcolor=Colors.AMBER_700
        ))
        page.update()

    # Web操作は時間がかかるため、別スレッドで実行
    def run_automation():
        try:
            # インスタンスを作成し、グローバル変数に保存
            reservation_instance = MizuhoReservation(page, data, selected_branch, selected_procedure)
            _active_reservations[case_id] = reservation_instance
            
            # ステップ1を実行（ブラウザを開き、日時選択画面まで遷移）
            reservation_instance.reservation()
            
            # ユーザーに日時選択後の操作を促す
            page.open(
                SnackBar(
                    content = Text("✅ 日時選択画面を表示しました。Webブラウザで日付と時間を選択し、「日時選択後に押す」ボタンをクリックしてください。", color=Colors.WHITE),
                    bgcolor = Colors.BLUE_700,
                    duration=600000
                )
            )
            
        except Exception as e:
            # エラー発生時はインスタンスを削除
            if case_id in _active_reservations:
                _active_reservations[case_id].cleanup()
                del _active_reservations[case_id]
            page.open(
                SnackBar(
                    content = Text(f"Web操作中にエラーが発生しました: {e}", color=Colors.WHITE),
                    bgcolor = Colors.RED_700
                )
            )
            
        finally:
            page.update()

    threading.Thread(target=run_automation).start()


def continue_mizuho_reservation(page: Page, case_id: int):
    """
    みずほ銀行の来店予約Web自動化処理を再開する。（ステップ2：お客さま情報入力以降）
    """
    if case_id not in _active_reservations:
        page.open(
            SnackBar(
                content=Text("エラー: 予約プロセスが開始されていません。「予約日時選択へ進む」ボタンを先にクリックしてください。", color=Colors.WHITE),
                bgcolor=Colors.RED_700
            )
        )
        page.update()
        return

    reservation_instance = _active_reservations[case_id]
    
    def run_automation_continue():
        try:
            driver = reservation_instance.driver

            # Web画面が閉じられていないかチェック (WebDriverExceptionもキャッチ)
            try:
                _ = driver.title 
            except (NoSuchElementException, WebDriverException) as e:
                page.open(SnackBar(
                    content=Text("エラー: Web画面が閉じられています。予約を最初からやり直してください。", color=Colors.WHITE),
                    bgcolor=Colors.RED_700
                ))
                # インスタンスを削除して終了
                reservation_instance.cleanup()
                if case_id in _active_reservations:
                    del _active_reservations[case_id]
                page.update()
                return # 処理を中断
                        
            # ユーザーに最終操作を促す
            page.open(
                SnackBar(
                    content = Text("✅ 最終確認画面に遷移しました。Webブラウザで「予約内容を確認」をクリックして予約を完了してください。", color=Colors.WHITE),
                    bgcolor = Colors.GREEN_700,
                    duration=300000
                )
            )
            
            # ステップ2を実行（お客さま情報入力）
            reservation_instance.start_proc() 

        except Exception as e:
            page.open(
                SnackBar(
                    content = Text(f"Web操作中にエラーが発生しました: {e}", color=Colors.WHITE),
                    bgcolor = Colors.RED_700
                )
            )

        finally:
            # 完了後、インスタンスを削除
            if case_id in _active_reservations:
                del _active_reservations[case_id]
            page.update()

    # threading.Thread(target=run_automation_continue).start()
    run_automation_continue()


# ----------------------------------------------------------------------------------
# Web自動化クラス
# ----------------------------------------------------------------------------------

class MizuhoReservation:
    def __init__(self, page: Page, data: dict, selected_branch, selected_procedure):
        self.page = page
        self.data = data
        self.selected_branch = selected_branch
        self.selected_procedure = selected_procedure
        self.proc = Web() # Web操作ヘルパーのインスタンス化 (シングルトン)
        
        self.deceased_name = self.data["deceased_name"]
        self.deceased_dob = self.data["deceased_dob"].split('-') if self.data["deceased_dob"] else ["0000", "00", "00"]
        self.bank_branch_code = self.data["bank_branch_code"]
        self.bank_account_number = self.data["bank_account_number"]
        self.staff_code = self.data["staff_code"]
        self.client_phone = self.data["client_phone"]
        self.client_email = self.data["client_email"]

        # 法人固定情報
        self.firm_name_kanji = self.data["firm_name_kanji"]
        self.firm_name_kana = self.data["firm_name_kana"]
        self.staff_name_kanji = self.data["staff_name_kanji"]
        self.staff_tel = self.data["staff_tel"]
        self.staff_mail = self.data["staff_mail"]
        self.firm_zip = self.data["firm_zip"]
        self.firm_addr2 = self.data["firm_addr2"]
        self.firm_dob_year = self.data["firm_dob_year"]
        self.firm_dob_month = self.data["firm_dob_month"]
        self.firm_dob_day = self.data["firm_dob_day"]

    # 💡 クリーンアップメソッド: シングルトンなので quit() は呼ばない
    def cleanup(self):
        """プロセス終了時の処理"""
        # シングルトンパターンのため、WebDriver全体を終了させる quit() は呼び出さない。
        # 必要に応じて、現在のタブを閉じる等の処理を記述するが、
        # 続けて別の操作を行う可能性を考慮し、ここでは何もしない。
        pass
        # try:
        #     if self.driver:
        #         self.driver.quit()
        # except Exception:
        #     pass

    def click_button_by_text(self, driver, text):
        """ボタンの表示テキストを使って要素を探し、クリックする関数"""
        xpath_locator = f"//button[text()='{text}']"
        try:
            button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath_locator))
            )
            button.click()
            sleep(0.5)
            print(f"✅ ボタン '{text}' をクリックしました。")
        except Exception:
            raise NoSuchElementException(f"エラー: ボタン '{text}' が見つからないか、クリックできませんでした。")

    def reservation(self):
        # ----------------------------------------------------
        # 1. 予約開始ページのオープン
        # ----------------------------------------------------
        if self.selected_branch == '京橋支店':
            url = 'https://www.mizuhobank.co.jp/tenpoinfo/tenpo_reservation/reservation.html?id=BA338922&_gl=1*k5k7g4*_ga*MTY5MzY1OTY1My4xNzU5ODE4NTkw*_ga_3D4K3DCJNB*czE3NjA0OTUxNDYkbzIkZzEkdDE3NjA0OTUzMzUkajYwJGwwJGgw'
        
        elif self.selected_branch == '八重洲口支店':
            url = 'https://www.mizuhobank.co.jp/tenpoinfo/tenpo_reservation/reservation.html?id=BA338924&_gl=1*1yjvpu4*_ga*MTY5MzY1OTY1My4xNzU5ODE4NTkw*_ga_3D4K3DCJNB*czE3NjA0OTUxNDYkbzIkZzEkdDE3NjA0OTU1MjkkajUxJGwwJGgw'
        
        elif self.selected_branch == '東京中央支店':
            url = 'https://www.mizuhobank.co.jp/tenpoinfo/tenpo_reservation/reservation.html?id=BA339731&_gl=1*1eoo2t1*_ga*MTY5MzY1OTY1My4xNzU5ODE4NTkw*_ga_3D4K3DCJNB*czE3NjA0OTUxNDYkbzIkZzEkdDE3NjA0OTU0MzgkajUyJGwwJGgw'
            
        self.proc.web_open(url)
        self.driver = self.proc.driver

        # --- ステップ 1: どちらかを選択してください。 ---
        self.click_button_by_text(self.driver, "個人のお客さま")

        # --- ステップ 2: ご来店目的を選択してください。 ---
        self.click_button_by_text(self.driver, "各種手続き")

        # --- ステップ 3: 内容を選択してください。 ---
        self.click_button_by_text(self.driver, "相続手続")

        # --- ステップ 4: 日時・お客さま情報入力へ進む ---
        reservation_link_xpath = '//*[@id="answer-20-3"]/div/div/a'

        reservation_link = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, reservation_link_xpath))
        )
        self.driver.execute_script("arguments[0].click();", reservation_link)
        print("✅ リンク '日時・お客さま情報入力へ' をクリックしました。")

        sleep(1)

    def start_proc(self):
        # ----------------------------------------------------
        # 2. 日時選択後の情報入力
        # ----------------------------------------------------
        driver = self.driver
        # ユーザーが日付を選択し、画面遷移した後のウィンドウに切り替える
        driver.switch_to.window(driver.window_handles[-1])
        driver.implicitly_wait(10)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "reserveform"))
        )

        ## 1. 必須のチェックボックス（3項目）の操作
        driver.find_element(By.XPATH, "//*[@id='right-column']/div[1]/form/div[1]/div[2]/div[1]/label/span").click()
        
        # 2. ご相談内容・ご希望など
        if self.selected_procedure == "残高証明書の発行依頼":
            procedure_text = "残高証明書の発行依頼"
        else: 
            procedure_text = "取引明細の発行依頼"
            
        text_content = (
            f'相続の手続き　{procedure_text}　被相続人：{self.deceased_name}様　'
            f'生年月日：{self.deceased_dob[0]}年{self.deceased_dob[1]}月{self.deceased_dob[2]}日　'
            f'口座番号：{mojimoji.zen_to_han(self.bank_branch_code or "")}{mojimoji.zen_to_han(self.bank_account_number or "0")}'
        )
        driver.find_element(By.ID, 'bt_form_attr_res11').send_keys(text_content)

        # 各種証明書発行
        driver.find_element(By.XPATH, '//*[@id="right-column"]/div[1]/form/div[1]/div[6]/div[2]/label/span').click()

        # ご予約時刻を15分過ぎても... -> 確認しました
        driver.find_element(By.XPATH, '//*[@id="right-column"]/div[1]/form/div[1]/div[8]/div/label/span').click()

        # フォームの送信
        driver.find_element(By.NAME, 'submit').click()

        # ----------------------------------------------------
        # 3. お客さま情報入力
        # ----------------------------------------------------
        sleep(2)
        self.proc.web_operation(driver.current_url)
        
        driver.implicitly_wait(10)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "form1"))
        )

        # 法人名【漢字】
        driver.find_element(By.NAME, "cus_name").send_keys(self.firm_name_kanji)

        # 法人名【全角カナ】
        driver.find_element(By.NAME, "cus_kana").send_keys(self.firm_name_kana)

        # ご来店者のお名前【漢字】
        driver.find_element(By.NAME, "attr_org1").send_keys(f'{self.staff_name_kanji}（{self.data["case_number"]}）')

        # ご来店者のお名前【全角カナ】
        driver.find_element(By.NAME, "attr_org2").send_keys(self.data['staff_name_kana'])

        # 電話番号
        driver.find_element(By.NAME, "cus_tel").send_keys(self.staff_tel.replace('-', ''))

        # 連絡がつきやすい時間帯
        driver.find_element(By.XPATH, "//*[@id='right-column']/div[1]/form/div[1]/div[12]/div[1]/label/span").click()

        # メールアドレス
        driver.find_element(By.NAME, "cus_mail").send_keys(self.staff_mail)

        # 生年月日
        Select(driver.find_element(By.ID, "bt_form_cus_birthy")).select_by_value(self.firm_dob_year)
        Select(driver.find_element(By.ID, "bt_form_cus_birthm")).select_by_value(self.firm_dob_month)
        Select(driver.find_element(By.ID, "bt_form_cus_birthd")).select_by_value(self.firm_dob_day)

        # 郵便番号
        driver.find_element(By.NAME, 'cus_zip').send_keys(mojimoji.zen_to_han(self.firm_zip or "1030028"))
        driver.find_element(By.XPATH, '//*[@id="right-column"]/div[1]/form/div[1]/div[18]/input[2]').click()
        sleep(1) 

        # 市区町村・番地
        driver.find_element(By.NAME, 'cus_addr1').send_keys('7-20')

        # 建物名など
        driver.find_element(By.NAME, 'cus_addr2').send_keys(self.firm_addr2 or "ビル名")

        # 店番号
        driver.find_element(By.NAME, "attr_org4").send_keys(mojimoji.zen_to_han(self.bank_branch_code or "0"))

        # 口座番号
        driver.find_element(By.NAME, "attr_org6").send_keys(mojimoji.zen_to_han(self.bank_account_number or "0"))

        # ご予約時に選択いただいたメニュー... -> 確認しました
        driver.find_element(By.XPATH, '//*[@id="right-column"]/div[1]/form/div[1]/div[34]/div/label/span').click()

        # 個人情報の利用目的... -> 同意します
        driver.find_element(By.XPATH, '//*[@id="right-column"]/div[1]/form/div[1]/div[36]/div/label/span').click()

        # メールマガジン -> 配信を希望しない
        driver.find_element(By.XPATH, '//*[@id="right-column"]/div[1]/form/div[1]/div[38]/div[2]/label/span').click()

        # ----------------------------------------------------
        # 4. 最終確認
        # ----------------------------------------------------
        driver.find_element(By.NAME, "submit").click()
        
        sleep(5)
        self.proc.web_operation(driver.current_url)