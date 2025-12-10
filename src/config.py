# src/config.py
import os
from dotenv import load_dotenv
from pathlib import Path

from flet import Colors, Theme, ThemeMode, VisualDensity  # テーマ関連のインポートを追加

# --- Fletテーマ設定 (直前の依頼で定義) ---
APP_THEME = Theme(
    color_scheme_seed=Colors.TEAL,
    visual_density=VisualDensity.COMFORTABLE,
)
DEFAULT_THEME_MODE = ThemeMode.DARK  # 常にダークモード

load_dotenv()

# --- アプリケーション設定 (既存のクラスを維持) ---
class Config:
    """アプリケーション全体の設定定数（パス、外部サービスなど）"""

    # パス設定
    BASE_DIR = Path(__file__).parent.parent
    ASSETS_DIR = BASE_DIR / "assets"
    DB_PATH = BASE_DIR / "database.sqlite"

    # アプリ設定
    APP_TITLE = "遺産整理・相続業務システム"
    VERSION = "1.0.0"

    # テーマカラー（既存の定義も維持、ただしFletのテーマ設定にはAPP_THEMEが使われる）
    COLOR_PRIMARY = Colors.BLUE_500
    COLOR_SECONDARY = Colors.TEAL_500
    COLOR_ERROR = Colors.RED_600
    COLOR_BACKGROUND = Colors.WHITE
    COLOR_SURFACE_VARIANT = "surfaceVariant"

    # 外部サービス設定
    # VERTEX_AI_PROJECT_ID = os.getenv("VERTEX_AI_PROJECT_ID", "")
    SELENIUM_HEADLESS = False

    # Google Cloud Project ID
    GOOGLE_PROJECT_ID: str = os.getenv("GOOGLE_PROJECT_ID", "your-project-id")
    
    # Vertex AI Region
    GOOGLE_LOCATION: str = os.getenv("GOOGLE_LOCATION", "us-central1")
    
    # サービスアカウントキーのパス (優先順位: 環境変数 -> ローカルのjsonファイル)
    # 本番運用時は環境変数を推奨。開発時は直下のjsonを参照可能にする。
    GOOGLE_CREDENTIALS_PATH: str = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS", 
        os.path.join(os.getcwd(), "service_account.json")
    )

    # Gemini モデル名
    GEMINI_MODEL_NAME: str = "gemini-1.5-flash"


# シングルトンとして使用可能 (DBやサービス層で使用)
settings = Config()
