# src/services/ai_service.py
import logging
import os
import json
import asyncio
from typing import List, Dict, Any
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
    利用可能なモデルを自動判別し、エラー時はフォールバックします。
    """

    # 優先順位順のモデルリスト
    MODEL_CANDIDATES = [
        'gemini-2.5-flash',       # 最新の標準モデル (推奨: 高速・低コスト)
        'gemini-2.5-pro',         # 最新の高性能モデル (高精度)
        'gemini-3-pro-preview',   # 次世代プレビュー (最高性能)
        'gemini-2.5-flash-lite',  # 最軽量モデル
        'gemini-1.5-flash',       # 旧安定版 (互換性のため残す場合)
    ]

    def __init__(self) -> None:
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.active_model_name = None
        
        if HAS_GEMINI and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = self._init_default_model()
            print(f"✅ Gemini AI Service initialized. (Default: {self.active_model_name})")
        else:
            self.model = None
            print("⚠️ Gemini AI Service not available (API Key missing or library not installed).")

    def _init_default_model(self):
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

    # --- 不動産 ---
    async def analyze_real_estate_document(self, base64_image: str) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self.analyze_real_estate_document_sync, base64_image)

    def analyze_real_estate_document_sync(self, base64_image: str) -> List[Dict[str, Any]]:
        prompt = """
        あなたは日本の不動産登記の専門家です。
        提供された名寄帳または固定資産税課税明細書の画像から、不動産（土地・家屋）の情報を抽出してください。
        以下のJSON形式のリストで出力してください。
        
        [
          {
            "type": "Land" または "Building" (土地か家屋か),
            "location": "所在",
            "lot_number": "地番 または 家屋番号",
            "category": "地目 または 種類",
            "area": "地積 または 床面積 (数値のみ、単位不要)",
            "structure": "構造 (建物の場合のみ、土地は'-')",
            "share": "持分 (不明な場合は'1/1'または空文字)"
          }
        ]
        """
        return self._run_analysis(base64_image, prompt)

    # --- 銀行 ---
    def analyze_bank_document_sync(self, base64_image: str) -> List[Dict[str, Any]]:
        """
        通帳や残高証明書から銀行口座情報を抽出する
        """
        prompt = """
        あなたは金融資産管理の専門家です。
        提供された銀行の通帳または残高証明書の画像から、口座情報を抽出してください。
        以下のJSON形式のリストで出力してください。
        
        [
          {
            "bank_name": "銀行名 (例: みずほ銀行)",
            "branch_name": "支店名 (例: 銀座支店)",
            "account_type": "口座種類 (例: 普通、定期)",
            "account_number": "口座番号",
            "balance": "残高または評価額 (数値のみ、カンマなし、円マークなし)"
          }
        ]
        """
        return self._run_analysis(base64_image, prompt)

    # --- 証券 ---
    def analyze_securities_document_sync(self, base64_image: str) -> List[Dict[str, Any]]:
        """
        取引残高報告書などから証券口座情報を抽出する
        """
        prompt = """
        あなたは金融資産管理の専門家です。
        提供された証券会社の取引残高報告書または評価証明書の画像から、口座情報を抽出してください。
        以下のJSON形式のリストで出力してください。
        
        [
          {
            "securities_name": "証券会社名 (例: 野村證券)",
            "branch_name": "部店名 (例: 本店)",
            "account_type": "口座区分 (例: 特定、一般)",
            "account_number": "口座番号 (加入者コード)",
            "balance": "評価額合計 (数値のみ、カンマなし、円マークなし)"
          }
        ]
        """
        return self._run_analysis(base64_image, prompt)

    # --- 共通実行ロジック ---
    def _run_analysis(self, base64_image: str, prompt: str) -> List[Dict[str, Any]]:
        if not self.model:
            time.sleep(1)
            return [] # APIキーがない場合は空リスト

        image_parts = [{"mime_type": "image/jpeg", "data": base64_image}]

        try:
            return self._execute_generation(self.model, prompt, image_parts)
        except (NotFound, InvalidArgument, Exception) as e:
            print(f"⚠️ Model {self.active_model_name} failed: {e}")
            
            # フォールバック試行
            for model_name in self.MODEL_CANDIDATES:
                if model_name == self.active_model_name: continue
                try:
                    print(f"Trying model: {model_name}...")
                    fallback_model = genai.GenerativeModel(model_name)
                    result = self._execute_generation(fallback_model, prompt, image_parts)
                    self.model = fallback_model
                    self.active_model_name = model_name
                    print(f"✅ Switched to {model_name} successfully.")
                    return result
                except Exception:
                    pass
            
            print("❌ All models failed.")
            return []

    def _execute_generation(self, model, prompt, image_parts):
        response = model.generate_content([prompt, image_parts[0]])
        text = response.text
        json_str = text
        if "```json" in text:
            json_str = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            json_str = text.split("```")[1].split("```")[0]
        return json.loads(json_str.strip())

# シングルトンインスタンス
ai_service = AIService()