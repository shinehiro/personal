# Image detection bot

A customizable Python bot that detects on-screen objects on screen using image recognition and performs automated mouse clicks and keyboard inputs to interact with them.

## Features

- 🧠 **Template Matching** using OpenCV for element detection  
- 🎯 **Custom Click Offsets** and key spamming for actions  
- 🎥 **Visual Feedback** with bounding boxes and debug information  
- 🛠️ **Calibration Mode** for precise click targeting  
- 💾 **Configurable Settings** saved to `bot_config.json`  
- 🧪 **Gaussian Blur** support for improved detection accuracy  
- ⌨️ **Hotkeys** for pausing (`F9`) and stopping (`ESC`) the bot  

## Requirements

- Python 3.x  
- Libraries:
  - `pyautogui`
  - `opencv-python`
  - `numpy`
  - `pillow`
  - `keyboard`

Install dependencies using:

```bash
pip install pyautogui opencv-python numpy pillow keyboard
```

## Setup

1. Place your preferred images (templates) in the `monster_templates/` directory.  
2. Run the script:

```bash
python image\ detection.py
```

3. Press `F9` to pause/resume, or `ESC` to stop the bot.

## Configuration

Settings can be adjusted by editing `bot_config.json` or directly in the script under the `Config` class.

Key options include:

- `CONFIDENCE_THRESHOLD`
- `KEY_SEQUENCE`
- `CLICK_OFFSET_X`, `CLICK_OFFSET_Y`
- `SCAN_REGION`
- `CALIBRATION_MODE`

## Calibration Mode

Use `CALIBRATION_MODE = True` in the configuration to fine-tune click positions. When a monster is detected, you can press `'c'` to capture a new click offset based on your mouse's current position.

## Logging

All actions and errors are logged in `bot_activity.log` for review.
