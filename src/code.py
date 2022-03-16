from adafruit_magtag.magtag import MagTag
import asyncio
from rainbowio import colorwheel
from secrets import secrets
import json

max_brightness = 0.3
my_pixel = secrets["my_pixel"]
ani = "It's working!!"
magtag = MagTag()
magtag.peripherals.neopixels.show()


class Colors:
    off = (0, 0, 0)

    def __init__(self, initial):
        self.color = initial


async def blink(pixel: int = my_pixel):
    pixels = magtag.peripherals.neopixels
    colors = Colors(pixels[pixel])

    def toggle():
        if magtag.peripherals.any_button_pressed:
            return  # prevent blinking when setting color
        if pixels[pixel] == colors.off:
            pixels[pixel] = colors.color
        else:
            colors.color = pixels[pixel]  # current colour
            pixels[pixel] = colors.off

    while True:
        print(f"Blinking pixel {pixel}: {colors.color}")
        print(f"Brightness: {pixels.brightness}")
        toggle()
        await asyncio.sleep(1)


async def color_control():
    "Control my colour with b and c buttons"
    pixels = magtag.peripherals.neopixels
    cur = wheel = 0
    step_size = 5
    while True:
        if magtag.peripherals.button_b_pressed:
            wheel += step_size
        if magtag.peripherals.button_c_pressed:
            wheel -= step_size
        wheel %= 255  # keep wheel in the interval [0, 255]
        if wheel != cur:
            pixels[my_pixel] = colorwheel(wheel)
            cur = wheel
        await asyncio.sleep(0.1)


async def brightness_control():
    "Control the brightness according to ambient light sensor"
    pixels = magtag.peripherals.neopixels

    def factor():
        return min(magtag.peripherals.light / 10_000, 1)

    while True:
        pixels.brightness = max(max_brightness * factor(), 0.02)

        await asyncio.sleep(5)


async def main():
    blink_task = asyncio.create_task(blink())
    color_task = asyncio.create_task(color_control())
    brightness_task = asyncio.create_task(brightness_control())
    await asyncio.gather(blink_task, color_task, brightness_task)


asyncio.run(main())
