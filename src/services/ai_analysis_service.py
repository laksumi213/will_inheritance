# src/services/ai_analysis_service.py
from typing import Optional

# import vertexai
# from vertexai.generative_models import GenerativeModel, Part

from src.config import settings


class AIAnalysisService:
    """
    AI解析サービスのダミークラス (Google Cloud依存排除版)
    """

    def __init__(self, project_id: str = "", location: str = "asia-northeast1"):
        self.project_id = project_id
        self.location = location
        self.model = None
        self._initialized = False

    def _initialize(self):
        pass

    def analyze_document_text(self, text_content: str) -> str:
        return "AI Service is not available."

    def analyze_image(
        self, image_path: str, prompt_text: str = "この画像の内容を説明してください"
    ) -> str:
        return "AI Service is not available."


# シングルトンインスタンス
ai_service = AIAnalysisService()