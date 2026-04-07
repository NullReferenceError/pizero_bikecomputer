from modules.app_logger import app_logger
from .display_core import Display

_BACKLIGHT_PATH = "/sys/class/backlight/rpi_backlight/brightness"


class HyperPixelDisplay(Display):
    has_touch = True
    has_color = True
    has_backlight = True
    allow_auto_backlight = True
    send = False

    size = (800, 480)
    color = 18
    brightness = 100
    brightness_table = [0, 100]
    brightness_index = len(brightness_table) - 1

    def __init__(self, config):
        super().__init__(config)
        self.size = (800, 480)
        self.brightness_index = len(self.brightness_table) - 1
        self.set_brightness(self.brightness_table[self.brightness_index])

    def quit(self):
        self.set_brightness(0)

    def clear(self):
        pass

    def update(self, buf, direct_update):
        pass

    def set_brightness(self, b):
        if b == self.brightness:
            return
        try:
            with open(_BACKLIGHT_PATH, "w") as f:
                f.write("1" if b > 0 else "0")
        except OSError as e:
            app_logger.warning(f"Failed to set backlight: {e}")
            return
        self.brightness = b
