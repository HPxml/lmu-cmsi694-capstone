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

# Create necessary directories
os.makedirs("config", exist_ok=True)
os.makedirs("events", exist_ok=True)

try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except ImportError:
    HAS_PYGETWINDOW = False

@dataclass
class Config:
    camera_index: int = 0
    roi_x1: int = 160
    roi_y1: int = 80
    roi_x2: int = 480
    roi_y2: int = 400
    
    cooldown_sec: float = 1.5           
    persistence_threshold: int = 6      # For demo responsiveness
    sleepiness_timeout_sec: float = 3.0 
    ear_threshold: float = 0.23         
    
    min_detection_confidence: float = 0.75
    min_tracking_confidence: float = 0.75
    actions: dict = None

    def load_roi(self):
        path = "config/roi.json"
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
                self.roi_x1 = data.get("roi_x1", self.roi_x1)
                self.roi_y1 = data.get("roi_y1", self.roi_y1)
                self.roi_x2 = data.get("roi_x2", self.roi_x2)
                self.roi_y2 = data.get("roi_y2", self.roi_y2)

    def load_actions(self):
        path = "config/actions.json"
        if os.path.exists(path):
            with open(path, "r") as f:
                self.actions = json.load(f)
        else:
            self.actions = {
                "open_palm": "k",
                "two_fingers": "l",
                "fist": "j",
                "thumbs_up": "up",
                "thumbs_down": "down"
            }

LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]

def calculate_ear(face_landmarks, eye_indices, w, h):
    pts = []
    for idx in eye_indices:
        lm = face_landmarks.landmark[idx]
        pts.append((lm.x * w, lm.y * h))
        
    def dist(p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])
        
    v1 = dist(pts[1], pts[5])
    v2 = dist(pts[2], pts[4])
    h1 = dist(pts[0], pts[3])
    
    return (v1 + v2) / (2.0 * h1) if h1 > 0 else 0.0

def focus_browser():
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

def get_folded_states(hand_landmarks):
    lm = hand_landmarks.landmark
    mp_hands = mp.solutions.hands
    wrist = lm[mp_hands.HandLandmark.WRIST]

    def dist_from_wrist(point):
        return math.hypot(point.x - wrist.x, point.y - wrist.y)

    def check_finger(tip_idx, pip_idx, mcp_idx):
        tip = lm[tip_idx]
        pip = lm[pip_idx]
        mcp = lm[mcp_idx]

        tip_d = dist_from_wrist(tip)
        pip_d = dist_from_wrist(pip)
        mcp_d = dist_from_wrist(mcp)

        is_extended = tip_d > pip_d and tip_d > mcp_d + 0.015
        is_folded = tip_d < pip_d - 0.005
        return is_extended, is_folded

    i_ext, i_fold = check_finger(
        mp_hands.HandLandmark.INDEX_FINGER_TIP,
        mp_hands.HandLandmark.INDEX_FINGER_PIP,
        mp_hands.HandLandmark.INDEX_FINGER_MCP,
    )
    m_ext, m_fold = check_finger(
        mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_PIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_MCP,
    )
    r_ext, r_fold = check_finger(
        mp_hands.HandLandmark.RING_FINGER_TIP,
        mp_hands.HandLandmark.RING_FINGER_PIP,
        mp_hands.HandLandmark.RING_FINGER_MCP,
    )
    p_ext, p_fold = check_finger(
        mp_hands.HandLandmark.PINKY_TIP,
        mp_hands.HandLandmark.PINKY_PIP,
        mp_hands.HandLandmark.PINKY_MCP,
    )

    return (i_ext, m_ext, r_ext, p_ext), (i_fold, m_fold, r_fold, p_fold)

def is_fist(hand_landmarks) -> bool:
    lm = hand_landmarks.landmark
    mp_hands = mp.solutions.hands
    _, fold_states = get_folded_states(hand_landmarks)
    i_f, m_f, r_f, p_f = fold_states
    
    thumb_tip_x = lm[mp_hands.HandLandmark.THUMB_TIP].x
    index_mcp_x = lm[mp_hands.HandLandmark.INDEX_FINGER_MCP].x
    
    return i_f and m_f and r_f and p_f and abs(thumb_tip_x - index_mcp_x) < 0.15

