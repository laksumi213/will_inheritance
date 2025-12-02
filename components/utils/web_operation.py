# components/utils/web_operation.py

import os
import threading
from time import sleep
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException

class Web:
    """
    Selenium WebDriverを管理するシングルトンクラス。
    アプリ全体で1つのブラウザインスタンスを共有します。
    """
    _instance = None
    _lock = threading.Lock()
    _driver = None

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Web, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        # OSごとのパス設定（参考用に保持）
        if os.name == 'nt':
            self.chrome_path = os.path.join(os.path.expanduser("~"), '.wdm/drivers/chromedriver/win64')
        else:
            self.chrome_path = os.path.join(os.environ['HOME'], '.cache/selenium/chromedriver/mac-x64')
        
        self._initialized = True

    @property
    def driver(self):
        """現在のドライバインスタンスを返す。なければ作成する"""
        if Web._driver is None:
            self.initialize_driver()
        else:
            # ブラウザが手動で閉じられたかチェック
            try:
                # titleにアクセスして生存確認
                _ = Web._driver.title
            except WebDriverException:
                print("⚠️ ブラウザが閉じられています。再起動します。")
                Web._driver = None
                self.initialize_driver()
        
        return Web._driver

    def initialize_driver(self):
        """ドライバを初期化・起動する（スレッドセーフ）"""
        with Web._lock:
            if Web._driver is not None:
                # 既に起動している場合は生存確認だけしてリターン
                try:
                    _ = Web._driver.title
                    return
                except WebDriverException:
                    Web._driver = None

            print("🚀 Initializing WebDriver (Singleton)...")
            try:
                # Chrome Options
                options = webdriver.ChromeOptions()
                # 「自動テストソフトウェアによって...」バーを非表示
                options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging'])
                options.add_argument("--remote-debugging-port=9222")
                
                # ユーザーデータディレクトリの設定（プロファイルの維持）
                if os.name == 'nt':
                    user_data_dir = f"{os.path.expanduser('~')}/chrome_user_data"
                else:
                    user_data_dir = f"{os.environ['HOME']}/chrome_user_data"
                options.add_argument(f"--user-data-dir={user_data_dir}")
                
                options.add_experimental_option('detach', True) # スクリプト終了後もブラウザを残す
                
                # パフォーマンス向上のためのオプション
                options.add_argument('--disable-background-networking')
                options.add_argument('--disable-default-apps')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-popup-blocking')
                options.add_argument('--ignore-certificate-errors')
                options.add_argument('--no-default-browser-check')
                options.add_argument('--start-maximized')
                options.add_argument('--disable-logging')
                options.add_argument('--log-level=3')

                # ドライバの起動
                service = ChromeService(ChromeDriverManager().install())
                Web._driver = webdriver.Chrome(service=service, options=options)
                
                print("✅ WebDriver initialized successfully.")

            except Exception as e:
                print(f"❌ WebDriver initialization failed: {e}")
                Web._driver = None
                raise e

    def web_open(self, url):
        """指定したURLを開く。既に開いていれば新しいタブで開く"""
        drv = self.driver # プロパティ経由で取得（生存確認込み）
        
        try:
            # ハンドル数を確認
            handles = drv.window_handles
            if not handles:
                # ハンドルがない場合はget
                drv.get(url)
            else:
                # 新しいタブを作成して切り替え
                drv.execute_script("window.open();")
                drv.switch_to.window(drv.window_handles[-1])
                drv.get(url)
                
        except Exception as e:
            print(f"web_open error: {e}")

    def web_operation(self, url):
        """指定したURLのタブを探して切り替える（デバッグ・確認用）"""
        drv = self.driver
        try:
            current = drv.current_window_handle
            for handle in drv.window_handles:
                drv.switch_to.window(handle)
                if url in drv.current_url: # 部分一致に変更
                    print(f"Switched to tab: {drv.current_url}")
                    return
            
            # 見つからなかったら元のタブに戻す
            drv.switch_to.window(current)
            print(f"Tab not found containing: {url}")
            
        except Exception as e:
            print(f"web_operation error: {e}")

    def quit_driver(self):
        """ブラウザを閉じてドライバを破棄する（アプリ終了時など）"""
        with Web._lock:
            if Web._driver:
                try:
                    Web._driver.quit()
                except:
                    pass
                finally:
                    Web._driver = None
                    print("🛑 WebDriver quit.")

if __name__ == '__main__':
    web = Web()
    web.initialize_driver()