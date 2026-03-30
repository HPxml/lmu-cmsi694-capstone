import time
import sys
import math
import os
import json
import csv
from datetime import datetime
from dataclasses import dataclass
import cv2
import mediapipe as mp
import pyautogui
import pickle

# Create necessary directories for Sprint 4 features
os.makedirs("data", exist_ok=True)
os.makedirs("events", exist_ok=True)
os.makedirs("config", exist_ok=True)
os.makedirs("dataset", exist_ok=True)

# Optional: Try to import pygetwindow for auto-focus, but don't crash if missing
try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except ImportError:
    HAS_PYGETWINDOW = False

<<<<<<< Updated upstream
def log_event(event_type, detail):
    pass # Deprecated, use log_state_event inside main()

@dataclass
class Config:
    camera_index: int = 0
    
    # ROI (interaction zone) in pixels
    roi_x1: int = 160
    roi_y1: int = 80
    roi_x2: int = 480
    roi_y2: int = 400
    
    # Reliability Settings
    cooldown_sec: float = 1.5           # Time between triggers
    persistence_threshold: int = 10     # Frames to hold gesture (~0.3s @ 30fps)
    absence_timeout_sec: float = 3.0    # Auto-pause absence timeout
    sleepiness_timeout_sec: float = 3.0 # Auto-pause sleepiness timeout
    ear_threshold: float = 0.20         # Eye Aspect Ratio threshold (below this is 'closed')
    
    min_detection_confidence: float = 0.6
    min_tracking_confidence: float = 0.6

    def load_roi(self):
        path = "config/roi.json"
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
                self.roi_x1 = data.get("roi_x1", self.roi_x1)
                self.roi_y1 = data.get("roi_y1", self.roi_y1)
                self.roi_x2 = data.get("roi_x2", self.roi_x2)
                self.roi_y2 = data.get("roi_y2", self.roi_y2)
                
    def save_roi(self):
        path = "config/roi.json"
        with open(path, "w") as f:
            json.dump({
                "roi_x1": self.roi_x1,
                "roi_y1": self.roi_y1,
                "roi_x2": self.roi_x2,
                "roi_y2": self.roi_y2
            }, f)
        print("ROI saved to config/roi.json")
=======
@dataclass
class Config:
    camera_index: int = 0
    
    # ROI (interaction zone) in pixels
    roi_x1: int = 160
    roi_y1: int = 80
    roi_x2: int = 480
    roi_y2: int = 400
    
    # Reliability Settings
    cooldown_sec: float = 1.5           # Time between triggers
    persistence_threshold: int = 10     # Frames to hold gesture (~0.3s @ 30fps)
    absence_timeout_sec: float = 3.0    # Auto-pause absence timeout
    sleepiness_timeout_sec: float = 3.0 # Auto-pause sleepiness timeout
    ear_threshold: float = 0.20         # Eye Aspect Ratio threshold (below this is 'closed')
    
    min_detection_confidence: float = 0.6
    min_tracking_confidence: float = 0.6
>>>>>>> Stashed changes


# Face Mesh Indices for Eyes (P1..P6)
LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]


def calculate_ear(face_landmarks, eye_indices, w, h):
    """Calculates the Eye Aspect Ratio (EAR) given Face Mesh landmarks."""
    pts = []
    for idx in eye_indices:
        lm = face_landmarks.landmark[idx]
        pts.append((lm.x * w, lm.y * h))
        
    def dist(p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])
<<<<<<< Updated upstream
        
=======
>>>>>>> Stashed changes
    # Vertical distances
    v1 = dist(pts[1], pts[5])
    v2 = dist(pts[2], pts[4])
    # Horizontal distance
    h1 = dist(pts[0], pts[3])
    
    return (v1 + v2) / (2.0 * h1) if h1 > 0 else 0.0


