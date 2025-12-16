# src/services/automation/registry_automation_service.py
import re
import time
import os
from typing import Tuple, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from src.utils.web_operation import Web

# 環境変数から取得、なければデフォルト値（セキュリティのため環境変数推奨）
USER_ID = os.getenv("TOUKI_USER_ID", "ABLV5270")
PASSWORD = os.getenv("TOUKI_PASSWORD", "gychester55")
LOGIN_URL = 'https://www.touki.or.jp/TeikyoUketsuke/'

class RegistryAutomationService:
    """
    登記情報提供サービスへの自動操作を行うサービスクラス
    """

    def __init__(self):
        self.proc = Web()  # シングルトンのWebドライバ管理クラス

    def _process_address_efficiently(self, address_string: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        住所文字列を都道府県、市区町村・町域、番地・号に分割し、
        全角変換などの正規化を行う。
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

        # 2. 町域と番地の分割
        buf_match = re.match(r'(.*丁目)(.*)', buf)
        if buf_match:
            town_name_raw = buf_match.group(1)
            block_raw = buf_match.group(2)
        else:
            # 簡易的な分割（丁目がない場合など、実際にはより高度な解析が必要な場合あり）
            # ここでは数値が出現する直前で分割する簡易ロジックを追加
            split_match = re.search(r'\d', buf)
            if split_match:
                idx = split_match.start()
                town_name_raw = buf[:idx]
                block_raw = buf[idx:]
            else:
                town_name_raw = buf
                block_raw = ''

        # 3. 全角変換
        def to_zenkaku(text):
            return text.translate(
                str.maketrans(
                    '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~',
                    '０１２３４５６７８９ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ！”＃＄％＆’（）＊＋，－．／：；＜＝＞？＠［￥］＾＿｀｛｜｝～'
                )
            )

        town_name = to_zenkaku(town_name_raw)
        block = to_zenkaku(block_raw)

        return prefectures, town_name, block

    def login(self) -> bool:
        """ログイン処理"""
        try:
            self.proc.web_open(LOGIN_URL)
            driver = self.proc.driver

            # 要素出現待機
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "userId"))
            )

            # 既にログイン後の画面かチェック（簡易）
            if "TeikyoUketsuke" in driver.current_url and "Menu" in driver.title:
                return True

            # ID・PASS入力
            driver.find_element(By.ID, 'userId').send_keys(USER_ID)
            driver.find_element(By.ID, 'password').send_keys(PASSWORD)
            
            LOGIN_BUTTON_XPATH = "//button[contains(@class, 'CForwardLong')]/span[text()='ログイン']"
            driver.find_element(By.XPATH, LOGIN_BUTTON_XPATH).click()

            # 強制ログイン（二重ログイン時など）
            try:
                FORCE_LOGIN_XPATH = "//span[contains(text(), '強制ログイン')]"
                force_login_button = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, FORCE_LOGIN_XPATH))
                )
                force_login_button.click()
            except:
                pass

            return True
        except Exception as e:
            print(f"Login failed: {e}")
            return False

    def request_real_estate(self, address: str, target_type: str = '土地') -> bool:
        """
        不動産登記情報の請求操作
        :param address: 住所文字列
        :param target_type: '土地' または '建物'
        """
        driver = self.proc.driver
        try:
            # 1. 不動産請求メニューへ遷移
            fudosan_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "不動産請求"))
            )
            fudosan_link.click()

            # 2. 住所処理
            pref, town, blk = self._process_address_efficiently(address)
            if not pref:
                print("住所の解析に失敗しました。")
                return False

            # 3. 種別選択
            if target_type == '建物':
                BUILDING_RADIO_ID = "fuShozaiTypeTATEMONO"
                building_radio = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, BUILDING_RADIO_ID))
                )
                building_radio.click()
            
            # 4. 住所入力
            # 都道府県
            Select(driver.find_element(By.NAME, "todofukenShozai")).select_by_visible_text(pref)
            
            # 直接入力モードへ切り替え
            driver.find_element(By.NAME, "fuShozaiChokusetuNyuryoku").click()
            time.sleep(0.5)

            # 市区町村・地番入力
            driver.find_element(By.NAME, 'chibanKuiki').send_keys(town)
            driver.find_element(By.NAME, 'chibanKaoku').send_keys(blk)

            # 共同担保目録: 有り
            try:
                KYODO_TANPO_YES_ID = "fuKyodoTanpoYES"
                kyodo_tanpo_yes = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, KYODO_TANPO_YES_ID))
                )
                kyodo_tanpo_yes.click()
            except:
                print("共同担保目録の選択スキップ")

            # 5. 確定ボタン（検索実行）
            # 実際の請求（課金）までは行わず、確定ボタン手前まで、または一覧表示まで進めるのが一般的
            # ここでは元のコードに従い「確定」をクリックするロジックを入れるが、
            # 実際には確認画面が出る場合があるため注意。
            
            CONFIRM_BUTTON_XPATH = "//button[contains(@class, 'CForward')]/span[contains(text(), '確定')]"
            confirm_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, CONFIRM_BUTTON_XPATH))
            )
            confirm_button.click()
            
            return True

        except Exception as e:
            print(f"Request failed: {e}")
            return False

    def request_corporate(self, name: str, pref: str = "東京都") -> bool:
        """
        商業・法人登記情報の請求操作 (簡易実装)
        """
        driver = self.proc.driver
        try:
            # 1. 商業・法人請求メニューへ遷移
            corp_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "商業・法人請求"))
            )
            corp_link.click()

            # 2. 検索条件入力 (会社名検索などを想定)
            # ※実際のDOM構造に合わせて調整が必要
            # ここではプレースホルダー的な実装とします
            
            # 都道府県選択
            try:
                Select(driver.find_element(By.NAME, "todofukenShozai")).select_by_visible_text(pref)
            except:
                pass

            # 名称入力 (例: name_kana ではなく name を直接入力する欄があると仮定)
            # driver.find_element(By.NAME, 'kaishaName').send_keys(name)
            
            # 検索ボタン押下...
            
            print(f"商業登記検索: {name} (実装はDOM解析後に調整が必要です)")
            return True

        except Exception as e:
            print(f"Corporate request failed: {e}")
            return False

# シングルトンインスタンス
registry_service = RegistryAutomationService()