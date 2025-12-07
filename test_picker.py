# test_picker.py
from flet import ElevatedButton, FilePicker, Page, app


def main(page: Page):
    def pick_files_result(e):
        print("Selected:", e.files)

    pick = FilePicker(on_result=pick_files_result)
    page.overlay.append(pick)
    page.update()

    page.add(
        ElevatedButton("Pick PDF", on_click=lambda _: pick.pick_files(allowed_extensions=["pdf"]))
    )


app(target=main)