def print_startup_checklist():
    print("="*60)
    print("      GESTURE YOUTUBE CONTROL - SPRINT 4      ")
    print("="*60)
    print("CHECKLIST FOR RELIABILITY:")
    print("1. LIGHTING: Ensure you are well-lit (face light source).")
    print("2. BACKGROUND: Avoid busy backgrounds or backlighting.")
    print("3. BROWSER: Open YouTube in Chrome/Edge.")
    print("4. FOCUS: Click inside the video player to ensure it has focus.")
    print("5. POSITION: Place this window so it doesn't cover the video.")
    print("-" * 60)
    print("CONTROLS:")
    print("  [Z] Toggle LOCK/UNLOCK (prevent accidental triggers)")
    print("  [R] Toggle Recording (Data Collection)")
    print("  [1/2/3] Change Label ('open_palm', 'fist', 'two_fingers')")
    print("  [W/A/S/D] Move ROI Box")
    print("  [J/L] Decrease/Increase ROI Width")
    print("  [I/K] Decrease/Increase ROI Height")
    print("  [P] Save ROI settings to config")
    print("  [Q] Quit Application")
    print("="*60)
    print("Starting camera...")


def put_text_hud(frame, text, x, y, color=(255, 255, 255), scale=0.7, thickness=2):
    """Draws text with a black outline for visibility."""
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def focus_browser():
    """Attempt to focus a browser window if pygetwindow is available."""
    if not HAS_PYGETWINDOW:
        return False
    
    keywords = ["YouTube", "Chrome", "Edge", "Firefox"]
    try:
        active = gw.getActiveWindow()
        if active and any(k.lower() in active.title.lower() for k in keywords):
            return True
            
        all_titles = gw.getAllTitles()
        for t in all_titles:
            if any(k.lower() in t.lower() for k in keywords):
                win = gw.getWindowsWithTitle(t)[0]
                if not win.isActive:
                    win.activate()
                return True
    except Exception:
        pass
    return False

