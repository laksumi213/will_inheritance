# src/config.py
import os
from dotenv import load_dotenv
from pathlib import Path

from flet import Colors, Theme, ThemeMode, VisualDensity

# --- Fletテーマ設定 ---
APP_THEME = Theme(
    color_scheme_seed=Colors.TEAL,
    visual_density=VisualDensity.COMFORTABLE,
)
DEFAULT_THEME_MODE = ThemeMode.DARK

load_dotenv()

# --- アプリケーション設定 ---
class Config:
    """アプリケーション全体の設定定数"""

    # パス設定
    BASE_DIR = Path(__file__).parent.parent
    ASSETS_DIR = BASE_DIR / "assets"
    DB_PATH = BASE_DIR / "database.sqlite"

    # アプリ設定
    APP_TITLE = "遺産整理・相続業務システム"
    VERSION = "1.0.0"

    # テーマカラー
    COLOR_PRIMARY = Colors.BLUE_500
    COLOR_SECONDARY = Colors.TEAL_500
    COLOR_ERROR = Colors.RED_600
    COLOR_BACKGROUND = Colors.WHITE
    COLOR_SURFACE_VARIANT = "surfaceVariant"

    # 外部サービス設定 (Google Cloud無効化)
    # VERTEX_AI_PROJECT_ID = os.getenv("VERTEX_AI_PROJECT_ID", "")
    SELENIUM_HEADLESS = False

    # Google Cloud Project ID (Deprecated)
    # GOOGLE_PROJECT_ID: str = os.getenv("GOOGLE_PROJECT_ID", "your-project-id")
    
    # Vertex AI Region (Deprecated)
    # GOOGLE_LOCATION: str = os.getenv("GOOGLE_LOCATION", "us-central1")
    
    # GOOGLE_CREDENTIALS_PATH: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

    # GEMINI_MODEL_NAME: str = "gemini-1.5-flash"


# シングルトンとして使用可能
settings = Config()