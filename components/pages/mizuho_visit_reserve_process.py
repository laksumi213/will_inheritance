# /components/automation/mizuho_visit_reserve_process.py

import threading
from time import sleep
from datetime import date
from flet import Page, SnackBar, Text, Colors
from components.utils.web_operation import Web
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import mojimoji 
from tkinter import messagebox
from services.deceased_service import get_financial_asset_automation_data

# ----------------------------------------------------------------------------------
# メインプロセス関数
# ----------------------------------------------------------------------------------

def start_mizuho_reservation_process(page: Page, case_id: int):
    """
    みずほ銀行の来店予約Web自動化処理を別スレッドで開始する。
    """
    
    # データベースから必要なデータを取得
    target_bank_code = "0001"
    data = get_financial_asset_automation_data(case_id, target_bank_code)
    
    if not data:
        page.open(SnackBar(
            content=Text(f"エラー: データベースからみずほ銀行（{target_bank_code}）の予約に必要なデータが見つかりませんでした。", color=Colors.WHITE),
            bgcolor=Colors.RED_700
        ))
        page.update()
        return

    # Web操作は時間がかかるため、別スレッドで実行
    def run_automation():
        try:
            MizuhoReservation(page, data).reservation()
            page.open(SnackBar(
                content=Text("✅ みずほ銀行来店予約のWeb操作が完了しました。", color=Colors.WHITE),
                bgcolor=Colors.GREEN_700
            ))
        except Exception as e:
            page.open(SnackBar(
                content=Text(f"Web操作中にエラーが発生しました: {e}", color=Colors.WHITE),
                bgcolor=Colors.RED_700
            ))
        finally:
            page.update()

    threading.Thread(target=run_automation).start()

# ----------------------------------------------------------------------------------
# Web自動化クラス
# ----------------------------------------------------------------------------------

