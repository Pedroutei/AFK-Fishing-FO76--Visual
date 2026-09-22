AFK Fishing FO76 - Visual version (no VB-Cable needed)
Must use Nuka Cola Quantum Bobber
Requirements
- Python 3 with: pip install mss numpy
- AutoHotkey v2 (C:\Program Files\AutoHotkey)
- Fishing.ba2 installed (draws the pink marker EasyFishing and this script rely on)
- Game at 1920x1080, windowed or borderless, on the primary monitor


1. Under Game settings disable C.A.M.P. Weather and Intense Weather Effects
2. Walk up to water and enter fishing mode
3. Run "Fishing Script/autoFish.py"

How it works
- "E) CAST" prompt visible          -> press E to cast
- Cyan bobber floating in the water -> wait
- Bobber disappears (bite)          -> press E to reel, easyFishing.exe plays the minigame
- Back to "E) CAST"                 -> repeat

Tuning
DEBUG = True in autoFish.py prints cast_white and bobber_px once a second.
If the bobber isn't detected (bobber_px stays near 0 while it's floating),
lower BOBBER_MIN_PIXELS or adjust WATER_ZONE.