def is_open_palm(hand_landmarks) -> bool:
    lm = hand_landmarks.landmark
    mp_hands = mp.solutions.hands
    wrist = lm[mp_hands.HandLandmark.WRIST]

    finger_pairs = [
        (mp_hands.HandLandmark.INDEX_FINGER_TIP, mp_hands.HandLandmark.INDEX_FINGER_MCP),
        (mp_hands.HandLandmark.MIDDLE_FINGER_TIP, mp_hands.HandLandmark.MIDDLE_FINGER_MCP),
        (mp_hands.HandLandmark.RING_FINGER_TIP, mp_hands.HandLandmark.RING_FINGER_MCP),
        (mp_hands.HandLandmark.PINKY_TIP, mp_hands.HandLandmark.PINKY_MCP),
    ]

    extended_count = 0
    for tip_idx, mcp_idx in finger_pairs:
        tip = lm[tip_idx]
        mcp = lm[mcp_idx]

        tip_dist = math.hypot(tip.x - wrist.x, tip.y - wrist.y)
        mcp_dist = math.hypot(mcp.x - wrist.x, mcp.y - wrist.y)

        if tip_dist > mcp_dist + 0.03:
            extended_count += 1

    index_tip = lm[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    pinky_tip = lm[mp_hands.HandLandmark.PINKY_TIP]
    spread = math.hypot(index_tip.x - pinky_tip.x, index_tip.y - pinky_tip.y)

    middle_tip = lm[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    middle_mcp = lm[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
    middle_extended = (
        math.hypot(middle_tip.x - wrist.x, middle_tip.y - wrist.y)
        > math.hypot(middle_mcp.x - wrist.x, middle_mcp.y - wrist.y) + 0.03
    )

    return extended_count >= 3 and spread > 0.09 and middle_extended

def is_two_fingers(hand_landmarks) -> bool:
    lm = hand_landmarks.landmark
    mp_hands = mp.solutions.hands
    ext_states, fold_states = get_folded_states(hand_landmarks)

    i_e, m_e, r_e, p_e = ext_states
    _, _, r_f, p_f = fold_states

    if is_open_palm(hand_landmarks):
        return False

    index_tip = lm[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_tip = lm[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    wrist = lm[mp_hands.HandLandmark.WRIST]

    index_up = math.hypot(index_tip.x - wrist.x, index_tip.y - wrist.y) > 0.18
    middle_up = math.hypot(middle_tip.x - wrist.x, middle_tip.y - wrist.y) > 0.18

    return i_e and m_e and index_up and middle_up and r_f and p_f and (not r_e) and (not p_e)

def is_thumbs_up(hand_landmarks) -> bool:
    lm = hand_landmarks.landmark
    mp_hands = mp.solutions.hands
    _, fold_states = get_folded_states(hand_landmarks)
    i_f, m_f, r_f, p_f = fold_states
    if not (i_f and m_f and r_f and p_f): return False
    
    thumb_tip_y = lm[mp_hands.HandLandmark.THUMB_TIP].y
    index_mcp_y = lm[mp_hands.HandLandmark.INDEX_FINGER_MCP].y
    
    return thumb_tip_y < index_mcp_y - 0.08

def is_thumbs_down(hand_landmarks) -> bool:
    lm = hand_landmarks.landmark
    mp_hands = mp.solutions.hands
    _, fold_states = get_folded_states(hand_landmarks)
    i_f, m_f, r_f, p_f = fold_states
    if not (i_f and m_f and r_f and p_f): return False
    
    thumb_tip_y = lm[mp_hands.HandLandmark.THUMB_TIP].y
    wrist_y = lm[mp_hands.HandLandmark.WRIST].y
    
    return thumb_tip_y > wrist_y + 0.08

def decide_demo_priority_gesture(hand_landmarks, ml_model, label_encoder, rel_lm_list):
    if is_open_palm(hand_landmarks):
        return "open_palm", "Priority (Open Palm)"

    if is_two_fingers(hand_landmarks):
        return "two_fingers", "Priority (Two Fingers)"

    if is_thumbs_up(hand_landmarks):
        return "thumbs_up", "Math (Thumbs Up)"

    if is_thumbs_down(hand_landmarks):
        return "thumbs_down", "Math (Thumbs Down)"

    if is_fist(hand_landmarks):
        return "fist", "Math (Fist)"

    if ml_model is not None and rel_lm_list is not None and label_encoder is not None:
        try:
            probs = ml_model.predict_proba([rel_lm_list])[0]
            sorted_probs = sorted(probs, reverse=True)
            predicted_label = label_encoder.inverse_transform([probs.argmax()])[0]
            max_prob = sorted_probs[0]

            if len(sorted_probs) >= 2 and (sorted_probs[0] - sorted_probs[1]) <= 0.08:
                return "Unknown", f"ML Ambiguous: {max_prob*100:.1f}%"

            if max_prob >= 0.75 and predicted_label not in ["open_palm", "two_fingers"]:
                return predicted_label, f"ML Conf: {max_prob*100:.1f}% ({predicted_label})"

        except Exception:
            pass

    return "Unknown", "N/A"

def put_text_hud(frame, text, x, y, color=(255, 255, 255), scale=0.7, thickness=2):
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)

def put_progress_bar(frame, x, y, width, height, progress, color=(0, 255, 0)):
    cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 0, 0), 2)
    cv2.rectangle(frame, (x, y), (x + width, y + height), (30, 30, 30), -1)
    if progress > 0:
        fill_width = int(width * progress)
        cv2.rectangle(frame, (x, y), (x + fill_width, y + height), color, -1)

GESTURE_COLORS = {
    "open_palm": (0, 255, 0),       # Green
    "two_fingers": (255, 200, 0),   # Cyan
    "fist": (0, 0, 255),            # Red
    "thumbs_up": (255, 0, 255),     # Magenta
    "thumbs_down": (0, 165, 255),   # Orange
    "Unknown": (150, 150, 150)      # Gray
}

def main():
    cfg = Config()
    cfg.load_roi()
    cfg.load_actions()
    
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
    except Exception as e:
        print(f"No ML model gracefully handled: {e}")

    mp_hands = mp.solutions.hands
    mp_face_mesh = mp.solutions.face_mesh
    mp_drawing = mp.solutions.drawing_utils

    cap = cv2.VideoCapture(cfg.camera_index)
    if not cap.isOpened():
        print("ERROR: Could not open webcam.")
        return
        
    cv2.namedWindow('Gesture Control Demo (Final)', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Gesture Control Demo (Final)', 420, 320)
    cv2.moveWindow('Gesture Control Demo (Final)', 20, 20)

    last_trigger_time = 0.0
    gesture_counters = {
        "open_palm": 0,
        "two_fingers": 0,
        "fist": 0,
        "thumbs_up": 0,
        "thumbs_down": 0
    }
    is_locked = True
    
    last_eyes_open_time = time.time() 
    
    auto_pause_fired = False
    prev_frame_time = time.time()
    
    last_action_time = 0.0
    last_status_override_time = 0.0
    override_status_msg = ""
    
    status_msg = "LOCKED"
    action_msg = "None"
    gesture_msg = "None"
    eyes_msg = "Eyes Open"
    current_pred_confidence = "N/A"
    
    hand_detected = False

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
            if not ret: break
                
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            
            current_time = time.time()
            fps = 1 / (current_time - prev_frame_time) if current_time > prev_frame_time else 0
            prev_frame_time = current_time
            
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results_hands = hands.process(rgb)
            hand_in_roi = False
            final_label_frame = "Unknown"
            
            current_pred_confidence = "N/A"
            
            if results_hands.multi_hand_landmarks:
                hand_detected = True
                
                first_hand_landmarks = results_hands.multi_hand_landmarks[0]
                mp_drawing.draw_landmarks(frame, first_hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                wrist = first_hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                wx, wy = int(wrist.x * w), int(wrist.y * h)
                
                if cfg.roi_x1 < wx < cfg.roi_x2 and cfg.roi_y1 < wy < cfg.roi_y2:
                    hand_in_roi = True
                    lm_list = []
                    for lm in first_hand_landmarks.landmark:
                        lm_list.extend([lm.x, lm.y, lm.z])
                        
                    rel_lm_list = None
                    if ml_model is not None:
                        try:
                            rel_lm_list = []
                            r_wx, r_wy, r_wz = lm_list[0], lm_list[1], lm_list[2]
                            for i in range(21):
                                rel_lm_list.extend([lm_list[i*3] - r_wx, lm_list[i*3+1] - r_wy, lm_list[i*3+2] - r_wz])
                        except Exception:
                            pass

                    inference_label, current_pred_confidence = decide_demo_priority_gesture(
                        first_hand_landmarks, ml_model, label_encoder, rel_lm_list
                    )
                    
                    final_label_frame = inference_label
            else:
                hand_detected = False
                
            results_face = face_mesh.process(rgb)
            eyes_closed_detected = False
            
            if results_face.multi_face_landmarks:
                for face_landmarks in results_face.multi_face_landmarks:
                    left_ear = calculate_ear(face_landmarks, LEFT_EYE_INDICES, w, h)
                    right_ear = calculate_ear(face_landmarks, RIGHT_EYE_INDICES, w, h)
                    avg_ear = (left_ear + right_ear) / 2.0
                    
                    if avg_ear < cfg.ear_threshold:
                        eyes_closed_detected = True
                        eyes_msg = "Closed"
                    else:
                        last_eyes_open_time = current_time
                        eyes_msg = "Open"
            else:
                last_eyes_open_time = current_time
                eyes_msg = "No Face"
            
            if not eyes_closed_detected:
                auto_pause_fired = False

            time_since_trigger = current_time - last_trigger_time
            time_since_eyes_open = current_time - last_eyes_open_time
            
            if hand_detected and final_label_frame != "Unknown":
                if hand_in_roi:
                    for g in gesture_counters:
                        if g == final_label_frame:
                            gesture_counters[g] += 1
                        else:
                            gesture_counters[g] = 0
                    gesture_msg = final_label_frame.replace("_", " ").title().strip()
                else:
                    for g in gesture_counters:
                        gesture_counters[g] = 0
                    gesture_msg = "Move hand to box"
                    current_pred_confidence = "N/A"
            else:
                for g in gesture_counters:
                    gesture_counters[g] = 0
                if not hand_detected:
                    gesture_msg = "No hand"
                    current_pred_confidence = "N/A"
                else:
                    gesture_msg = "Unknown"

            max_counter_gesture = max(gesture_counters, key=gesture_counters.get) if any(gesture_counters.values()) else None
            max_counter = gesture_counters[max_counter_gesture] if max_counter_gesture else 0

            progress_val = min(max_counter / float(cfg.persistence_threshold), 1.0)
            
            # --- ROI Box Rendering ---
            roi_color = (150, 150, 150) # Gray: no hand
            if hand_in_roi:
                if final_label_frame == "Unknown":
                    roi_color = (255, 100, 0) # Blue (BGR format) meaning hand is present but no gesture
                else:
                    if time_since_trigger < cfg.cooldown_sec or progress_val >= 1.0:
                        roi_color = (0, 255, 0) # Green (Triggered)
                    else:
                        roi_color = (0, 255, 255) # Yellow (Building)
                        
            base_thickness = 2
            if roi_color == (0, 255, 255) or roi_color == (0, 255, 0):
                pulse = int(2 + 2 * math.sin(current_time * 12))
                base_thickness += pulse

            cv2.rectangle(frame, (cfg.roi_x1, cfg.roi_y1), (cfg.roi_x2, cfg.roi_y2), roi_color, base_thickness)
            cv2.putText(frame, "[Z] Lock", (cfg.roi_x1 + 8, cfg.roi_y1 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, roi_color, 1, cv2.LINE_AA)
            cv2.putText(frame, "[Q] Quit", (cfg.roi_x1 + 8, cfg.roi_y1 + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.45, roi_color, 1, cv2.LINE_AA)
            
            # Trigger Logic
            if max_counter >= cfg.persistence_threshold:
                if is_locked:
                    status_msg = "LOCKED (Press Z)"
                elif time_since_trigger < cfg.cooldown_sec:
                    status_msg = f"Cooldown ({int(cfg.cooldown_sec - time_since_trigger)})"
                else:
                    focus_browser() 
                    
                    action_key = cfg.actions.get(max_counter_gesture)
                    if action_key:
                        pyautogui.press(action_key)
                        
                        # Friendly display names mapping
                        display_name_map = {
                            "open_palm": "PLAY/PAUSE",
                            "two_fingers": "SKIP FWD",
                            "fist": "SKIP BACK", 
                            "thumbs_up": "VOL UP",
                            "thumbs_down": "VOL DOWN"
                        }
                        nice_name = display_name_map.get(max_counter_gesture, max_counter_gesture.upper())
                        action_msg = f"{nice_name} ('{action_key}')"
                    
                    status_msg = "TRIGGERED"
                    last_trigger_time = current_time
                    
                    for g in gesture_counters:
                        gesture_counters[g] = 0
                        
                    last_action_time = current_time
                    last_status_override_time = current_time
                    override_status_msg = "TRIGGERED!"
                    
            elif not is_locked:
                if time_since_eyes_open > cfg.sleepiness_timeout_sec:
                    if not auto_pause_fired:
                        focus_browser()
                        pyautogui.press("k")
                        action_msg = "AUTO-PAUSE SENT"
                        auto_pause_fired = True
                        last_action_time = current_time
                        last_status_override_time = current_time
                        override_status_msg = "AUTO-PAUSED (Sleepy)"
                    status_msg = "READY"
                elif not hand_detected:
                    status_msg = "READY"
                elif eyes_closed_detected:
                    status_msg = "READY"
                else:
                    status_msg = "READY"
            else:
                status_msg = "LOCKED"

            if not is_locked and (current_time - last_status_override_time < 1.5):
                status_msg = override_status_msg
            if current_time - last_action_time > 1.5:
                action_msg = "None"

            # --- CLEAN HUD RENDERING ---
            put_text_hud(frame, "GESTURE CONTROL SYSTEM (DEMO)", 20, 25, scale=0.6, color=(0, 255, 255))
            put_text_hud(frame, f"STATUS: {status_msg}", 20, 55, scale=0.8, color=(0, 255, 0) if not is_locked else (0, 0, 255))
            if action_msg != "None":
                put_text_hud(frame, f"ACTION: {action_msg}", 20, 95, scale=0.9, color=(255, 255, 0), thickness=3)

            draw_color = GESTURE_COLORS.get(max_counter_gesture, (200, 200, 200)) if progress_val > 0 else (200, 200, 200)
            if "Unknown" in gesture_msg or "No" in gesture_msg or "Move" in gesture_msg:
                draw_color = GESTURE_COLORS["Unknown"]
                
            put_text_hud(frame, f"PRED: {final_label_frame.upper()} [{current_pred_confidence}]", 20, h - 110, scale=0.6, color=(220, 220, 220))
            put_text_hud(frame, f"GESTURE: {gesture_msg.upper()}", 20, h - 80, scale=1.1, color=draw_color, thickness=3)
            
            if progress_val > 0 and progress_val < 1.0:
                put_progress_bar(frame, 20, h - 35, 200, 15, progress_val, color=draw_color)
            elif progress_val >= 1.0:
                put_text_hud(frame, "HOLD EXECUTING...", 20, h - 20, scale=0.6, color=(0, 255, 0))
            elif progress_val == 0:
                put_text_hud(frame, "[Z] Toggle Lock  [Q] Quit", 20, h - 20, scale=0.5, color=(180, 180, 180))

            # HUD Right Side Info
            put_text_hud(frame, f"FPS: {int(fps)}", w - 160, 30, scale=0.6, color=(255, 255, 255))
            eyes_color = (0, 255, 0) if eyes_msg == "Open" else (0, 0, 255)
            put_text_hud(frame, f"EYES: {eyes_msg}", w - 160, 60, scale=0.6, color=eyes_color)
            
            # Key Mappings HUD
            put_text_hud(frame, "MAPPINGS:", w - 180, 100, scale=0.5, color=(200, 200, 200))
            m_y_offset = 125
            for g_name, k in cfg.actions.items():
                lbl = g_name.replace("_", " ").title()
                put_text_hud(frame, f"{lbl} -> '{k}'", w - 180, m_y_offset, scale=0.45, color=GESTURE_COLORS.get(g_name, (200, 200, 200)), thickness=1)
                m_y_offset += 25

            cv2.imshow("Gesture Control Demo (Final)", frame)

            key = cv2.waitKeyEx(1)
            key_byte = key & 0xFF
            if key_byte == ord('q'):
                break
            elif key_byte == ord('z'):
                is_locked = not is_locked
                if is_locked:
                    status_msg = "LOCKED"
                    action_msg = "None"
                else:
                    last_eyes_open_time = time.time()
                    auto_pause_fired = False

    if 'cap' in locals() and cap.isOpened():
        cap.release()
    cv2.destroyAllWindows()
    print("Demo Closed.")

if __name__ == "__main__":
    main()
