# Gesture Control System - Sprint 6 (FINAL SPRINT) 🚀

Welcome to the finalized **Gesture Control System**, created for our Capstone Demo. This represents the completion of Sprint 6, serving as the **Final Sprint** of the project.

This application provides a professional, side-by-side presentation-ready gesture control system specifically designed to operate YouTube and other media players without touching the keyboard. It leverages OpenCV, MediaPipe, and Scikit-Learn.

## 🎯 Final Sprint Goals Achieved
- **Capstone Demo Ready**: Polished, professional UI/HUD designed specifically for live demonstrations. 
- **Physiological Math Overrides**: High-reliability rule-based detection for "Open Palm" (Play/Pause), "Two Fingers", "Fist", "Thumbs Up", and "Thumbs Down".
- **ML Inference Fallback**: Machine Learning model fallback for ambiguous gestures, utilizing our previously trained model.
- **Robust Auto-Pause**: Application monitors facial landmarks. If you fall asleep or close your eyes (EAR tracking), an automatic pause command (`k`) is sent.
- **Lock/Unlock Safety System**: Built-in toggle to prevent accidental triggers.

## ⌨️ Gestures & Actions Map
Ensure your hand is fully within the ROI (Region of Interest) box.
- ✋ **Open Palm**: Play / Pause (presses `k`)
- ✌️ **Two Fingers**: Skip Forward 10s (presses `l`)
- ✊ **Fist**: Skip Backward 10s (presses `j`)
- 👍 **Thumbs Up**: Volume Up (presses `up`)
- 👎 **Thumbs Down**: Volume Down (presses `down`)

### Core Application Controls
- `Z` : Toggle LOCK/UNLOCK (System starts locked)
- `Q` : Quit Demo

## 🔌 Setup & Run Instructions (Windows / PowerShell)

1. **Initialize Virtual Environment & Install Dependencies:**
   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Run the Capstone Demo:**
   ```powershell
   python main.py
   ```

## 🎥 Demo Checklist
- [ ] Environment is running Python 3.12 and strictly `mediapipe==0.10.14`.
- [ ] Ensure lighting is adequate and your entire hand fits comfortably inside the ROI box.
- [ ] Check that `models/gesture_model.pkl` is present for ML fallback functionality.
- [ ] Press `Z` to UNLOCK the system before gesturing.
- [ ] Test the sleepy auto-pause: close your eyes for 3+ seconds to see it trigger an auto-pause.
