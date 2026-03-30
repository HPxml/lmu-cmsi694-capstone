# Sprint 4: ML Foundation & Data Collection

This sprint adds dataset collection, event logging, and ROI calibration support while keeping the core functionality intact.

## Sprint 4 Goal
Build an ML-ready foundation by collecting labeled gesture samples (CSV), validating dataset quality, adding event logging, and adding ROI calibration so demos and training are reliable and repeatable.

## Key Changes
1. **Event Logging**: Logs application events into `events/events_log.csv`.
2. **Dataset Collection**: Records gesture landmark rows into `data/samples.csv` only when wrist is inside ROI and the detected gesture matches the selected label.
3. **Dataset Validation**: `dataset/validate_dataset.py` verifies dataset format and prints PASS/FAIL.
4. **ROI Calibration**: Move/resize ROI and persist it to `config/roi.json`.

## Keybindings & Controls
### Core Controls
- `Z` : Toggle LOCK/UNLOCK (prevents accidental triggers)
- `Q` : Quit

### ROI Calibration (Move / Resize)
- **Move ROI**: `W/A/S/D` or Arrow Keys
- **Resize ROI**:
  - Width: `J/L`
  - Height: `I/K`
  - Expand/Shrink: `+/-`
- `P` : Save ROI to `config/roi.json`

### Data Collection (writes to `data/samples.csv`)
- `R` : Toggle Recording ON/OFF
- `1` : Label = `open_palm` (Open Palm triggers Play/Pause → presses `k`)
- `2` : Label = `fist` (Idle)
- `3` : Label = `two_fingers` (Two Fingers triggers Skip Forward 10s → presses `l`)

## Optional: Train Your Own Model (Sprint 5 Prep)
```powershell
pip install pandas scikit-learn
python train_model.py
```

## Run Steps (PowerShell)
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

## How to use the Validator
After collecting gesture samples with `1/2/3` and `R`, validate your `data/samples.csv`:
```powershell
.\.venv\Scripts\python.exe dataset/validate_dataset.py
```

## Demo Checklist
- [ ] Environment is running Python 3.12 and strictly `mediapipe==0.10.14`.
- [ ] Application starts successfully and `events/events_log.csv` populates on lock/unlock.
- [ ] Lighting is adequate, and your whole hand fits comfortably in the green ROI box.
- [ ] Press `P` after moving/resizing the box and ensure the `Saved ✅` UI appears. Restart application to verify config is loaded.
- [ ] Collect samples by selecting labels `1` / `2` / `3` and toggling `R`.
- [ ] Ensure Open Palm triggers Play/Pause (presses k) and Two Fingers triggers Skip Forward 10s (presses l).
- [ ] Close app (`Q`) and run `dataset/validate_dataset.py` to see `PASS: Dataset looks valid ✅`.
