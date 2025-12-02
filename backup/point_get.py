import matplotlib.image as mpimg
import matplotlib.pyplot as plt

# 調べたい画像のパス
IMAGE_PATH = r"sample_bankbook.jpg"


def on_click(event):
    if event.xdata is not None and event.ydata is not None:
        # クリックした場所の座標を表示（整数に丸める）
        x = int(event.xdata)
        y = int(event.ydata)
        print(f"座標: ({x}, {y})")


# 画像を読み込んで表示
img = mpimg.imread(IMAGE_PATH)
fig, ax = plt.subplots()
ax.imshow(img)

# クリックイベントを紐付ける
fig.canvas.mpl_connect("button_press_event", on_click)

plt.title("クリックして座標を確認 (コンソールを見てね)")
plt.show()
