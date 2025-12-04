import os
import time
import tkinter as tk
from tkinter import messagebox

import fitz  # PyMuPDF
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image, ImageTk

# --- 初期設定 ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)


class PdfMaskingApp:
    def __init__(self, root, pdf_path):
        self.root = root
        self.root.title("PDFマスキングツール - 範囲を指定してGeminiへ送信")
        self.pdf_path = pdf_path
        self.temp_output = "masked_temp.pdf"

        # PDFを開く
        self.doc = fitz.open(self.pdf_path)
        self.page = self.doc[0]  # 1ページ目を対象（必要ならページ送り機能を追加可能）

        # 画面表示用の画像を生成
        # 解像度を上げて文字を見やすくする (matrix=2.0)
        self.zoom_matrix = fitz.Matrix(2.0, 2.0)
        self.pix = self.page.get_pixmap(matrix=self.zoom_matrix)

        # PIL形式に変換
        # img_data = Image.frombytes("RGB", [self.pix.width, self.pix.height], self.pix.samples)

        # img_data = img_data.convert("RGB")  # 必須変換
        # # self.tk_img = ImageTk.PhotoImage(img_data)
        # # または純粋 tkinter
        # self.tk_img = tk.PhotoImage(
        #     data=img_data.tobytes(), width=img_data.width, height=img_data.height
        # )

        # self.tk_img = ImageTk.PhotoImage(img_data)

        img_data = Image.frombytes("RGB", [self.pix.width, self.pix.height], self.pix.samples)
        img_data = img_data.convert("RGB")  # RGBに変換

        self.tk_img = ImageTk.PhotoImage(img_data)

        # 座標変換のためのスケール計算
        # PDF本来の座標系と、表示している画像(zoom_matrix適用後)の比率
        self.scale_x = self.page.rect.width / self.pix.width
        self.scale_y = self.page.rect.height / self.pix.height

        # --- GUIの配置 ---
        # キャンバス（画像を表示するエリア）
        self.canvas = tk.Canvas(root, width=self.pix.width, height=self.pix.height, cursor="cross")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, image=self.tk_img, anchor=tk.NW)

        # ボタンエリア
        btn_frame = tk.Frame(root)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        tk.Button(btn_frame, text="元に戻す (直前の選択を消す)", command=self.undo_last).pack(
            side=tk.LEFT, padx=10
        )
        tk.Button(btn_frame, text="全てクリア", command=self.clear_all).pack(side=tk.LEFT, padx=10)

        # メインのアクションボタン
        btn_send = tk.Button(
            btn_frame,
            text="決定してAI解析実行",
            command=self.execute_masking_and_send,
            bg="#ddffdd",
            font=("Arial", 12, "bold"),
        )
        btn_send.pack(side=tk.RIGHT, padx=20)

        # --- マウスイベントのバインド ---
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        # 内部変数
        self.rect = None
        self.start_x = None
        self.start_y = None

        # 選択範囲リスト [(canvas_rect_id, x0, y0, x1, y1), ...]
        self.selections = []

    def on_button_press(self, event):
        # クリック開始位置を記憶
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        # 仮の長方形を描画
        self.rect = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x,
            self.start_y,
            outline="red",
            width=2,
            fill="black",
            stipple="gray50",
        )

    def on_move_press(self, event):
        # ドラッグ中に長方形のサイズを更新
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        # マウスを離したら確定
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)

        # 選択範囲をリストに保存
        # 座標を正規化（左上、右下になるように）
        x0, x1 = sorted([self.start_x, cur_x])
        y0, y1 = sorted([self.start_y, cur_y])

        self.selections.append({"id": self.rect, "coords": (x0, y0, x1, y1)})
        self.rect = None

    def undo_last(self):
        if self.selections:
            last = self.selections.pop()
            self.canvas.delete(last["id"])

    def clear_all(self):
        for s in self.selections:
            self.canvas.delete(s["id"])
        self.selections = []

    def execute_masking_and_send(self):
        if not self.selections:
            if not messagebox.askyesno(
                "確認", "マスキング箇所がありませんが、そのままAIに送信しますか？"
            ):
                return

        # --- 1. PDFにマスキングを適用 ---
        print("マスキング処理中...")
        for s in self.selections:
            x0, y0, x1, y1 = s["coords"]

            # キャンバス座標 → PDF座標への変換
            pdf_rect = fitz.Rect(
                x0 * self.scale_x,
                y0 * self.scale_y,
                x1 * self.scale_x,
                y1 * self.scale_y,
            )

            # 黒塗りの追加
            self.page.add_redact_annot(pdf_rect, fill=(0, 0, 0))

        # 適用（テキストデータも削除）
        self.page.apply_redactions()

        # 一時ファイルに保存
        self.doc.save(self.temp_output)
        self.doc.close()

        print(f"マスキング済みファイルを保存しました: {self.temp_output}")
        self.root.destroy()  # GUIを閉じる

        # --- 2. Geminiへ送信 ---
        self.send_to_gemini(self.temp_output)

    def send_to_gemini(self, file_path):
        print("\n--- Geminiへ送信開始 ---")
        try:
            uploaded_file = genai.upload_file(path=file_path)

            print("アップロード中...")
            while uploaded_file.state.name == "PROCESSING":
                print(".", end="", flush=True)
                time.sleep(1)
                uploaded_file = genai.get_file(uploaded_file.name)

            if uploaded_file.state.name == "FAILED":
                print("アップロードに失敗しました。")
                return

            print("\n解析実行中...")
            model = genai.GenerativeModel(model_name="gemini-1.5-flash")

            prompt = """
            このPDF文書から、黒塗りされていない部分を読み取り、以下の情報を抽出してください。
            
            【抽出項目】
            1. 金融機関名
            2. 担当者名
            """

            response = model.generate_content([uploaded_file, prompt])

            print("=" * 40)
            print(response.text)
            print("=" * 40)

            # 後始末
            genai.delete_file(uploaded_file.name)
            if os.path.exists(file_path):
                os.remove(file_path)
                print("一時ファイルを削除しました。")

        except Exception as e:
            print(f"エラーが発生しました: {e}")


# --- メイン実行部 ---
if __name__ == "__main__":
    target_pdf = "au.pdf"  # ここに読み込むPDFファイル名を指定

    if os.path.exists(target_pdf):
        root = tk.Tk()
        # ウィンドウサイズ設定（必要に応じて調整）
        # root.geometry("1000x800")
        app = PdfMaskingApp(root, target_pdf)
        root.mainloop()
    else:
        print(f"ファイル {target_pdf} が見つかりません。")
