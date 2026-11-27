# tapo-calibrate

Calibrate the colours of a TP-Link Tapo camera: white balance, saturation, contrast and more.

The Tapo app offers few image controls. The camera's local API has many more image settings, including fixed white balance gains. This tool reads and changes those settings, takes frames from the live stream, and measures colours in them. It can also find white balance gains for you from a grey card.

It was built to give a fish tank camera (a Tapo C110) true colours, so an AI could judge water tint and the health of fish and plants. It works for any scene where the camera's automatic white balance gets the colours wrong.

> Unofficial. The local API is undocumented and may change with firmware. Run `backup` before you change anything.

## Requirements

- Python 3.12+
- `ffmpeg` on your `PATH`
- A Tapo camera on your local network, and two logins:

| Variable | What it is |
|---|---|
| `TAPO_HOST` | The camera's IP address |
| `TAPO_PASSWORD` | Your **Tapo cloud account** password (the local API logs in as `admin` with it) |
| `TAPO_RTSP_USER` / `TAPO_RTSP_PASSWORD` | The **camera account** for the RTSP stream. Create it in the Tapo app: camera settings → Advanced settings → Camera account |

Keep the passwords in a password manager and load them into the environment, for example with `op read`. The tool hides them in every error message.

## Install

```sh
git clone https://github.com/markwallsgrove/tapo-calibrate
cd tapo-calibrate
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Commands

Every command prints one JSON object per line.

| Command | What it does |
|---|---|
| `tapo-calibrate show` | Print the image settings this tool changes |
| `tapo-calibrate backup backup.json` | Save every image setting |
| `tapo-calibrate restore backup.json` | Put the settings back from a backup |
| `tapo-calibrate set saturation=40 contrast=70` | Change settings (see below), then print them as the camera reports them |
| `tapo-calibrate snapshot frame.jpg` | Save one frame of the live picture |
| `tapo-calibrate measure frame.jpg X Y W H [--brightest 0.02]` | The mean colour in a box, the share of clipped pixels, and optionally the colour of the brightest pixels. Needs no camera |
| `tapo-calibrate calibrate X Y W H` | Find white balance gains that make a grey card in the box neutral |

A box is four fractions of the frame: left, top, width and height. `0.4 0.6 0.1 0.1` is a small square a little below and left of the centre.

Settings `set` accepts:

| Setting | Values | Default |
|---|---|---|
| `wb_type` | `auto`, `manual`, `locked` | `auto` |
| `wb_R_gain`, `wb_G_gain`, `wb_B_gain` | 0–100, used when `wb_type` is `manual` | 50 |
| `saturation`, `chroma`, `contrast`, `luma`, `sharpness` | 0–100 | 50 |

## How to calibrate

1. **Back up:** `tapo-calibrate backup original.json`.
2. **Set the scene as it will be used:** same light, same time of day. For a fish tank: tank light on, room lights as usual.
3. **Put a mid-grey card in view,** at the distance of what you care about. Use mid grey, not white: a white card is likely to clip, and a clipped channel can't be measured.
4. **Find the card:** `tapo-calibrate snapshot card.jpg`, open the image, and work out the card's box. Pick the evenly lit middle of the card, with no glare.
5. **Check it doesn't clip:** `tapo-calibrate measure card.jpg X Y W H`. `clipped` should be close to 0, and no channel near 235 or above.
6. **Calibrate:** `tapo-calibrate calibrate X Y W H`.
   - It sets `wb_type` to `manual`, keeps green at 50, and scales red and blue until the card is neutral, to within 2%.
   - It saves the old settings to `backup.json` first. If it can't converge, it puts the old white balance back.
   - It keeps the frame from each step in `frames/`.
7. **Check by eye, and adjust:** a neutral card doesn't always mean a picture that looks right. See the notes below. Fine-tune with `set` in large steps: a change of 5 in a gain is hard to see, a change of 20 is easy.
8. **Write the final values down.** A reset or firmware update may put the camera back on auto.

## What we learned (Tapo C110, hardware 3.0, firmware 1.3.1)

- **The local API has far more settings than ONVIF.** ONVIF offers only brightness, saturation, contrast and sharpness. The local API (`getLightFrequencyInfo` / `setLightFrequencyInfo` on `image.common`) has white balance mode and gains, chroma, luma, dehaze, wide dynamic range and more.
- **Manual white balance works.** `wb_type: manual` with gains has a strong, immediate effect. `locked` seems to freeze the current automatic gains.
- **Exposure settings are ignored.** The camera accepts `exp_type: manual`, `shutter` and `exp_level` but the picture barely changes, so under a bright light you can't stop a white card clipping. Use a mid-grey card and measure its least lit part.
- **One RTSP stream at a time.** Close the Tapo app's live view and any other viewer (such as Home Assistant's stream) before you grab frames, or ffmpeg gets nothing.
- **Lights with separate red, green and blue LEDs** (common on aquarium and plant lights) have a spiky spectrum. Three gains can't make every colour right under such a light, so a neutral grey card can still leave some colours looking off. Finish by eye.
- **A phone is not a reference.** Phone cameras set white balance for every shot. Two photos of the same stones a few minutes apart differed by over 25% in blue.
- **Depth tints colour.** Water absorbs red, so things further away look more blue-green, or yellow-green with tannins. Put the card where the things you care about are.

The settings we ended with for a planted tank under an RGB LED light:

```sh
tapo-calibrate set wb_type=manual wb_R_gain=53 wb_G_gain=50 wb_B_gain=44 saturation=40 contrast=70
```

The grey card alone gave blue 22, which made the picture look yellow. Blue went up until the yellow was gone, saturation went down because the reds were too strong, and contrast went up because the picture looked washed out.

## Validating the result

Checking by eye is subjective, and a grey card only checks white balance. To measure how true the colours are:

1. Photograph a colour chart with published reference values (for example a Datacolor SpyderCheckr 24 or a Calibrite ColorChecker Classic) under the real light.
2. Measure each patch with `measure`.
3. Compare each patch with its reference using ΔE2000: below 2 is hard to see, 2–5 is visible side by side, above 5 is clearly off.
4. Check the grey steps: the dark ones shouldn't merge into black, nor the light ones into white.

## Development

```sh
.venv/bin/pip install -e '.[dev]'
.venv/bin/ruff format --check . && .venv/bin/ruff check . && .venv/bin/mypy src tests && .venv/bin/pytest
```

The tests use a fake camera whose picture follows its white balance gains, and real ffmpeg. `tapo.py`, the pytapo adapter, needs a real camera, so it is left out of the coverage target.

## Licence

MIT
