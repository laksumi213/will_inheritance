# src/services/ai_service.py
import logging

# Google Cloud / Vertex AI 依存を排除
# import vertexai
# from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
# from google.oauth2 import service_account

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIService:
    """
    AIサービスのダミークラス (Google Cloud依存排除版)
    """

    def __init__(self) -> None:
        self.model = None
        print("AIService initialized (Dummy Mode)")

    def _initialize_vertex_ai(self) -> None:
        pass

    async def generate_response(self, prompt: str) -> str:
        """通常テキストチャット用 (ダミー)"""
        return "AI機能は現在無効化されています。"

    async def generate_from_pdf(self, prompt: str, pdf_bytes: bytes, json_mode: bool = False) -> str:
        """PDFファイルを解析して回答を生成する (ダミー)"""
        if json_mode:
            return "{}"
        return "AI機能は現在無効化されています。"

# シングルトンインスタンス
ai_service = AIService()