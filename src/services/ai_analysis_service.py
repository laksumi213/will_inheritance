# src/services/ai_analysis_service.py
from typing import Optional

import vertexai
from vertexai.generative_models import GenerativeModel, Part

from src.config import settings


class AIAnalysisService:
    """
    Vertex AI (Gemini) を使用したAI解析サービス
    """

    def __init__(
        self, project_id: str = settings.VERTEX_AI_PROJECT_ID, location: str = "asia-northeast1"
    ):
        self.project_id = project_id
        self.location = location
        self.model: Optional[GenerativeModel] = None
        self._initialized = False

    def _initialize(self):
        """Vertex AIの初期化"""
        if self._initialized:
            return

        try:
            # 認証情報が環境変数 (GOOGLE_APPLICATION_CREDENTIALS) に設定されている前提
            vertexai.init(project=self.project_id, location=self.location)
            self.model = GenerativeModel("gemini-1.5-flash-001")  # または gemini-1.5-pro
            self._initialized = True
            print("Vertex AI initialized successfully.")
        except Exception as e:
            print(f"Failed to initialize Vertex AI: {e}")
            # エラー時でもアプリ全体が落ちないようにする

    def analyze_document_text(self, text_content: str) -> str:
        """テキストデータを解析して要約や抽出を行う"""
        self._initialize()
        if not self.model:
            return "AI Service is not available."

        prompt = f"""
        あなたは遺産相続業務の専門家アシスタントです。
        以下の文章から、重要な「日付」「金額」「人物名」を抽出してJSON形式で出力してください。
        
        文章:
        {text_content}
        """

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI Analysis Error: {e}"

    def analyze_image(
        self, image_path: str, prompt_text: str = "この画像の内容を説明してください"
    ) -> str:
        """画像を解析する（OCR用途など）"""
        self._initialize()
        if not self.model:
            return "AI Service is not available."

        try:
            with open(image_path, "rb") as f:
                image_data = f.read()

            image_part = Part.from_data(
                data=image_data, mime_type="image/jpeg"
            )  # MIMEタイプは動的に判定推奨

            response = self.model.generate_content([image_part, prompt_text])
            return response.text
        except Exception as e:
            return f"Image Analysis Error: {e}"


# シングルトンインスタンス
ai_service = AIAnalysisService()
