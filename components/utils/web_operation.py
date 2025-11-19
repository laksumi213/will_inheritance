from selenium import webdriver
import os
from time import sleep
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


class Web:
    def __init__(self):
        # ChromeDriverManager().install()

        if os.name == 'nt':
            self.chrome_path = os.path.join(os.path.expanduser("~"), '.wdm/drivers/chromedriver/win64')
        else:
            self.chrome_path = os.path.join(os.environ['HOME'], '.cache/selenium/chromedriver/mac-x64')

        self.chrome_max_ver = max(
            name for name in os.listdir(self.chrome_path) if os.path.isdir(os.path.join(self.chrome_path, name)))
        print('chrome_path:', self.chrome_path)
        print('chrome_max_ver:', self.chrome_max_ver)
        self.driver = None

    def web_open(self, url):
        # if self.driver is None:
        try:
            print('driver.window_handles:', self.driver.window_handles)
        except Exception as e:
            print('web_open Exception:', e)
            options = webdriver.ChromeOptions()
            options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging']) # chromeは自動テスト ソフトウェアによって制御されています。を非表示
            options.add_argument("--remote-debugging-port=9222")
            if os.name == 'nt':
                options.add_argument(f"--user-data-dir={os.path.expanduser('~')}/chrome_user_data")
            else:
                options.add_argument(f"--user-data-dir={os.environ['HOME']}/chrome_user_data")
            # options.add_argument("--profile-directory=Profile 6")
            options.add_experimental_option('detach', True)
            self.driver = webdriver.Chrome(options=options)
            print('driver.window_handles:', self.driver.window_handles)

        options = webdriver.ChromeOptions()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        # options.add_argument('--blink-settings=imagesEnabled=false')    # 画像を非表示
        options.add_argument('--disable-background-networking')         # 拡張機能の更新、セーフブラウジングサービス、アップグレード検出、翻訳、UMAを含む様々なバックグラウンドネットワークサービスを無効
        options.add_argument('--disable-default-apps')                  # デフォルトアプリのインストールを無効
        options.add_argument('--disable-dev-shm-usage')                 # ディスクのメモリスペースを使う。DockerやGcloudのメモリ対策でよく使われる
        options.add_argument('--disable-extensions')                    # 拡張機能をすべて無効
        options.add_argument('--disable-popup-blocking')                # ポップアップブロックを無効
        options.add_argument('--ignore-certificate-errors')             # SSL認証(この接続ではプライバシーが保護されません)を無効
        options.add_argument('--no-default-browser-check')              # アドレスバー下に表示される「既定のブラウザとして設定」を無効
        options.add_argument('--propagate-iph-for-testing')             # Chromeに表示される青いヒント(？)を非表示
        options.add_argument('--start-maximized')                       # ウィンドウの初期サイズを最大化
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')

        if os.name == 'nt':
            service = ChromeService(executable_path=os.path.join(self.chrome_path, self.chrome_max_ver, 'chromedriver-win32', "chromedriver.exe"))
        else:
            service = ChromeService(executable_path=os.path.join(self.chrome_path, self.chrome_max_ver, "chromedriver"))
        self.driver = webdriver.Chrome(service=service, options=options)

        # # 新規タブを作成してページを開く
        # self.driver.execute_script(f"window.open('{url}');")

        # 新規タブを作成
        self.driver.execute_script("window.open()")

        # 新しいタブに切り替える
        sleep(1)
        self.driver.switch_to.window(self.driver.window_handles[-1])

        self.driver.get(url)

        Web.driver = self.driver

    def web_operation(self, url):
        try:
            print('driver.window_handles:', self.driver.window_handles)
        except Exception as e:
            print('web_open Exception:', e)
            options = webdriver.ChromeOptions()
            options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging']) # chromeは自動テスト ソフトウェアによって制御されています。を非表示
            options.add_argument("--remote-debugging-port=9222")
            if os.name == 'nt':
                options.add_argument(f"--user-data-dir={os.path.expanduser('~')}/chrome_user_data")
            else:
                options.add_argument(f"--user-data-dir={os.environ['HOME']}/chrome_user_data")
            # options.add_argument("--profile-directory=Profile 6")
            options.add_experimental_option('detach', True)
            self.driver = webdriver.Chrome(options=options)
            print('driver.window_handles:', self.driver.window_handles)

        for driver in self.driver.window_handles:
            print('driver:', driver)
            self.driver.switch_to.window(driver)
            print('self.driver.title:', self.driver.title)
            if self.driver.current_url == url:
                print('url:', url)
                # Web.driver = self.driver
                # a = Web.driver.find_element(By.NAME, 'firstNmKn')
                # a.send_keys('22')


                # # CSSセレクタを使って、type="checkbox"のすべての<input>要素を取得
                # checkboxes = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
                #
                # # 取得したチェックボックスをループで処理
                # for checkbox in checkboxes:
                #     print(f"Name: {checkbox.get_attribute('name')}")
                #     print(f"Value: {checkbox.get_attribute('value')}")
                #     print(f"Is Selected: {checkbox.is_selected()}")
                #     print("-" * 20)

                # self.driver.find_element(By.XPATH, '//*[@id="checkBtn"]').click()
                # self.driver.minimize_window()
                # self.driver.maximize_window()
                # element = self.driver.find_element(By.XPATH, "/html/body/main/div[3]/div/div[3]/figure")
                # actions = ActionChains(self.driver)
                # actions.move_to_element(element)
                # actions.perform()
                # sleep(1)
                # element.click()
                break


if __name__ == '__main__':
    proc = Web()
    # proc.web_open("https://qiita.com/yagrush/items/ff069b2741d0f09a6d7f")
    # proc.web_open('https://www.google.com/')
    url = 'https://www.jicc.co.jp/kaiji/31#%E6%B3%95%E5%AE%9A%E7%9B%B8%E7%B6%9A%E4%BA%BA%E7%AD%89%E3%81%8B%E3%82%89%E5%A7%94%E4%BB%BB%E3%82%92%E5%8F%97%E3%81%91%E3%81%9F%20%E5%BC%81%E8%AD%B7%E5%A3%AB%E3%83%BB%E5%8F%B8%E6%B3%95%E6%9B%B8%E5%A3%AB%E3%81%AE%E6%96%B9%E3%81%AB%E3%82%88%E3%82%8B%E6%89%8B%E7%B6%9A%E3%81%8D'
    proc.web_open(url)
    proc.web_operation(url)
    # proc.web_operation('二親等以内の血族 法定相続人等による開示 | 開示を申し込む | 開示サービス | 日本信用情報機構（JICC）指定信用情報機関')
