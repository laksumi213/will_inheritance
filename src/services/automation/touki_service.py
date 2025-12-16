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
    def __init__(self):
        self.proc = Web() # シングルトンWebインスタンス

    def _to_zenkaku(self, text: str) -> str:
        """半角文字を全角文字に変換する"""
        if not text:
            return ""
        return text.translate(str.maketrans(
            '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ ',
            '０１２３４５６７８９ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ！”＃＄％＆’（）＊＋，－．／：；＜＝＞？＠［￥］＾＿｀｛｜｝～　'
        ))

    def _process_address_efficiently(self, address_string: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        住所文字列を都道府県、市区町村・町域、番地・号に分割・正規化する
        """
        if not address_string:
            return None, None, None

        # 1. 都道府県の抽出
        pref_pattern = r'(東京都|北海道|(?:京都|大阪)府|.{2,3}県)'
        match = re.match(pref_pattern + r'(.+)', address_string)

        if not match:
            return None, None, None

        prefectures = match.group(1)
        buf = match.group(2)

        # 2. 「丁目」を区切りとして分割 (不動産用)
        buf_match = re.match(r'(.*丁目)(.*)', buf)
        if buf_match:
            town_name_raw = buf_match.group(1)
            block_raw = buf_match.group(2)
        else:
            town_name_raw = buf
            block_raw = ''

        town_name = self._to_zenkaku(town_name_raw)
        block = self._to_zenkaku(block_raw)

        return prefectures, town_name, block

    def _extract_municipality(self, address_without_pref: str) -> str:
        """
        都道府県を除いた住所文字列から、市区町村部分（○○市、○○区、○○町、○○村）のみを抽出する
        例: "港区三田1-1" -> "港区"
        """
        # 郡、市、区、町、村 のいずれかで終わる最短の文字列を取得
        # 政令指定都市（横浜市中区など）への対応は簡易的に最初の「区」までとする場合が多いが、
        # ここでは一般的な「市区町村」の区切りで抽出する
        match = re.match(r'^(.+?[郡市区町村])', address_without_pref)
        if match:
            return match.group(1)
        return address_without_pref # マッチしない場合はそのまま返す

    def _wait_and_click(self, by, value, timeout=10):
        """
        要素が表示されるのを待ち、クリックする。
        通常のクリックが失敗した場合はJavaScriptでクリックを試みる。
        """
        driver = self.proc.driver
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            element.click()
        except (TimeoutException, ElementClickInterceptedException):
            # タイムアウトやクリック阻害時はJSで強制クリック
            try:
                element = driver.find_element(by, value)
                driver.execute_script("arguments[0].click();", element)
                time.sleep(0.5) # 画面遷移待ち
            except Exception as e:
                raise Exception(f"要素をクリックできませんでした ({value}): {e}")

    def _wait_and_send_keys(self, by, value, text, timeout=10):
        """
        要素が表示されるのを待ち、テキストを入力する。
        """
        driver = self.proc.driver
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            # 要素が見えていてもInteractableでない場合があるため、JSでスクロール
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
            
            # ログイン画面待機
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "userId"))
            )

            # 既にログイン後の画面かチェック（簡易）
            if "TeikyoUketsuke" in driver.current_url and "Menu" in driver.title:
                return True

            # IDとパスワードの入力
            self._wait_and_send_keys(By.ID, 'userId', USER_ID)
            self._wait_and_send_keys(By.ID, 'password', PASSWORD)
            
            login_btn_xpath = "//button[contains(@class, 'CForwardLong')]/span[text()='ログイン']"
            self._wait_and_click(By.XPATH, login_btn_xpath)

            # 強制ログイン（二重ログイン）チェック
            try:
                force_login_xpath = "/html/body/div/div[1]/div[4]/div[2]/form/button[2]/span"
                # 短めのタイムアウトで確認
                force_btn = WebDriverWait(driver, 3).until(
                    EC.visibility_of_element_located((By.XPATH, force_login_xpath))
                )
                force_btn.click()
                print("強制ログインを実行しました。")
            except Exception:
                pass 

            return True
        except Exception as e:
            print(f"Touki Login Error: {e}")
            return False

    def request_real_estate(self, address: str, target_type: str = '土地') -> str:
        """
        不動産（土地・建物）の請求を行う
        """
        driver = self.proc.driver
        
        # 1. ログイン確認
        if "TeikyoUketsuke" not in driver.current_url:
            if not self.login():
                raise Exception("ログインに失敗しました")

        try:
            # 不動産請求タブへ (部分一致で検索)
            self._wait_and_click(By.PARTIAL_LINK_TEXT, "不動産請求")
        except Exception as e:
            raise Exception(f"不動産請求メニューへの遷移に失敗: {e}")

        # 2. 住所処理
        pref, town, blk = self._process_address_efficiently(address)
        if not pref:
            raise ValueError(f"住所の解析に失敗しました: {address}")

        try:
            # 3. 種別選択
            if target_type == '建物':
                self._wait_and_click(By.ID, "fuShozaiTypeTATEMONO")
            else:
                self._wait_and_click(By.ID, "fuShozaiTypeTOCHI")

            # 4. 住所入力
            # 都道府県選択
            pref_select = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.NAME, "todofukenShozai"))
            )
            Select(pref_select).select_by_visible_text(pref)
            
            # 直接入力モードへ
            self._wait_and_click(By.NAME, "fuShozaiChokusetuNyuryoku")
            
            # 住所入力
            self._wait_and_send_keys(By.NAME, 'chibanKuiki', town)
            self._wait_and_send_keys(By.NAME, 'chibanKaoku', blk)

            # 5. 共同担保目録: 有
            try:
                self._wait_and_click(By.ID, "fuKyodoTanpoYES", timeout=2)
            except:
                pass # 必須ではないため無視

            # 6. 確定ボタン
            confirm_xpath = "//button[contains(@class, 'CForward')]/span[contains(text(), '確定')]"
            self._wait_and_click(By.XPATH, confirm_xpath)
            
            return f"「{address}」({target_type}) の検索を実行しました。検索結果を確認してください。"

        except Exception as e:
            print(f"Automation Error: {e}")
            raise Exception(f"自動操作中にエラーが発生しました: {e}")

    def request_commercial(self, name: str, address: str) -> str:
        """
        商業・法人請求を行う
        """
        driver = self.proc.driver

        # 1. ログイン確認
        if "TeikyoUketsuke" not in driver.current_url:
            if not self.login():
                raise Exception("ログインに失敗しました")

        try:
            # 2. 商業・法人請求タブへ遷移
            self._wait_and_click(By.PARTIAL_LINK_TEXT, "商業・法人")
            
            # 画面遷移待機: 都道府県選択プルダウンが表示されるまで
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "shTodofukenShozaiA1"))
            )
            
        except Exception as e:
            raise Exception(f"商業・法人請求メニューへの遷移に失敗しました: {e}")

        # 3. 住所処理 (都道府県と市区町村の抽出)
        # _process_address_efficiently を使って都道府県を取り出し、残りを取得
        pref_pattern = r'(東京都|北海道|(?:京都|大阪)府|.{2,3}県)'
        match = re.match(pref_pattern + r'(.+)', address)
        
        if not match:
            raise ValueError(f"住所の解析に失敗しました: {address}")

        pref = match.group(1)
        remainder = match.group(2)

        # 市区町村の抽出 (例: 港区三田... -> 港区)
        municipality = self._extract_municipality(remainder)
        # 全角変換
        municipality_zenkaku = self._to_zenkaku(municipality)

        try:
            # 4. 都道府県の選択 (ID指定)
            pref_select_elem = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "shTodofukenShozaiA1"))
            )
            Select(pref_select_elem).select_by_visible_text(pref)

            # 5. 直接入力の選択 (ID指定)
            # クリック前に少し待機
            time.sleep(0.5)
            self._wait_and_click(By.ID, "shShozaiChokusetuNyuryokuA1")

            # 6. 所在（市区町村）の入力 (ID指定)
            # 全角で入力
            self._wait_and_send_keys(By.ID, "shChibanKuiki1", municipality_zenkaku)

            # 7. 商号・名称の入力 (ID指定)
            self._wait_and_send_keys(By.ID, "shShogoMeisyo", name)

            # 8. 検索実行
            # onclick="shBtnForward()" を持つボタンをクリック
            search_btn_xpath = "//button[contains(@onclick, 'shBtnForward')]"
            self._wait_and_click(By.XPATH, search_btn_xpath)

            return f"法人「{name}」({pref}{municipality_zenkaku}) の検索を実行しました。検索結果一覧を確認し、対象を選択してください。"

        except Exception as e:
            print(f"Commercial Automation Error: {e}")
            raise Exception(f"商業・法人請求の自動操作中にエラーが発生しました: {e}")

# シングルトン
touki_service = ToukiService()