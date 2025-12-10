# services/ai_service.py
import os
import logging
import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
from google.oauth2 import service_account
from google.api_core.exceptions import GoogleAPICallError, PermissionDenied

# 設定ファイルをインポート
# プロジェクト構成に合わせてパスを調整してください (例: src.config または config)
try:
    from src.config import Config
except ImportError:
    from config import Config

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIService:
    """Vertex AI (Gemini) との通信を担当するサービスクラス"""

    def __init__(self) -> None:
        self.model: GenerativeModel | None = None
        self._initialize_vertex_ai()

    def _initialize_vertex_ai(self) -> None:
        """
        Vertex AIの初期化を行う。
        認証ファイルが存在する場合はそれを使用し、なければデフォルト認証を試みる。
        """
        try:
            creds = None
            
            # 明示的にJSONキーファイルが存在するか確認
            if Config.GOOGLE_CREDENTIALS_PATH and os.path.exists(Config.GOOGLE_CREDENTIALS_PATH):
                logger.info(f"認証ファイルを読み込み中: {Config.GOOGLE_CREDENTIALS_PATH}")
                creds = service_account.Credentials.from_service_account_file(
                    Config.GOOGLE_CREDENTIALS_PATH
                )
            else:
                logger.warning(
                    f"認証ファイルが見つかりません: {Config.GOOGLE_CREDENTIALS_PATH}。 "
                    "Application Default Credentials (ADC) を試行します。"
                )

            # Vertex AI 初期化
            vertexai.init(
                project=Config.GOOGLE_PROJECT_ID,
                location=Config.GOOGLE_LOCATION,
                credentials=creds
            )
            
            self.model = GenerativeModel(Config.GEMINI_MODEL_NAME)
            logger.info("Vertex AI 初期化成功")

        except Exception as e:
            logger.error(f"Vertex AI 初期化エラー: {e}")
            self.model = None

    async def generate_response(self, prompt: str) -> str:
        """通常テキストチャット用"""
        if not self.model:
            self._initialize_vertex_ai()
            if not self.model:
                raise RuntimeError("AIモデルが初期化されていません。")

        try:
            response = await self.model.generate_content_async(prompt)
            return response.text if response.text else ""
        except Exception as e:
            logger.error(f"AI生成エラー: {e}")
            raise e

    async def generate_from_pdf(self, prompt: str, pdf_bytes: bytes, json_mode: bool = False) -> str:
        """
        PDFファイルを解析して回答を生成する
        
        Args:
            prompt (str): 指示プロンプト
            pdf_bytes (bytes): PDFファイルのバイナリデータ
            json_mode (bool): JSON形式での出力を強制するかどうか
        """
        if not self.model:
            self._initialize_vertex_ai()
            if not self.model:
                raise RuntimeError("AIモデルが初期化されていません。")

        try:
            # マルチモーダル入力データ作成
            pdf_part = Part.from_data(data=pdf_bytes, mime_type="application/pdf")
            
            # 設定（JSONモードなど）
            generation_config = None
            if json_mode:
                generation_config = GenerationConfig(response_mime_type="application/json")

            # 非同期リクエスト
            response = await self.model.generate_content_async(
                [pdf_part, prompt],
                generation_config=generation_config
            )
            
            if response.text:
                return response.text
            else:
                raise ValueError("AIからの応答が空でした。")

        except Exception as e:
            logger.error(f"PDF解析エラー: {e}")
            raise Exception(f"AI解析エラー: {str(e)}")

# シングルトンインスタンス
ai_service = AIService()