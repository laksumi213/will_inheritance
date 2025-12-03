from flet import Colors, DropdownM2, TextStyle, dropdown


class CustomDropdown(DropdownM2):
    def __init__(
        self,
        color=Colors.BLACK,
        bgcolor=Colors.AMBER_50,
        width=200,
        text_style=TextStyle(color=Colors.BLACK),
        label_style=TextStyle(color=Colors.BLACK),
        focused_color=Colors.BLACK,
        # focused_border_color=Colors.BLACK,
        focused_border_color=Colors.CYAN,
        *args,
        **kwargs,
    ):
        super().__init__(
            color=color,
            bgcolor=bgcolor,
            width=width,
            text_style=text_style,
            label_style=label_style,
            focused_color=focused_color,
            focused_border_color=focused_border_color,
            *args,
            **kwargs,
        )

    def add_options(self, data):
        for item in data:
            self.options.append(dropdown.Option(*item.values()))
