import time
import sys
import math
from dataclasses import dataclass
import cv2
import mediapipe as mp
import pyautogui

# Optional: Try to import pygetwindow for auto-focus, but don't crash if missing
try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except ImportError:
    HAS_PYGETWINDOW = False


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
        
    # Vertical distances
    v1 = dist(pts[1], pts[5])
    v2 = dist(pts[2], pts[4])
    # Horizontal distance
    h1 = dist(pts[0], pts[3])
    
    return (v1 + v2) / (2.0 * h1) if h1 > 0 else 0.0


def print_startup_checklist():
    print("="*60)
    print("      GESTURE YOUTUBE CONTROL - SPRINT 3 DEMO      ")
    print("="*60)
    print("CHECKLIST FOR RELIABILITY:")
    print("1. LIGHTING: Ensure you are well-lit (face light source).")
    print("2. BACKGROUND: Avoid busy backgrounds or backlighting.")
    print("3. BROWSER: Open YouTube in Chrome/Edge.")
    print("4. FOCUS: Click inside the video player to ensure it has focus.")
    print("5. POSITION: Place this window so it doesn't cover the video.")
    print("6. AUTO-PAUSE: Video will pause if no hand is seen OR eyes are closed for 3 seconds.")
    print("7. LOCK SAFETY: Lock the system ([S]) to prevent accidental triggers/pauses.")
    print("-" * 60)
    print("CONTROLS:")
    print("  [S] Toggle LOCK/UNLOCK (prevent accidental triggers)")
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


def is_open_palm(hand_landmarks) -> bool:
    """Returns True if all 5 fingers (including thumb) are fully extended."""
    lm = hand_landmarks.landmark
    mp_hands = mp.solutions.hands
    
    # Check the 4 main fingers (Index, Middle, Ring, Pinky) are extended UP
    finger_tips_pips = [
        (mp_hands.HandLandmark.INDEX_FINGER_TIP, mp_hands.HandLandmark.INDEX_FINGER_PIP),
        (mp_hands.HandLandmark.MIDDLE_FINGER_TIP, mp_hands.HandLandmark.MIDDLE_FINGER_PIP),
        (mp_hands.HandLandmark.RING_FINGER_TIP, mp_hands.HandLandmark.RING_FINGER_PIP),
        (mp_hands.HandLandmark.PINKY_TIP, mp_hands.HandLandmark.PINKY_PIP),
    ]
    
    extended_count = 0
    for tip, pip in finger_tips_pips:
        if lm[tip].y < lm[pip].y: # Hand is upright, tip is above pip
            extended_count += 1
            
    # Check if thumb is extended OUTWARD (using X coordinates relative to PIP)
    thumb_tip = lm[mp_hands.HandLandmark.THUMB_TIP]
    thumb_ip = lm[mp_hands.HandLandmark.THUMB_IP] 
    pinky_mcp = lm[mp_hands.HandLandmark.PINKY_MCP]
    
    thumb_extended = False
    dist_tip = ((thumb_tip.x - pinky_mcp.x)**2 + (thumb_tip.y - pinky_mcp.y)**2)**0.5
    dist_ip = ((thumb_ip.x - pinky_mcp.x)**2 + (thumb_ip.y - pinky_mcp.y)**2)**0.5
    


