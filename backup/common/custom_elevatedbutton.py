from flet import Container, ElevatedButton, Icon, Row, Text


class CustomElevatedButton(ElevatedButton):
    def __init__(
        self,
        icon: str = "",
        text_value: str = "",
        text_size=20,
        height=40,
        data="",
        on_click=None,
        # on_hover=None,
        *args,
        **kwargs,
    ):
        super().__init__(
            height=height,
            data=data,
            on_click=self._on_click,
            on_hover=self._on_hover,
            *args,
            **kwargs,
        )

        self._on_click_callback = on_click

        self.content = Container(
            content=Row(
                controls=[
                    Icon(icon),
                    Text(value=text_value, size=text_size),
                ]
            ),
            height=height,
            data=data,
        )

    def _on_click(self, buf):
        print()
        print("_on_click:")
        # print('buf:', buf)
        # print('self:', self)
        # print('buf:', buf)
        if self._on_click_callback:
            self._on_click_callback(buf)

    def _on_hover(self, e):
        e.control.bgcolor = "GREY" if e.data == "true" else "AMBER_50"
        self.update()
