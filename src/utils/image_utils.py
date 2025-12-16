# src/utils/image_utils.py
import base64
import io
from typing import List, Tuple

from PIL import Image, ImageDraw


def apply_masking_to_image(base64_image: str, masks: List[Tuple[float, float, float, float]], original_width: int, original_height: int, display_width: float, display_height: float) -> str:
    """
    Base64画像に対してマスキング（黒塗り）を適用し、再度Base64文字列として返す。
    
    Args:
        base64_image: 元画像のBase64文字列
        masks: マスキング矩形のリスト [(x, y, width, height), ...] (UI上の座標)
        original_width: 元画像の実際の幅
        original_height: 元画像の実際の高さ
        display_width: UIでの表示幅
        display_height: UIでの表示高さ
    
    Returns:
        str: マスキング適用後の画像(Base64, JPEG)
    """
    try:
        # Base64デコード
        image_data = base64.b64decode(base64_image)
        img = Image.open(io.BytesIO(image_data))
        
        # 描画オブジェクト作成
        draw = ImageDraw.Draw(img)
        
        # スケール比率の計算
        scale_x = original_width / display_width
        scale_y = original_height / display_height
        
        for mask in masks:
            ui_x, ui_y, ui_w, ui_h = mask
            
            # UI座標を実画像座標に変換
            real_x = ui_x * scale_x
            real_y = ui_y * scale_y
            real_w = ui_w * scale_x
            real_h = ui_h * scale_y
            
            # 矩形描画 (黒塗り)
            draw.rectangle(
                [real_x, real_y, real_x + real_w, real_y + real_h],
                fill="black",
                outline="black"
            )
            
        # 画像をバッファに保存
        output_buffer = io.BytesIO()
        img.save(output_buffer, format="JPEG", quality=95)
        return base64.b64encode(output_buffer.getvalue()).decode("utf-8")
        
    except Exception as e:
        print(f"Masking Error: {e}")
        return base64_image  # エラー時は元画像を返す