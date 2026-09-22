import os
import subprocess
import time

import mss
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AHK_EXE = r"C:\Program Files\AutoHotkey\UX\AutoHotkeyUX.exe"

# All coordinates are for 1920x1080. Values were calibrated from real
# screenshots: the "E) CAST" prompt starts ~100px further left than
# "E) START REELING", and the floating bobber is a small cyan blob.
MONITOR = 1  # mss monitor index (1 = primary)

# Fishing.ba2 draws a pink marker at the top-left corner while in fishing mode
MARKER_POS = (2, 2)
MARKER_RGB = (0xF7, 0xA0, 0xB5)
MARKER_TOLERANCE = 20

# Left part of the prompt bar - only has white text when it says "E) CAST"
CAST_ZONE = {"left": 580, "top": 1022, "width": 80, "height": 30}
CAST_MIN_WHITE = 100        # seen: 392 when showing, 0 otherwise

# Water area. Starts below the horizon so the bobber hanging from the rod
# tip (before casting) isn't counted.
WATER_ZONE = {"left": 0, "top": 560, "width": 1920, "height": 440}
BOBBER_MIN_PIXELS = 5       # seen: ~30 for a mid-distance bobber, 0 after a bite

BITE_CONFIRM = 0.2          # bobber must be gone this long before reeling
CAST_SETTLE = 4             # time for the bobber to land after casting
NO_BOBBER_TIMEOUT = 10      # bobber never showed up after casting -> reel in and retry
MAX_WAIT = 30               # no bite after this long -> reel in and recast
MINIGAME_TIMEOUT = 60       # give up waiting for "CAST" after reeling
CAST_DELAY = 2              # pause after "CAST" appears before casting again
POLL = 0.03

DEBUG = True                # print detection values once a second, for tuning


def press_e():
    print("Pressing 'e'")
    subprocess.Popen([AHK_EXE, os.path.join(SCRIPT_DIR, "press_e.ahk")])


def start_easy_fishing():
    # EasyFishing.ahk is AutoHotkey v1 syntax; easyFishing.exe is a
    # precompiled v1 build of it, so launch that directly.
    print("Launching easyFishing.exe...")
    subprocess.Popen([os.path.join(SCRIPT_DIR, "easyFishing.exe")], cwd=SCRIPT_DIR)
    time.sleep(1.5)  # give it time to load and register the F5 hotkey
    print("Starting EasyFishing loop (F5)...")
    subprocess.Popen([AHK_EXE, os.path.join(SCRIPT_DIR, "press_f5.ahk")])


class Screen:
    def __init__(self):
        self.sct = mss.mss()
        mon = self.sct.monitors[MONITOR]
        self.offset = (mon["left"], mon["top"])

    def grab(self, zone):
        region = dict(zone)
        region["left"] += self.offset[0]
        region["top"] += self.offset[1]
        # mss returns BGRA
        return np.asarray(self.sct.grab(region))[..., 2::-1].astype(np.int16)

    def in_fishing_mode(self):
        x, y = MARKER_POS
        px = self.grab({"left": x, "top": y, "width": 1, "height": 1})[0, 0]
        return all(abs(int(c) - t) <= MARKER_TOLERANCE for c, t in zip(px, MARKER_RGB))

    def cast_white_pixels(self):
        img = self.grab(CAST_ZONE)
        return int((img.min(axis=2) > 200).sum())

    def bobber_pixels(self):
        img = self.grab(WATER_ZONE)
        r, g, b = img[..., 0], img[..., 1], img[..., 2]
        cyan = (g > 150) & (b > 150) & (g - r > 40) & (b - r > 40)
        return int(cyan.sum())


STATE_IDLE = "idle"            # waiting for the "CAST" prompt
STATE_CASTING = "casting"      # cast pressed, bobber landing
STATE_WAITING = "waiting"      # bobber floating, watching for a bite
STATE_REELING = "reeling"      # EasyFishing is playing the minigame

state = STATE_IDLE
last_state_change = time.time()
bobber_seen = False
bobber_gone_since = None
cast_seen_since = None
catches = 0


def set_state(new_state):
    global state, last_state_change
    state = new_state
    last_state_change = time.time()
    print(f">>> State changed to {state}")


def tick(screen):
    global bobber_seen, bobber_gone_since, cast_seen_since, catches

    now = time.time()
    elapsed = now - last_state_change
    cast_prompt = screen.cast_white_pixels() >= CAST_MIN_WHITE

    if state in (STATE_IDLE, STATE_REELING):
        if cast_prompt:
            if cast_seen_since is None:
                cast_seen_since = now
            if now - cast_seen_since >= CAST_DELAY:
                print("Casting...")
                press_e()
                cast_seen_since = None
                bobber_seen = False
                bobber_gone_since = None
                set_state(STATE_CASTING)
        else:
            cast_seen_since = None
            if state == STATE_REELING and elapsed >= MINIGAME_TIMEOUT:
                print("Never got back to the CAST prompt - resetting.")
                set_state(STATE_IDLE)
        return

    bobber = screen.bobber_pixels() >= BOBBER_MIN_PIXELS

    if state == STATE_CASTING:
        if bobber:
            bobber_seen = True
        if elapsed >= CAST_SETTLE:
            set_state(STATE_WAITING)
        return

    # STATE_WAITING
    if bobber:
        bobber_seen = True
        bobber_gone_since = None
    elif bobber_seen:
        if bobber_gone_since is None:
            bobber_gone_since = now
        if now - bobber_gone_since >= BITE_CONFIRM:
            catches += 1
            print(f"Bite #{catches}! Reeling in.")
            press_e()
            set_state(STATE_REELING)
            return

    if not bobber_seen and elapsed >= NO_BOBBER_TIMEOUT:
        print("Couldn't find the bobber - reeling in to recast.")
        press_e()
        set_state(STATE_REELING)
    elif elapsed >= MAX_WAIT:
        print(f"No bite after {MAX_WAIT}s - reeling in to recast.")
        press_e()
        set_state(STATE_REELING)


def main():
    screen = Screen()
    start_easy_fishing()
    print("Watching the screen. Press Ctrl+C to stop...")
    last_debug = 0.0
    try:
        while True:
            if not screen.in_fishing_mode():
                if time.time() - last_debug >= 1.0:
                    print("Not in fishing mode (no pink marker) - waiting...")
                    last_debug = time.time()
                time.sleep(0.5)
                continue

            tick(screen)

            if DEBUG and time.time() - last_debug >= 1.0:
                print(f"[debug] state={state} cast_white={screen.cast_white_pixels()} "
                      f"bobber_px={screen.bobber_pixels()}")
                last_debug = time.time()

            time.sleep(POLL)
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
