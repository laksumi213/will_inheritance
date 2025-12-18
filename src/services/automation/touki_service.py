# src/services/automation/touki_service.py
import re
import time
from typing import Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

from src.utils.web_operation import Web

# 定数定義
USER_ID = 'ABLV5270'
PASSWORD = 'gychester55'
LOGIN_URL = 'https://www.touki.or.jp/TeikyoUketsuke/'

class ToukiService:
    """
    登記情報提供サービスの自動操作を行うサービスクラス
    """
    def __init__(self) -> None:
        self.proc = Web()

    def _to_zenkaku(self, text: str) -> str:
        """半角文字を全角文字に変換する"""
        if not text:
            return ""
        return text.translate(str.maketrans(
            '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ ',
            '０１２３４５６７８９ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ！”＃＄％＆’（）＊＋，－．／：；＜＝＞？＠［￥］＾＿｀｛｜｝～　'
        ))

    def _process_address_efficiently(self, address_string: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """住所文字列を都道府県、市区町村・町域、番地・号に分割・正規化する"""
        if not address_string:
            return None, None, None

        # 1. 都道府県の抽出
        pref_pattern = r'(東京都|北海道|(?:京都|大阪)府|.{2,3}県)'
        match = re.match(pref_pattern + r'(.+)', address_string)
        if not match:
            return None, None, None

        prefectures = match.group(1)
        buf = match.group(2).strip()

        # 2. 町域と番地の分割 (丁目または数値で判定)
        buf_match = re.match(r'(.*丁目)(.*)', buf)
        if buf_match:
            town_name_raw = buf_match.group(1)
            block_raw = buf_match.group(2)
        else:
            split_match = re.search(r'\d', buf)
            if split_match:
                idx = split_match.start()
                town_name_raw = buf[:idx]
                block_raw = buf[idx:]
            else:
                town_name_raw = buf
                block_raw = ''

        town_name = self._to_zenkaku(town_name_raw.strip())
        block = self._to_zenkaku(block_raw.strip())
        return prefectures, town_name, block

    def _extract_municipality(self, address_without_pref: str) -> str:
        """市区町村部分を抽出"""
        match = re.match(r'^(.+?[郡市区町村])', address_without_pref)
        if match:
            return match.group(1)
        return address_without_pref

    def _wait_and_click(self, by: By, value: str, timeout: int = 10) -> None:
        """要素が表示されるのを待ち、クリックする"""
        driver = self.proc.driver
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            element.click()
        except (TimeoutException, ElementClickInterceptedException):
            try:
                # JavaScriptで強制クリック
                element = driver.find_element(by, value)
                driver.execute_script("arguments[0].click();", element)
                time.sleep(0.5)
            except Exception as e:
                raise Exception(f"要素をクリックできませんでした ({value}): {e}")

    def _wait_and_send_keys(self, by: By, value: str, text: str, timeout: int = 10) -> None:
        """要素が表示されるのを待ち、テキストを入力する"""
        driver = self.proc.driver
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            element.clear()
            element.send_keys(text)
        except Exception as e:
            raise Exception(f"テキスト入力に失敗しました ({value}): {e}")

    def login(self) -> bool:
        """ログイン処理"""
        driver = self.proc.driver
        try:
            self.proc.web_open(LOGIN_URL)
            if "TeikyoUketsuke" in driver.current_url and "Menu" in driver.title:
                return True

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "userId")))
            self._wait_and_send_keys(By.ID, 'userId', USER_ID)
            self._wait_and_send_keys(By.ID, 'password', PASSWORD)
            
            login_btn_xpath = "//button[contains(@class, 'CForwardLong')]/span[text()='ログイン']"
            self._wait_and_click(By.XPATH, login_btn_xpath)

            # 多重ログイン確認
            try:
                force_login_xpath = "//span[contains(text(), '強制ログイン')]"
                force_btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, force_login_xpath)))
                force_btn.click()
            except:
                pass 

            # WebDriverWait(driver, 10).until(lambda d: "Menu" in d.title)
            return True
        except Exception as e:
            print(f"Touki Login Error: {e}")
            return False

    def request_real_estate(self, address: str, target_type: str = '土地') -> str:
        """不動産（土地・建物）の請求を行う"""
        driver = self.proc.driver
        if "TeikyoUketsuke" not in driver.current_url:
            if not self.login():
                raise Exception("ログインに失敗しました")

        try:
            # 1. メニュー遷移
            self._wait_and_click(By.PARTIAL_LINK_TEXT, "不動産請求")
            
            # 2. 住所解析
            pref, town, blk = self._process_address_efficiently(address)
            if not pref:
                raise ValueError(f"住所の解析に失敗しました: {address}")

            # 3. 入力画面表示待機
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "fuShozaiTypeTOCHI")))
            
            if target_type == '建物':
                self._wait_and_click(By.ID, "fuShozaiTypeTATEMONO")
            else:
                self._wait_and_click(By.ID, "fuShozaiTypeTOCHI")

            # 4. 住所入力
            pref_select = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.NAME, "todofukenShozai")))
            Select(pref_select).select_by_visible_text(pref)
            
            self._wait_and_click(By.NAME, "fuShozaiChokusetuNyuryoku")
            
            # 直接入力フィールドが表示されるのを待機
            WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.NAME, "chibanKuiki")))

            self._wait_and_send_keys(By.NAME, 'chibanKuiki', town)
            self._wait_and_send_keys(By.NAME, 'chibanKaoku', blk)

            # 5. 共同担保目録: 有
            try:
                self._wait_and_click(By.ID, "fuKyodoTanpoYES", timeout=2)
            except:
                pass

            # 6. 確定
            confirm_xpath = "//button[contains(@class, 'CForward')]/span[contains(text(), '確定')]"
            self._wait_and_click(By.XPATH, confirm_xpath)
            
            return f"「{address}」({target_type}) の検索を実行しました。"

        except Exception as e:
            raise Exception(f"自動操作中にエラーが発生しました: {e}")

    def request_commercial(self, name: str, address: str) -> str:
        """商業・法人請求を行う"""
        driver = self.proc.driver
        if "TeikyoUketsuke" not in driver.current_url:
            if not self.login():
                raise Exception("ログインに失敗しました")

        try:
            self._wait_and_click(By.PARTIAL_LINK_TEXT, "商業・法人")
            
            pref_pattern = r'(東京都|北海道|(?:京都|大阪)府|.{2,3}県)'
            match = re.match(pref_pattern + r'(.+)', address)
            if not match:
                raise ValueError(f"住所の解析に失敗しました: {address}")

            pref = match.group(1)
            municipality = self._extract_municipality(match.group(2).strip())
            municipality_zenkaku = self._to_zenkaku(municipality)

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "shTodofukenShozaiA1")))
            Select(driver.find_element(By.ID, "shTodofukenShozaiA1")).select_by_visible_text(pref)
            
            time.sleep(0.5)
            self._wait_and_click(By.ID, "shShozaiChokusetuNyuryokuA1")
            self._wait_and_send_keys(By.ID, "shChibanKuiki1", municipality_zenkaku)
            self._wait_and_send_keys(By.ID, "shShogoMeisyo", name)
            
            search_btn_xpath = "//button[contains(@onclick, 'shBtnForward')]"
            self._wait_and_click(By.XPATH, search_btn_xpath)

            return f"法人「{name}」の検索を実行しました。"

        except Exception as e:
            raise Exception(f"商業登記の自動操作中にエラーが発生しました: {e}")

touki_service = ToukiService()