def main():
    print_startup_checklist()
    cfg = Config()
    
    mp_hands = mp.solutions.hands
    mp_face_mesh = mp.solutions.face_mesh
    mp_drawing = mp.solutions.drawing_utils

    try:
        cap = cv2.VideoCapture(cfg.camera_index)
        if not cap.isOpened():
            print("ERROR: Could not open webcam. Please check your connection.")
            return

        # State Variables
        last_trigger_time = 0.0
        persistence_counter = 0
        is_locked = True  # Start locked for safety
        
        last_hand_seen_time = time.time()
        last_eyes_open_time = time.time()  # Track when eyes were last open
        
        auto_pause_fired = False
        prev_frame_time = time.time()
        
        # Track timers for 1.5s sticky HUD messages
        last_action_time = 0.0
        last_status_override_time = 0.0
        override_status_msg = ""
        
        status_msg = "LOCKED"
        action_msg = "None"
        gesture_msg = "None"
        eyes_msg = "Eyes Open"
        
        hand_detected = False

        # Open both models inside with statement
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
                    
                # Flip and get dimensions
                frame = cv2.flip(frame, 1)
                h, w, _ = frame.shape
                
                # FPS Calculation
                current_time = time.time()
                fps = 1 / (current_time - prev_frame_time) if current_time > prev_frame_time else 0
                prev_frame_time = current_time
                
                # Draw ROI
                cv2.rectangle(frame, (cfg.roi_x1, cfg.roi_y1), (cfg.roi_x2, cfg.roi_y2), (255, 255, 255), 2)
                put_text_hud(frame, "ROI", cfg.roi_x1, cfg.roi_y1 - 10, scale=0.5, thickness=1)

                # Process Frame for Hand & Face
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # 1. Process Hands
                results_hands = hands.process(rgb)
                hand_in_roi = False
                detected_open_palm = False

                if results_hands.multi_hand_landmarks:
                    hand_detected = True
                    last_hand_seen_time = current_time
                    
                    for hand_landmarks in results_hands.multi_hand_landmarks:
                        mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                        
                        # Check if Wrist is inside ROI
                        wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                        wx, wy = int(wrist.x * w), int(wrist.y * h)
                        
                        if cfg.roi_x1 < wx < cfg.roi_x2 and cfg.roi_y1 < wy < cfg.roi_y2:
                            hand_in_roi = True
                            if is_open_palm(hand_landmarks):
                                detected_open_palm = True
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
                    # If no face is detected, we don't assume eyes are closed
                    last_eyes_open_time = current_time
                    eyes_msg = "No Face"
                
                # Reset Auto Pause flag if condition is clear (Hand seen AND Eyes open)
                if hand_detected and not eyes_closed_detected:
                    auto_pause_fired = False

                # Time checks
                time_since_trigger = current_time - last_trigger_time
                time_since_hand = current_time - last_hand_seen_time
                time_since_eyes_open = current_time - last_eyes_open_time
                
                # Gesture State Machine
                if hand_detected:
                    if hand_in_roi and detected_open_palm:
                        persistence_counter += 1
                        display_count = min(persistence_counter, cfg.persistence_threshold)
                        gesture_msg = f"Open Palm ({display_count}/{cfg.persistence_threshold})"
                    else:
                        persistence_counter = 0
                        if hand_in_roi:
                            gesture_msg = "Hand in ROI (no gesture)"
                        else:
                            gesture_msg = "Move hand into ROI"
                else:
                    persistence_counter = 0
                    gesture_msg = "No hand detected"

                # Trigger Logic
                if persistence_counter >= cfg.persistence_threshold:
                    if is_locked:
                        status_msg = "LOCKED (Press S)"
                    elif time_since_trigger < cfg.cooldown_sec:
                        status_msg = f"Cooldown ({int(cfg.cooldown_sec - time_since_trigger)})"
                    else:
                        # FIRE ACTION
                        focus_browser() 
                        pyautogui.press("k")
                        
                        action_msg = "PLAY/PAUSE SENT"
                        status_msg = "TRIGGERED!"
                        last_trigger_time = current_time
                        persistence_counter = 0 # Reset counter
                        
                        # Set tracking for 1.5s HUD UI fade
                        last_action_time = current_time
                        last_status_override_time = current_time
                        override_status_msg = "TRIGGERED!"
                        
                elif not is_locked:
                    # Auto-pause absence & sleepiness check
                    if time_since_hand > cfg.absence_timeout_sec:
                        if not auto_pause_fired:
                            focus_browser()
                            pyautogui.press("k")
                            action_msg = "AUTO-PAUSE SENT"
                            auto_pause_fired = True
                            
                            # Set tracking for 1.5s fade
                            last_action_time = current_time
                            last_status_override_time = current_time
                            override_status_msg = "AUTO-PAUSED (Absent)"
                        status_msg = "READY"
                    elif time_since_eyes_open > cfg.sleepiness_timeout_sec:
                        if not auto_pause_fired:
                            focus_browser()
                            pyautogui.press("k")
                            action_msg = "AUTO-PAUSE SENT"
                            auto_pause_fired = True
                            
                            # Set tracking for 1.5s fade
                            last_action_time = current_time
                            last_status_override_time = current_time
                            override_status_msg = "AUTO-PAUSED (Sleepy)"
                        status_msg = "READY"
                    # Normal countdown visualization 
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

                # Apply Message Fade Overrides
                if not is_locked and (current_time - last_status_override_time < 1.5):
                    status_msg = override_status_msg
                
                if current_time - last_action_time > 1.5:
                    action_msg = "None"

                # --- HUD Drawing ---
                put_text_hud(frame, f"FPS: {int(fps)}", w - 100, 30, scale=0.6)
                
                # Bottom Left Information Stack
                start_y = h - 30
                line_height = 30
                
                # 1. Quit Instruction
                put_text_hud(frame, " [Q] Quit  [S] Lock/Unlock", 20, start_y, scale=0.6)
                
                # 2. Status
                color = (0, 0, 255) if is_locked else (0, 255, 0) # Red if locked, Green if ready
                if "Cooldown" in status_msg or "in" in status_msg: color = (0, 255, 255) # Yellow
                if "AUTO-PAUSED" in status_msg: color = (255, 165, 0) # Orange
                put_text_hud(frame, f"STATUS:  {status_msg}", 20, start_y - line_height, color=color, scale=0.8)

                # 3. Action
                put_text_hud(frame, f"ACTION:  {action_msg}", 20, start_y - 2*line_height, color=(255, 100, 100))

                # 4. Gesture Debug & Eyes Debug
                debug_str = f"GESTURE: {gesture_msg} | {eyes_msg}"
                put_text_hud(frame, debug_str, 20, start_y - 3*line_height, scale=0.6)

                cv2.imshow("Gesture Control (Sprint 3)", frame)

                # Input Handling
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    is_locked = not is_locked
                    if is_locked:
                        status_msg = "LOCKED"
                        action_msg = "None"
                    else:
                        # Reset tracking to prevent immediate auto-pause on unlock
                        last_hand_seen_time = time.time()
                        last_eyes_open_time = time.time()
                        auto_pause_fired = False

    except Exception as e:
        print(f"FATAL ERROR: An unexpected error occurred: {e}")
        
    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        cv2.destroyAllWindows()
        print("Application closed.")

if __name__ == "__main__":
    main()