class MizuhoReservation:
    def __init__(self, page: Page, data: dict):
        self.page = page
        self.data = data
        self.proc = Web() # Web操作ヘルパーのインスタンス化
        
        # データベースから取得したデータを属性に展開
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
        # 京橋支店 ※この支店は法人ではなく個人で予約
        # url = 'https://www.mizuhobank.co.jp/tenpoinfo/tenpo_reservation/reservation.html?id=BA338922&_gl=1*k5k7g4*_ga*MTY5MzY1OTY1My4xNzU5ODE4NTkw*_ga_3D4K3DCJNB*czE3NjA0OTUxNDYkbzIkZzEkdDE3NjA0OTUzMzUkajYwJGwwJGgw'
        
        # 八重洲口支店
        # url = 'https://www.mizuhobank.co.jp/tenpoinfo/tenpo_reservation/reservation.html?id=BA338924&_gl=1*1yjvpu4*_ga*MTY5MzY1OTY1My4xNzU5ODE4NTkw*_ga_3D4K3DCJNB*czE3NjA0OTUxNDYkbzIkZzEkdDE3NjA0OTU1MjkkajUxJGwwJGgw'
        
        # 東京中央支店 ※この支店は法人ではなく個人で予約
        url = 'https://www.mizuhobank.co.jp/tenpoinfo/tenpo_reservation/reservation.html?id=BA339731&_gl=1*1eoo2t1*_ga*MTY5MzY1OTY1My4xNzU5ODE4NTkw*_ga_3D4K3DCJNB*czE3NjA0OTUxNDYkbzIkZzEkdDE3NjA0OTU0MzgkajUyJGwwJGgw'
        
        self.proc.web_open(url)
        driver = self.proc.driver

        # --- ステップ 1: どちらかを選択してください。 ---
        self.click_button_by_text(driver, "個人のお客さま")

        # --- ステップ 2: ご来店目的を選択してください。 ---
        self.click_button_by_text(driver, "各種手続き")

        # --- ステップ 3: 内容を選択してください。 ---
        self.click_button_by_text(driver, "相続手続")

        # --- ステップ 4: 日時・お客さま情報入力へ進む ---
        reservation_link_xpath = '//*[@id="answer-20-3"]/div/div/a'

        reservation_link = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, reservation_link_xpath))
        )
        driver.execute_script("arguments[0].click();", reservation_link)
        print("✅ リンク '日時・お客さま情報入力へ' をクリックしました。")

        sleep(1)
        messagebox.showinfo("待機中", "「日付選択後」にOKボタンをクリックしてください。")

        # ユーザーが日付を選択し、画面遷移した後のウィンドウに切り替える
        driver.switch_to.window(driver.window_handles[-1])
        driver.implicitly_wait(10)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "reserveform"))
        )

        ## 1. 必須のチェックボックス（3項目）の操作
        driver.find_element(By.XPATH,
                                      "//*[@id='right-column']/div[1]/form/div[1]/div[2]/div[1]/label/span").click()
        
        # 残りの2項目（法人・独立予約メニュー）は今回は省略（個人客としての流れを優先）
        
        # 2. ご相談内容・ご希望など (bt_form_attr_res11)
        # 被相続人情報と口座番号をDBから取得して挿入
        text_content = (
            # f'相続の手続き　残高証明書の発行依頼　被相続人：{self.deceased_name}様　'
            f'相続の手続き　取引明細の発行依頼　被相続人：{self.deceased_name}様　'
            f'生年月日：{self.deceased_dob[0]}年{self.deceased_dob[1]}月{self.deceased_dob[2]}日　'
            f'口座番号：{mojimoji.zen_to_han(self.bank_branch_code or "")}{mojimoji.zen_to_han(self.bank_account_number or "0")}'
        )
        driver.find_element(By.ID, 'bt_form_attr_res11').send_keys(text_content)

        # 各種証明書発行
        driver.find_element(By.XPATH,
                                      '//*[@id="right-column"]/div[1]/form/div[1]/div[6]/div[2]/label/span').click()

        # ご予約時刻を15分過ぎても... -> 確認しました
        driver.find_element(By.XPATH, '//*[@id="right-column"]/div[1]/form/div[1]/div[8]/div/label/span').click()

        # フォームの送信
        driver.find_element(By.NAME, 'submit').click()

        # ----------------------------------------------------
        # 3. お客さま情報入力
        # ----------------------------------------------------
        sleep(2)
        self.proc.web_operation(driver.current_url) # 画面を手動操作に切り替え
        
        driver.implicitly_wait(10)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "form1"))
        )

        # 法人名【漢字】 (DB固定値)
        driver.find_element(By.NAME, "cus_name").send_keys(self.firm_name_kanji)

        # 法人名【全角カナ】 (DB固定値)
        driver.find_element(By.NAME, "cus_kana").send_keys(self.firm_name_kana)

        # ご来店者のお名前【漢字】 (DB情報 + 案件担当者コード)
        driver.find_element(By.NAME, "attr_org1").send_keys(f'{self.staff_name_kanji}（{self.data['case_number']}）')

        # ご来店者のお名前【全角カナ】 (DB固定値)
        driver.find_element(By.NAME, "attr_org2").send_keys(self.data['staff_name_kana']) # カタカナ変換が必要だが、ここでは仮に漢字の読み仮名を使用

        # 電話番号 (契約者電話番号)
        driver.find_element(By.NAME, "cus_tel").send_keys(self.staff_tel.replace('-', ''))

        # 連絡がつきやすい時間帯 (いつでも)
        driver.find_element(By.XPATH, "//*[@id='right-column']/div[1]/form/div[1]/div[12]/div[1]/label/span").click()

        # メールアドレス (契約者メールアドレス)
        driver.find_element(By.NAME, "cus_mail").send_keys(self.staff_mail)

        # 生年月日 (法人設立年月日または今日の日付 - 法人情報から取得)
        Select(driver.find_element(By.ID, "bt_form_cus_birthy")).select_by_value(self.firm_dob_year)
        Select(driver.find_element(By.ID, "bt_form_cus_birthm")).select_by_value(self.firm_dob_month)
        Select(driver.find_element(By.ID, "bt_form_cus_birthd")).select_by_value(self.firm_dob_day)

        # 郵便番号 (法人郵便番号)
        driver.find_element(By.NAME, 'cus_zip').send_keys(mojimoji.zen_to_han(self.firm_zip or "1030028"))
        driver.find_element(By.XPATH, '//*[@id="right-column"]/div[1]/form/div[1]/div[18]/input[2]').click()
        sleep(1) # 住所自動入力の待機

        # 市区町村・番地 (自動入力されるが、念のため)
        driver.find_element(By.NAME, 'cus_addr1').send_keys('7-20')

        # 建物名など (法人建物名)
        driver.find_element(By.NAME, 'cus_addr2').send_keys(self.firm_addr2 or "ビル名")

        # 店番号 (DBから取得した支店コード)
        driver.find_element(By.NAME, "attr_org4").send_keys(mojimoji.zen_to_han(self.bank_branch_code or "0"))

        # 口座番号 (DBから取得した口座番号)
        driver.find_element(By.NAME, "attr_org6").send_keys(mojimoji.zen_to_han(self.bank_account_number or "0"))

        # ご予約時に選択いただいたメニュー... -> 確認しました
        driver.find_element(By.XPATH, '//*[@id="right-column"]/div[1]/form/div[1]/div[34]/div/label/span').click()

        # 個人情報の利用目的... -> 同意します
        driver.find_element(By.XPATH,
                            '//*[@id="right-column"]/div[1]/form/div[1]/div[36]/div/label/span').click()

        # メールマガジン -> 配信を希望しない
        driver.find_element(By.XPATH,
                                      '//*[@id="right-column"]/div[1]/form/div[1]/div[38]/div[2]/label/span').click()

        # ----------------------------------------------------
        # 4. 最終確認
        # ----------------------------------------------------
        # 「次へ進む」ボタンを特定 (type="submit", value="次へ進む")
        driver.find_element(By.NAME, "submit").click()
        
        # 💡 ユーザーに最終操作を促す
        self.page.show_snack_bar(SnackBar(
            content=Text("✅ 最終確認画面に遷移しました。Webブラウザで「予約内容を確認」をクリックして予約を完了してください。", color=Colors.WHITE),
            bgcolor=Colors.GREEN_700
        ))
        self.page.update()

        sleep(5)
        self.proc.web_operation(driver.current_url) # 最終画面をユーザーに渡して終了