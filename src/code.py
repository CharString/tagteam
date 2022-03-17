from adafruit_magtag.magtag import MagTag
import asyncio
from rainbowio import colorwheel
from secrets import secrets
import json

max_brightness = 0.3
my_pixel = secrets["my_pixel"]
feed = "image"
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


async def notification(pixel):
    "Blinks the `pixel` till any button is pressed"
    blink_task = asyncio.create_task(blink(pixel))
    while True:
        if magtag.peripherals.any_button_pressed:
            return blink_task.cancel()
        await asyncio.sleep(0.1)


async def test_notificaion():
    while True:
        if magtag.peripherals.button_a_pressed:
            print("Test notification: A pressed")
            await asyncio.sleep(0.1)  # debounce
            asyncio.create_task(notification(my_pixel))
        await asyncio.sleep(0.1)


def decode_pixel_state(data):
    "Decode the list of neopixel colours from IO feed data list"
    colors = [None, None, None, None]  # colors as sent to feed by pixel_owner
    guess = None  # colors as known by last feed entry
    for entry in data:
        if all(colors):
            # all latest colours known, stop processing history
            return colors
        try:
            d = json.loads(entry["value"])
            if "me" not in d or "colors" not in d:
                continue  # incomplete json
        except (ValueError, TypeError):
            continue  # skip invalid values in feed
        if not guess:
            guess = d["colors"]
        if colors[d["me"]] is None:
            colors[d["me"]] = d["colors"][d["me"]]
    guess = guess or [(0, 0, 0)] * 4
    return [(c if c else g) for c, g in zip(colors, guess)]


def encode_pixel_state(colors):
    return json.dumps({"me": my_pixel, "colors": colors})


async def get_io_pixel_state():
    data = magtag.get_io_data(feed)
    state = decode_pixel_state(data)
    print(state)
    return state


async def send_io_pixel_state(colors):
    return magtag.push_to_io(feed, encode_pixel_state(colors))


async def my_color():
    off = (0, 0, 0)
    for _ in range(11):  # retry for 1.1 second
        color = magtag.peripherals.neopixels[my_pixel]
        if color != off:
            return color
        else:
            await asyncio.sleep(0.1)
    return off  # default


async def pixel_sync():
    pixels = magtag.peripherals.neopixels
    throttle = 15 * 60  # AdafruitIO throttle
    while True:
        known = await get_io_pixel_state()
        mine = await my_color()
        if mine == (0, 0, 0):
            # on boot we don't know our color
            # set from io
            pixels[my_pixel] = mine = known[my_pixel]
        if mine != known[my_pixel]:
            # our color changed
            known[my_pixel] = mine
            await send_io_pixel_state(known)
        for i, color in enumerate(known):
            if i == my_pixel:
                continue
            if pixels[i] != color:
                pixels[i] = color
                # asyncio.create_task(notification(i))
        await asyncio.sleep(throttle)


async def main():
    # blink_task = asyncio.create_task(blink())
    await asyncio.gather(
        asyncio.create_task(color_control()),
        asyncio.create_task(brightness_control()),
        # asyncio.create_task(test_notificaion()),
        asyncio.create_task(pixel_sync()),
    )


# This makes code importable from the REPL without starting all tasks
# just connect your terminal send CTRL-C to stop the running tasks
# and type `import code` on the >>> prompt
if __name__ == "__main__":
    asyncio.run(main())
