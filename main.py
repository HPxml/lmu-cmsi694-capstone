import time
import sys
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
    
    min_detection_confidence: float = 0.6
    min_tracking_confidence: float = 0.6


def print_startup_checklist():
    print("="*60)
    print("      GESTURE YOUTUBE CONTROL - SPRINT 2 DEMO      ")
    print("="*60)
    print("CHECKLIST FOR RELIABILITY:")
    print("1. LIGHTING: Ensure you are well-lit (face light source).")
    print("2. BACKGROUND: Avoid busy backgrounds or backlighting.")
    print("3. BROWSER: Open YouTube in Chrome/Edge.")
    print("4. FOCUS: Click inside the video player to ensure it has focus.")
    print("5. POSITION: Place this window so it doesn't cover the video.")
    print("-" * 60)
    print("CONTROLS:")
    print("  [S] Toggle LOCK/UNLOCK (prevent accidental triggers)")
    print("  [Q] Quit Application")
    print("="*60)
    print("Starting camera...")



    # State Variables
    last_trigger_time = 0.0
    persistence_counter = 0
    is_locked = True  # Start locked for safety
    
    status_msg = "LOCKED"
    action_msg = "None"
    gesture_msg = "None"

    with mp_hands.Hands(
        model_complexity=0,
        min_detection_confidence=cfg.min_detection_confidence,
        min_tracking_confidence=cfg.min_tracking_confidence,
        max_num_hands=1
    ) as hands:
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Flip and get dimensions
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            
            # Draw ROI
            cv2.rectangle(frame, (cfg.roi_x1, cfg.roi_y1), (cfg.roi_x2, cfg.roi_y2), (255, 255, 255), 2)
            put_text_hud(frame, "ROI", cfg.roi_x1, cfg.roi_y1 - 10, scale=0.5, thickness=1)

            # Process Hand
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)
            
            hand_in_roi = False
            detected_open_palm = False

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    
                    # Check if Wrist is inside ROI
                    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                    wx, wy = int(wrist.x * w), int(wrist.y * h)
                    
                    if cfg.roi_x1 < wx < cfg.roi_x2 and cfg.roi_y1 < wy < cfg.roi_y2:
                        hand_in_roi = True
                        if is_open_palm(hand_landmarks):
                            detected_open_palm = True
            
            # Logic Update
            current_time = time.time()
            time_since_trigger = current_time - last_trigger_time
            
            # Gesture State Machine
            if hand_in_roi and detected_open_palm:
                persistence_counter += 1
                # UI Polish: Clamp display value to threshold
                display_count = min(persistence_counter, cfg.persistence_threshold)
                gesture_msg = f"Open Palm ({display_count}/{cfg.persistence_threshold})"
            else:
                persistence_counter = 0
                gesture_msg = "ROI Active" if hand_in_roi else "Searching..."

            # Trigger Logic
            if persistence_counter >= cfg.persistence_threshold:
                if is_locked:
                    status_msg = "LOCKED (Press S)"
                elif time_since_trigger < cfg.cooldown_sec:
                    status_msg = f"Cooldown ({int(cfg.cooldown_sec - time_since_trigger)})"
                else:
                    # FIRE ACTION
                    focus_browser() # Try to focus if possible
                    pyautogui.press("k")
                    
                    action_msg = "PLAY/PAUSE SENT"
                    status_msg = "TRIGGERED!"
                    last_trigger_time = current_time
                    persistence_counter = 0 # Reset counter
            elif not is_locked:
                status_msg = "READY"
            else:
                status_msg = "LOCKED"

            # --- HUD Drawing ---
            # Bottom Left Information Stack
            start_y = h - 30
            line_height = 30
            
            # 1. Quit Instruction
            put_text_hud(frame, " [Q] Quit  [S] Lock/Unlock", 20, start_y, scale=0.6)
            
            # 2. Status
            color = (0, 0, 255) if is_locked else (0, 255, 0) # Red if locked, Green if ready
            if "Cooldown" in status_msg: color = (0, 255, 255) # Yellow
            put_text_hud(frame, f"STATUS:  {status_msg}", 20, start_y - line_height, color=color, scale=0.8)

            # 3. Action
            put_text_hud(frame, f"ACTION:  {action_msg}", 20, start_y - 2*line_height, color=(255, 100, 100))

            # 4. Gesture Debug
            put_text_hud(frame, f"GESTURE: {gesture_msg}", 20, start_y - 3*line_height, scale=0.6)

            cv2.imshow("Gesture Control (Sprint 2)", frame)

            # Input Handling
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                is_locked = not is_locked
                if is_locked:
                    status_msg = "LOCKED"
                    action_msg = "None"

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