def is_fist(hand_landmarks) -> bool:
    """Returns True if all 4 main fingers are folded."""
    lm = hand_landmarks.landmark
    mp_hands = mp.solutions.hands
    index_folded = lm[mp_hands.HandLandmark.INDEX_FINGER_TIP].y > lm[mp_hands.HandLandmark.INDEX_FINGER_PIP].y
    middle_folded = lm[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y > lm[mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y
    ring_folded = lm[mp_hands.HandLandmark.RING_FINGER_TIP].y > lm[mp_hands.HandLandmark.RING_FINGER_PIP].y
    pinky_folded = lm[mp_hands.HandLandmark.PINKY_TIP].y > lm[mp_hands.HandLandmark.PINKY_PIP].y
    return index_folded and middle_folded and ring_folded and pinky_folded


def is_open_palm(hand_landmarks) -> bool:
    """Returns True if the 4 main fingers are fully extended (thumb is ignored)."""
    lm = hand_landmarks.landmark
    mp_hands = mp.solutions.hands
    
    # Extended condition: tip.y < pip.y
    # NOT folded for Ring/Pinky: tip.y < pip.y
    
    index_ext = lm[mp_hands.HandLandmark.INDEX_FINGER_TIP].y < lm[mp_hands.HandLandmark.INDEX_FINGER_PIP].y
    middle_ext = lm[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y < lm[mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y
    ring_ext = lm[mp_hands.HandLandmark.RING_FINGER_TIP].y < lm[mp_hands.HandLandmark.RING_FINGER_PIP].y
    pinky_ext = lm[mp_hands.HandLandmark.PINKY_TIP].y < lm[mp_hands.HandLandmark.PINKY_PIP].y
            
    return index_ext and middle_ext and ring_ext and pinky_ext


def is_two_fingers(hand_landmarks) -> bool:
    """Returns True if exclusively Index and Middle fingers are extended."""
    lm = hand_landmarks.landmark
    mp_hands = mp.solutions.hands
    
    # Require index + middle extended strongly
    index_ext = lm[mp_hands.HandLandmark.INDEX_FINGER_TIP].y < lm[mp_hands.HandLandmark.INDEX_FINGER_PIP].y - 0.02
    middle_ext = lm[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y < lm[mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y - 0.02
    
    # Require ring + pinky folded strongly
    ring_folded = lm[mp_hands.HandLandmark.RING_FINGER_TIP].y > lm[mp_hands.HandLandmark.RING_FINGER_PIP].y + 0.02
    pinky_folded = lm[mp_hands.HandLandmark.PINKY_TIP].y > lm[mp_hands.HandLandmark.PINKY_PIP].y + 0.02
    
    return index_ext and middle_ext and ring_folded and pinky_folded


def load_csv_counts():
    file_path = "data/samples.csv"
    counts = {"open_palm": 0, "fist": 0, "two_fingers": 0}
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                for row in reader:
                    if len(row) > 1:
                        lbl = row[1].strip()
                        counts[lbl] = counts.get(lbl, 0) + 1
        except Exception:
            pass
    return counts


<<<<<<< Updated upstream
=======
def main():
    print_startup_checklist()
    cfg = Config()
    cfg.load_roi() # Load saved ROI from Sprint 4
    
    # ML Model Persistence Integration
    ml_model = None
    label_encoder = None
    try:
        model_path = "models/gesture_model.pkl"
        if os.path.exists(model_path):
            with open(model_path, "rb") as f:
                data = pickle.load(f)
                ml_model = data["model"]
                label_encoder = data["label_encoder"]
            print(f"Loaded ML model! Classes: {label_encoder.classes_}")
        else:
            print("No ML model found in models/ - Falling back to math calculations.")
    except Exception as e:
        print(f"Failed to load ML model (do you have scikit-learn installed?): {e}")

    mp_hands = mp.solutions.hands
    mp_face_mesh = mp.solutions.face_mesh
    mp_drawing = mp.solutions.drawing_utils

    try:
        cap = cv2.VideoCapture(cfg.camera_index)
        if not cap.isOpened():
            print("ERROR: Could not open webcam.")
            return

        # State Variables
        last_trigger_time = 0.0
        persistence_counter = 0
        two_fingers_counter = 0
        is_locked = True  # Start locked for safety
        
        last_hand_seen_time = time.time()
        last_eyes_open_time = time.time() 
        saved_until = 0.0
        
        auto_pause_fired = False
        prev_frame_time = time.time()
        
        # Sprint 4: Data Gathering State
        is_recording = False
        current_label = "open_palm"
        sample_count = 0
        dataset_counts = load_csv_counts()
        
        # Track timers for 1.5s sticky HUD messages
        last_action_time = 0.0
        last_status_override_time = 0.0
        override_status_msg = ""
        
        status_msg = "LOCKED"
        action_msg = "None"
        gesture_msg = "None"
        eyes_msg = "Eyes Open"
        current_pred_confidence = "N/A"
        
        hand_detected = False

        # Event throttle timers
        last_roi_adjust_time = 0.0
        skipped_warning_until = 0.0
        
        def log_state_event(evt_type, current_fps):
            log_file = "events/events_log.csv"
            file_exists = os.path.exists(log_file)
            with open(log_file, "a", newline="") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["timestamp", "event_type", "label_mode", "gesture_detected", "action_sent", "lock_state", "roi_coords", "fps"])
                writer.writerow([
                    datetime.now().isoformat(), 
                    evt_type, 
                    current_label, 
                    f"{gesture_msg} | {current_pred_confidence}", 
                    action_msg, 
                    is_locked, 
                    f"({cfg.roi_x1},{cfg.roi_y1},{cfg.roi_x2},{cfg.roi_y2})", 
                    f"{int(current_fps)}"
                ])

        log_state_event("STARTUP", 0)

        with mp_hands.Hands(
            model_complexity=0,
            min_detection_confidence=cfg.min_detection_confidence,
            min_tracking_confidence=cfg.min_tracking_confidence,
            max_num_hands=1
        ) as hands, mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=cfg.min_detection_confidence,
            min_tracking_confidence=cfg.min_tracking_confidence
        ) as face_mesh:
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("ERROR: Lost connection to webcam.")
                    break
                    
                frame = cv2.flip(frame, 1)
                h, w, _ = frame.shape
                
                # FPS Calculation
                current_time = time.time()
                fps = 1 / (current_time - prev_frame_time) if current_time > prev_frame_time else 0
                prev_frame_time = current_time
                
                # Draw ROI
                cv2.rectangle(frame, (cfg.roi_x1, cfg.roi_y1), (cfg.roi_x2, cfg.roi_y2), (0, 255, 0), 2)
                
                # Process Frame for Hand & Face
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                results_hands = hands.process(rgb)
                hand_in_roi = False
                detected_open_palm = False
                detected_two_fingers = False
                detected_fist = False

                raw_two_fingers = False
                raw_open_palm = False
                raw_fist = False
                final_label_frame = "Unknown"
                
                if results_hands.multi_hand_landmarks:
                    hand_detected = True
                    last_hand_seen_time = current_time
                    
                    # Sprint 4 constraint: Only taking the first hand for data gathering
                    first_hand_landmarks = results_hands.multi_hand_landmarks[0]
                    mp_drawing.draw_landmarks(frame, first_hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    
                    # Check if Wrist is inside ROI
                    wrist = first_hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                    wx, wy = int(wrist.x * w), int(wrist.y * h)
                    
                    if cfg.roi_x1 < wx < cfg.roi_x2 and cfg.roi_y1 < wy < cfg.roi_y2:
                        hand_in_roi = True
                        
                        lm_list = []
                        for lm in first_hand_landmarks.landmark:
                            lm_list.extend([lm.x, lm.y, lm.z])
                            
                        # Machine Learning Inference (Sprint 4 / Sprint 5 Bridge)
                        inference_label = "Unknown"
                        if ml_model is not None:
                            try:
                                probs = ml_model.predict_proba([lm_list])[0]
                                max_prob = max(probs)
                                # Strict confidence threshold (reduce false triggers)
                                if max_prob >= 0.75:  
                                    inference_label = label_encoder.inverse_transform([probs.argmax()])[0]
                                
                                current_pred_confidence = f"{max_prob*100:.1f}% ({inference_label})"
                            except Exception:
                                pass # Catch any sklearn mismatch temporarily
                        
                        # ALWAYS compute raw math detections for Sprint 4 evaluation
                        raw_two_fingers = is_two_fingers(first_hand_landmarks)
                        raw_open_palm = is_open_palm(first_hand_landmarks)
                        raw_fist = is_fist(first_hand_landmarks)
                        
                        # Apply strict exclusivity and priority rules
                        # Priority: 1. two_fingers, 2. open_palm, 3. fist
                        overlap_count = sum([raw_two_fingers, raw_open_palm, raw_fist])
                        
                        if overlap_count > 1:
                            final_label_frame = "Unknown"
                        elif raw_two_fingers:
                            final_label_frame = "two_fingers"
                        elif raw_open_palm:
                            final_label_frame = "open_palm"
                        elif raw_fist:
                            final_label_frame = "fist"
                        else:
                            final_label_frame = "Unknown"
                        
                        # Force detected variables to strictly match final label
                        detected_two_fingers = (final_label_frame == "two_fingers")
                        detected_open_palm = (final_label_frame == "open_palm")
                        detected_fist = (final_label_frame == "fist")

                    # DATA GATHERING (SPRINT 4)
                    if is_recording:
                        if hand_in_roi:
                            is_match = False
                            if current_label == "open_palm" and detected_open_palm: is_match = True
                            elif current_label == "two_fingers" and detected_two_fingers: is_match = True
                            elif current_label == "fist" and detected_fist: is_match = True
                            
                            if is_match:
                                file_path = "data/samples.csv"
                                file_exists = os.path.exists(file_path)
                                with open(file_path, "a", newline="") as f:
                                    writer = csv.writer(f)
                                    if not file_exists:
                                        headers = ["timestamp", "label"]
                                        for i in range(21):
                                            headers.extend([f"x{i}", f"y{i}", f"z{i}"])
                                        writer.writerow(headers)
                                    
                                    row = [datetime.now().isoformat(), current_label] + lm_list
                                    writer.writerow(row)
                                    sample_count += 1
                                    dataset_counts[current_label] = dataset_counts.get(current_label, 0) + 1
                                
                                if sample_count % 30 == 0:
                                    print(f"Saved sample to data/samples.csv (label={current_label}, rows={sample_count})")
                        else:
                            skipped_warning_until = current_time + 1.0

                else:
                    hand_detected = False
                    
                # 2. Process Face for Sleepiness (EAR)
                results_face = face_mesh.process(rgb)
                eyes_closed_detected = False
                
                if results_face.multi_face_landmarks:
                    for face_landmarks in results_face.multi_face_landmarks:
                        left_ear = calculate_ear(face_landmarks, LEFT_EYE_INDICES, w, h)
                        right_ear = calculate_ear(face_landmarks, RIGHT_EYE_INDICES, w, h)
                        avg_ear = (left_ear + right_ear) / 2.0
                        
                        if avg_ear < cfg.ear_threshold:
                            eyes_closed_detected = True
                            eyes_msg = f"Eyes Closed (EAR: {avg_ear:.2f})"
                        else:
                            last_eyes_open_time = current_time
                            eyes_msg = f"Eyes Open (EAR: {avg_ear:.2f})"
                else:
                    last_eyes_open_time = current_time
                    eyes_msg = "No Face"
                
                if hand_detected and not eyes_closed_detected:
                    auto_pause_fired = False

                time_since_trigger = current_time - last_trigger_time
                time_since_hand = current_time - last_hand_seen_time
                time_since_eyes_open = current_time - last_eyes_open_time
                fist_counter = 0 # Future expansion
                
                if hand_detected and final_label_frame != "Unknown":
                    if hand_in_roi and final_label_frame == "two_fingers":
                        two_fingers_counter += 1
                        persistence_counter = 0
                        display_count = min(two_fingers_counter, cfg.persistence_threshold)
                        gesture_msg = f"Two Fingers ({display_count}/{cfg.persistence_threshold})"
                    elif hand_in_roi and final_label_frame == "open_palm":
                        persistence_counter += 1
                        two_fingers_counter = 0
                        display_count = min(persistence_counter, cfg.persistence_threshold)
                        gesture_msg = f"Open Palm ({display_count}/{cfg.persistence_threshold})"
                    elif hand_in_roi and final_label_frame == "fist":
                        fist_counter += 1
                        persistence_counter = 0
                        two_fingers_counter = 0
                        gesture_msg = "Fist (Idle)"
                    else:
                        persistence_counter = 0
                        two_fingers_counter = 0
                        if hand_in_roi:
                            gesture_msg = "Hand in ROI (no matched gesture)"
                        else:
                            gesture_msg = "Move hand into ROI"
                else:
                    persistence_counter = 0
                    two_fingers_counter = 0
                    if not hand_detected:
                        gesture_msg = "No hand detected"
                        current_pred_confidence = "N/A"
                    else:
                        gesture_msg = "Ambiguous/Unknown Gesture"

                if persistence_counter >= cfg.persistence_threshold or two_fingers_counter >= cfg.persistence_threshold:
                    if is_locked:
                        status_msg = "LOCKED (Press Z)"
                    elif time_since_trigger < cfg.cooldown_sec:
                        status_msg = f"Cooldown ({int(cfg.cooldown_sec - time_since_trigger)})"
                    else:
                        focus_browser() 
                        
                        if persistence_counter >= cfg.persistence_threshold:
                            pyautogui.press("k")
                            action_msg = "PLAY/PAUSE SENT ('k')"
                        elif two_fingers_counter >= cfg.persistence_threshold:
                            pyautogui.press("l")
                            action_msg = "SKIP FWD 10s ('l')"
                        
                        status_msg = "TRIGGERED!"
                        last_trigger_time = current_time
                        persistence_counter = 0 
                        two_fingers_counter = 0
                        
                        last_action_time = current_time
                        last_status_override_time = current_time
                        override_status_msg = "TRIGGERED!"
                        log_state_event("ACTION_SENT", fps)
                        
                elif not is_locked:
                    if time_since_hand > cfg.absence_timeout_sec:
                        if not auto_pause_fired:
                            focus_browser()
                            pyautogui.press("k")
                            action_msg = "AUTO-PAUSE SENT"
                            auto_pause_fired = True
                            
                            last_action_time = current_time
                            last_status_override_time = current_time
                            override_status_msg = "AUTO-PAUSED (Absent)"
                            log_state_event("ACTION_SENT", fps)
                        status_msg = "READY"
                    elif time_since_eyes_open > cfg.sleepiness_timeout_sec:
                        if not auto_pause_fired:
                            focus_browser()
                            pyautogui.press("k")
                            action_msg = "AUTO-PAUSE SENT"
                            auto_pause_fired = True
                            
                            last_action_time = current_time
                            last_status_override_time = current_time
                            override_status_msg = "AUTO-PAUSED (Sleepy)"
                            log_state_event("ACTION_SENT", fps)
                        status_msg = "READY"
                    elif not hand_detected:
                        countdown = max(0.0, cfg.absence_timeout_sec - time_since_hand)
                        status_msg = f"Absent in {countdown:.1f}s"
                    elif eyes_closed_detected:
                        countdown = max(0.0, cfg.sleepiness_timeout_sec - time_since_eyes_open)
                        status_msg = f"Sleepy in {countdown:.1f}s"
                    else:
                        status_msg = "READY"
                else:
                    if not hand_detected or eyes_closed_detected:
                        status_msg = "LOCKED (No auto-pause)"
                    else:
                        status_msg = "LOCKED"

                if not is_locked and (current_time - last_status_override_time < 1.5):
                    status_msg = override_status_msg
                if current_time - last_action_time > 1.5:
                    action_msg = "None"

                # Sprint 4 HUD Additions
                if is_recording:
                    put_text_hud(frame, f"REC [{current_label}] (Press R to stop)", 20, 30, color=(0, 0, 255))
                else:
                    put_text_hud(frame, f"Label: {current_label} (Press 1/2/3 to change, R to record)", 20, 30, color=(0, 200, 200))

                put_text_hud(frame, f"ROI: ({cfg.roi_x1},{cfg.roi_y1}) to ({cfg.roi_x2},{cfg.roi_y2})", 20, 60, scale=0.5)
                put_text_hud(frame, f"FPS: {int(fps)}", w - 100, 30, scale=0.6)
                
                if current_time < saved_until:
                    put_text_hud(frame, "Saved ✅", w - 100, 60, color=(0, 255, 0), scale=0.6)
                if current_time < skipped_warning_until:
                    put_text_hud(frame, "Skipped (not in ROI)", 20, 110, color=(0, 0, 255), scale=0.6, thickness=2)

                # Balanced Dataset Helper
                total_samples = sum(dataset_counts.values())
                y_offset = 90
                put_text_hud(frame, f"DATASET (Total: {total_samples})", 20, y_offset, scale=0.5, color=(200, 200, 200))
                y_offset += 20
                for lbl in ["open_palm", "fist", "two_fingers"]:
                    cnt = dataset_counts.get(lbl, 0)
                    pct = (cnt / total_samples * 100) if total_samples > 0 else 0
                    warn_color = (0, 0, 255) if pct > 60 and total_samples > 50 else (0, 255, 0)
                    active_marker = ">" if lbl == current_label else " "
                    txt = f"{active_marker} {lbl}: {cnt} ({pct:.1f}%)"
                    if pct > 60 and total_samples > 50:
                        txt += " [WARNING: >60%]"
                    put_text_hud(frame, txt, 20, y_offset, scale=0.5, color=warn_color)
                    y_offset += 20
                
                # Bottom Left Info
                start_y = h - 30
                line_height = 30
                
                lock_text = "LOCKED" if is_locked else "UNLOCKED"
                put_text_hud(frame, f"STATUS: {lock_text} | [Q] Quit  [Z] Toggle Lock", 20, start_y, scale=0.6, color=(0, 0, 255) if is_locked else (0, 255, 0))
                put_text_hud(frame, f"ACTION:  {action_msg}", 20, start_y - line_height, color=(255, 100, 100))
                put_text_hud(frame, f"GESTURE: {gesture_msg} | ML: {current_pred_confidence}", 20, start_y - 2*line_height, scale=0.6)
                put_text_hud(frame, f"EYES:    {eyes_msg}", 20, start_y - 3*line_height, scale=0.6)
                
                # Debug HUD for raw thresholds
                if hand_detected:
                    debug_str = f"RAW DETECTION: open_palm={raw_open_palm}, two_fingers={raw_two_fingers}, fist={raw_fist} | FINAL: {final_label_frame}"
                    put_text_hud(frame, debug_str, 20, start_y - 4*line_height, scale=0.5, color=(0,255,255))
                
                cv2.imshow("Gesture Control (Sprint 4)", frame)

                # Snapshot old ROI to track actual mutations
                old_roi = (cfg.roi_x1, cfg.roi_y1, cfg.roi_x2, cfg.roi_y2)

                # Input Handling (Sprint 4 Keyboard Layout)
                key = cv2.waitKeyEx(1)
                
                # Check for arrow keys (Windows keycodes mapping via waitKeyEx)
                if key == 2490368 or key == ord('w'): # UP
                    cfg.roi_y1 -= 10
                    cfg.roi_y2 -= 10
                elif key == 2621440 or key == ord('s'): # DOWN
                    cfg.roi_y1 += 10
                    cfg.roi_y2 += 10
                elif key == 2424832 or key == ord('a'): # LEFT
                    cfg.roi_x1 -= 10
                    cfg.roi_x2 -= 10
                elif key == 2555904 or key == ord('d'): # RIGHT
                    cfg.roi_x1 += 10
                    cfg.roi_x2 += 10
                    
                key_byte = key & 0xFF
                if key_byte == ord('q'):
                    break
                elif key_byte == ord('z'):
                    is_locked = not is_locked
                    log_state_event("LOCK_CHANGE", fps)
                    if is_locked:
                        status_msg = "LOCKED"
                        action_msg = "None"
                    else:
                        last_hand_seen_time = time.time()
                        last_eyes_open_time = time.time()
                        auto_pause_fired = False
                elif key_byte == ord('j'):
                    cfg.roi_x2 -= 10
                elif key_byte == ord('l'):
                    cfg.roi_x2 += 10
                elif key_byte == ord('i'):
                    cfg.roi_y2 -= 10
                elif key_byte == ord('k'):
                    cfg.roi_y2 += 10
                elif key_byte in [ord('+'), ord('=')]:
                    cfg.roi_x1 -= 10
                    cfg.roi_y1 -= 10
                    cfg.roi_x2 += 10
                    cfg.roi_y2 += 10
                elif key_byte == ord('-'):
                    cfg.roi_x1 += 10
                    cfg.roi_y1 += 10
                    cfg.roi_x2 -= 10
                    cfg.roi_y2 -= 10
                elif key_byte == ord('p'):
                    cfg.save_roi()
                    saved_until = current_time + 1.5
                    log_state_event("ROI_SAVE", fps)
                elif key_byte == ord('r'):
                    is_recording = not is_recording
                    log_state_event("RECORD_TOGGLE", fps)
                    if is_recording:
                        print(f"\n[+] Recording STARTED: Target -> data/samples.csv | Label -> {current_label}")
                    else:
                        print(f"[-] Recording STOPPED. Total samples saved: {sample_count}\n")
                elif key_byte == ord('1'):
                    if current_label != "open_palm":
                        current_label = "open_palm"
                        log_state_event("LABEL_CHANGE", fps)
                elif key_byte == ord('2'):
                    if current_label != "fist":
                        current_label = "fist"
                        log_state_event("LABEL_CHANGE", fps)
                elif key_byte == ord('3'):
                    if current_label != "two_fingers":
                        current_label = "two_fingers"
                        log_state_event("LABEL_CHANGE", fps)
                
                # Check for true ROI adjustment logging
                new_roi = (cfg.roi_x1, cfg.roi_y1, cfg.roi_x2, cfg.roi_y2)
                if new_roi != old_roi and current_time - last_roi_adjust_time > 0.5:
                    last_roi_adjust_time = current_time
                    log_state_event("ROI_ADJUST", fps)

                # Screen Clamping logic for ROI to prevent out-of-bounds crashes
                cfg.roi_x1 = max(0, cfg.roi_x1)
                cfg.roi_y1 = max(0, cfg.roi_y1)
                cfg.roi_x2 = min(w - 1, cfg.roi_x2)
                cfg.roi_y2 = min(h - 1, cfg.roi_y2)
                
                # Prevent inverse ROI sizes (x2 > x1, y2 > y1)
                if cfg.roi_x2 <= cfg.roi_x1:
                    cfg.roi_x2 = cfg.roi_x1 + 10
                if cfg.roi_y2 <= cfg.roi_y1:
                    cfg.roi_y2 = cfg.roi_y1 + 10
                    
                # Secondary safety clamp if minimum size pushes them out of bounds again
                cfg.roi_x2 = min(w - 1, cfg.roi_x2)
                if cfg.roi_x1 >= cfg.roi_x2:
                    cfg.roi_x1 = cfg.roi_x2 - 10
                cfg.roi_y2 = min(h - 1, cfg.roi_y2)
                if cfg.roi_y1 >= cfg.roi_y2:
                    cfg.roi_y1 = cfg.roi_y2 - 10

    except Exception as e:
        print(f"FATAL ERROR: An unexpected error occurred: {e}")
        
    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        cv2.destroyAllWindows()
        print("Application closed.")

>>>>>>> Stashed changes
if __name__ == "__main__":
    main()
