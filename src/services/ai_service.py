# src/services/ai_service.py
import logging
import os
import json
import asyncio
from typing import List, Dict, Any, Optional
import time

# Google Generative AI (Gemini)
try:
    import google.generativeai as genai
    from google.api_core.exceptions import NotFound, InvalidArgument
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIService:
    """
    AIサービスのクラス (Google Gemini対応)
    手書き文字認識の精度向上チューニング済み
    """

    # 優先順位順のモデルリスト
    # 手書き認識には Pro モデルが比較的強い傾向があります
    MODEL_CANDIDATES = [
        'gemini-2.5-flash',       # 最新の標準モデル (推奨: 高速・低コスト)
        'gemini-2.5-pro',         # 最新の高性能モデル (高精度)
        'gemini-3-pro-preview',   # 次世代プレビュー (最高性能)
        'gemini-2.5-flash-lite',  # 最軽量モデル
        'gemini-1.5-flash',       # 旧安定版 (互換性のため残す場合)
    ]

    def __init__(self) -> None:
        self.api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
        self.active_model_name: Optional[str] = None
        
        if HAS_GEMINI and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = self._init_default_model()
            print(f"✅ Gemini AI Service initialized. (Default: {self.active_model_name})")
        else:
            self.model = None
            print("⚠️ Gemini AI Service not available (API Key missing or library not installed).")

    def _init_default_model(self) -> genai.GenerativeModel:
        """最初に試行するモデルを初期化"""
        self.active_model_name = self.MODEL_CANDIDATES[0]
        return genai.GenerativeModel(self.active_model_name)

    async def generate_response(self, prompt: str) -> str:
        """通常テキストチャット用"""
        if not self.model:
            return "AI機能は無効化されています。(APIキー設定を確認してください)"
        
        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return response.text
        except Exception as e:
            return f"AI Error: {str(e)}"

    # --- 不動産（名寄帳）解析 ---
    async def analyze_real_estate_document(self, base64_image: str) -> Dict[str, Any]:
        """非同期での名寄帳解析"""
        return await asyncio.to_thread(self.analyze_real_estate_document_sync, base64_image)

    def analyze_real_estate_document_sync(self, base64_image: str) -> Dict[str, Any]:
        """
        名寄帳または固定資産税課税明細書の画像から情報を抽出する。
        """
        prompt = """
        あなたは日本の不動産登記および地方税務の専門家です。
        提供された名寄帳または固定資産税課税明細書の画像（手書きが含まれる可能性あり）から情報を抽出してください。

        【抽出ルール】
        1. candidate_locations: 
           書類の発行元自治体（都道府県および市区町村）を特定してください。
           ロゴ、印影、還付先案内、または「〇〇市長」「〇〇町村長」などの記載から推測してください。
           もし複数の可能性（例：合併前の旧地名と新地名）がある場合はすべて挙げてください。
           例: [{"prefecture": "東京都", "municipality": "中央区"}]

        2. properties:
           物件リスト（土地・家屋）を抽出してください。
           - type: "Land" (土地) または "Building" (家屋/建物)
           - location: 記載されている「所在」の最小単位（町名、字、枝番など）。
             ※都道府県名や市区町村名は含めないでください。
           - lot_number: 地番 または 家屋番号
           - category: 地目 または 種類
           - area: 地積 または 床面積 (数値のみ)
           - structure: 構造 (建物ののみ)
           - share: 持分 (不明な場合は "1/1")

        以下のJSON形式のみで回答してください。
        {
          "candidate_locations": [
            {"prefecture": "都道府県名", "municipality": "市区町村名"}
          ],
          "properties": [
            {
              "type": "Land",
              "location": "銀座1丁目",
              "lot_number": "101-1",
              "category": "宅地",
              "area": "100.50",
              "structure": "-",
              "share": "1/1"
            }
          ]
        }
        """
        result = self._run_analysis(base64_image, prompt)
        if isinstance(result, list):
            return {"candidate_locations": [], "properties": result}
        return result

    # --- 銀行口座解析 (手書き対応強化) ---
    def analyze_bank_document_sync(self, base64_image: str) -> List[Dict[str, Any]]:
        """
        通帳や残高証明書から銀行口座情報を抽出する
        """
        prompt = """
        あなたは金融資産管理の専門家であり、筆跡鑑定のプロフェッショナルです。
        提供された銀行の通帳または残高証明書の画像から、口座情報を抽出してください。

        【重要：手書き文字の読み取りについて】
        - この書類には「手書き」の文字や数字が含まれている可能性が高いです。
        - 活字だけでなく、ペンで書かれた文字も慎重に読み取ってください。
        - 数字の「0」と「6」、「1」と「7」と「9」などの判別に注意してください。
        - 金額の桁区切り（カンマ）や円マークは数値データには含めないでください。

        以下のJSON形式のリストで出力してください。
        
        [
          {
            "bank_name": "銀行名 (例: みずほ銀行)",
            "branch_name": "支店名 (例: 銀座支店)",
            "account_type": "口座種類 (例: 普通、定期)",
            "account_number": "口座番号 (手書きの場合も正確に)",
            "balance": "残高または評価額 (数値のみ、カンマなし)"
          }
        ]
        """
        return self._run_analysis(base64_image, prompt)

    # --- 証券口座解析 ---
    def analyze_securities_document_sync(self, base64_image: str) -> List[Dict[str, Any]]:
        """
        取引残高報告書などから証券口座情報を抽出する
        """
        prompt = """
        あなたは金融資産管理の専門家です。
        提供された証券会社の取引残高報告書または評価証明書の画像から、口座情報を抽出してください。
        手書きの文字が含まれる場合も、文脈から判断して正確に読み取ってください。

        以下のJSON形式のリストで出力してください。
        
        [
          {
            "securities_name": "証券会社名 (例: 野村證券)",
            "branch_name": "部店名 (例: 本店)",
            "account_type": "口座区分 (例: 特定、一般)",
            "account_number": "口座番号 (加入者コード)",
            "balance": "評価額合計 (数値のみ、カンマなし)"
          }
        ]
        """
        return self._run_analysis(base64_image, prompt)

    # --- 共通実行ロジック ---
    def _run_analysis(self, base64_image: str, prompt: str) -> Any:
        """解析実行とリトライ・フォールバック制御"""
        if not self.model:
            time.sleep(0.5)
            return []

        image_parts = [{"mime_type": "image/jpeg", "data": base64_image}]

        try:
            return self._execute_generation(self.model, prompt, image_parts)
        except (NotFound, InvalidArgument, Exception) as e:
            logger.warning(f"⚠️ Model {self.active_model_name} failed: {e}. Trying fallback...")
            
            # フォールバック試行
            for model_name in self.MODEL_CANDIDATES:
                if model_name == self.active_model_name:
                    continue
                try:
                    fallback_model = genai.GenerativeModel(model_name)
                    result = self._execute_generation(fallback_model, prompt, image_parts)
                    self.model = fallback_model
                    self.active_model_name = model_name
                    logger.info(f"✅ Switched to {model_name} successfully.")
                    return result
                except Exception:
                    continue
            
            logger.error("❌ All models failed.")
            return {"candidate_locations": [], "properties": []} if "properties" in prompt else []

    def _execute_generation(self, model: genai.GenerativeModel, prompt: str, image_parts: List[Dict[str, str]]) -> Any:
        """実際のコンテンツ生成とJSONパース"""
        response = model.generate_content([prompt, image_parts[0]])
        text = response.text
        
        # MarkdownのJSONブロックを除去
        json_str = text
        if "```json" in text:
            json_str = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            json_str = text.split("```")[1].split("```")[0]
        
        return json.loads(json_str.strip())

# シングルトンインスタンス
ai_service = AIService()