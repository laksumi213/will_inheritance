import asyncio

from flet import Colors, TextField, TextStyle


class CustomTextField(TextField):
    def __init__(
        self,
        label: str = "",
        label_style=TextStyle(color=Colors.BLACK),
        # hint_text: str = "",
        color=Colors.BLACK,
        focused_border_color=Colors.CYAN,
        password: bool = False,
        width=200,
        on_change=None,
        on_focus=None,
        on_blur=None,
        format=None,
        hinttext=None,
        *args,
        **kwargs,
    ):
        super().__init__(
            label=label,
            label_style=label_style,
            color=color,
            width=width,
            focused_border_color=focused_border_color,
            password=password,
            on_change=self._on_change,
            on_focus=self._on_focus,
            on_blur=self._on_blur,
            *args,
            **kwargs,
        )
        self._on_change_callback = on_change
        self._blur_callback = on_blur
        self._on_focus = on_focus
        self._blur = on_blur
        self.hint_text = hinttext
        self.format = format
        # self.label_style = TextStyle(color=Colors.BLACK)
        # self.color = Colors.BLACK
        # self.focused_border_color = Colors.CYAN

    def _on_blur(self, e):
        # print('_blur:')
        if self._blur_callback:
            self._blur_callback(e)

    def _on_change(self, e):
        if self._on_change_callback:
            self._on_change_callback(e)

    def _on_focus(self, e):
        if self.format == "ime_on":
            self.ime_on()

        if self.format == "ime_off":
            self.ime_off()

        if self.format == "number":
            self.ime_off()
            self.re_number_format(e)

    # def _on_blur(self, e):
    #     if self.format == "number":
    #         self.number_format(e)

    def number_format(self, e):
        e.control.value = (
            format(int(e.control.value), ",") if e.control.value != "" else 0
        )
        self.page.update()

    def re_number_format(self, e):
        e.control.value = str(e.control.value).replace(",", "")
        self.page.update()

    @classmethod
    def ime_on(cls):
        asyncio.new_event_loop().run_in_executor(None, utils.ime_on)

    @classmethod
    def ime_off(cls):
        asyncio.new_event_loop().run_in_executor(None, utils.ime_off)

    @classmethod
    def create_self(cls, config=None):
        return CustomTextField(**config)
