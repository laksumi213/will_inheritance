# src/services/automation_service.py
import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from src.config import settings


class AutomationService:
    """
    Seleniumを使用したWebオートメーションの基盤クラス
    """

    def __init__(self, headless: bool = False):
        self.driver: Optional[webdriver.Chrome] = None
        self.headless = headless

    def start_driver(self):
        """Chromeドライバーを起動する"""
        if self.driver is not None:
            return

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")

        # 一般的な安定化オプション
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")

        # ユーザーエージェントの設定（必要に応じて）
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        try:
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("Chrome Driver started successfully.")
        except Exception as e:
            print(f"Failed to start Chrome Driver: {e}")
            raise e

    def stop_driver(self):
        """ドライバーを終了する"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            print("Chrome Driver stopped.")

    def navigate_to(self, url: str):
        """指定したURLに遷移する"""
        if not self.driver:
            self.start_driver()
        self.driver.get(url)
        time.sleep(1)  # 簡易的なウェイト

    def find_element(self, by: By, value: str, timeout: int = 10):
        """要素を検索する（待機機能付き）"""
        if not self.driver:
            raise RuntimeError("Driver is not started.")

        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except Exception as e:
            print(f"Element not found: {value} - {e}")
            return None

    def capture_screenshot(self, filepath: str):
        """スクリーンショットを保存する"""
        if self.driver:
            self.driver.save_screenshot(filepath)

    # --- 業務固有の自動化メソッド例 ---

    def auto_login_bank(self, bank_code: str, account_id: str, password: str) -> bool:
        """
        銀行サイトへの自動ログイン（サンプル実装）
        :param bank_code: 銀行コード（例: 0001）
        :return: 成功可否
        """
        # 実装例: みずほ銀行の場合
        if bank_code == "0001":
            target_url = (
                "https://www.mizuhobank.co.jp/retail/products/direct/index.html"  # ※ダミーURL
            )
            try:
                self.navigate_to(target_url)
                # ここに実際のログインロジックを記述
                # user_input = self.find_element(By.ID, "txbCustNo")
                # pass_input = self.find_element(By.ID, "txbPassword")
                # ...
                print(f"Login logic for bank {bank_code} executed.")
                return True
            except Exception as e:
                print(f"Bank login failed: {e}")
                return False

        print(f"Automation for bank code {bank_code} is not implemented.")
        return False


# シングルトンとして利用する場合
automation_service = AutomationService(headless=settings.SELENIUM_HEADLESS)
