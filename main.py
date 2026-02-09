import time
from dataclasses import dataclass

import cv2
import mediapipe as mp
import pyautogui


@dataclass
class Config:
    camera_index: int = 0

    # ROI (interaction zone) in pixels
    roi_x1: int = 160
    roi_y1: int = 80
    roi_x2: int = 480
    roi_y2: int = 400

    cooldown_sec: float = 1.25

    min_detection_confidence: float = 0.6
    min_tracking_confidence: float = 0.6


mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils


def put_text_outline(frame, text, x, y, scale=0.7, thickness=2):
    """Readable white text with black outline."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, text, (x, y), font, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(frame, text, (x, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)


def draw_roi(frame, cfg: Config):
    cv2.rectangle(frame, (cfg.roi_x1, cfg.roi_y1), (cfg.roi_x2, cfg.roi_y2), (255, 255, 255), 2)
    put_text_outline(frame, "ROI (gesture inside box)", cfg.roi_x1, cfg.roi_y1 - 10, scale=0.6, thickness=2)


def wrist_in_roi(hand_landmarks, w: int, h: int, cfg: Config) -> bool:
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    x, y = int(wrist.x * w), int(wrist.y * h)
    return cfg.roi_x1 <= x <= cfg.roi_x2 and cfg.roi_y1 <= y <= cfg.roi_y2


def is_open_palm(hand_landmarks) -> bool:
    lm = hand_landmarks.landmark
    finger_pairs = [
        (mp_hands.HandLandmark.INDEX_FINGER_TIP, mp_hands.HandLandmark.INDEX_FINGER_PIP),
        (mp_hands.HandLandmark.MIDDLE_FINGER_TIP, mp_hands.HandLandmark.MIDDLE_FINGER_PIP),
        (mp_hands.HandLandmark.RING_FINGER_TIP, mp_hands.HandLandmark.RING_FINGER_PIP),
        (mp_hands.HandLandmark.PINKY_TIP, mp_hands.HandLandmark.PINKY_PIP),
    ]

    extended = 0
    for tip, pip in finger_pairs:
        if lm[tip].y < lm[pip].y:
            extended += 1

    return extended >= 3


def main():
    cfg = Config()

    cap = cv2.VideoCapture(cfg.camera_index)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")

    last_trigger = 0.0
    status = "Ready"

    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        model_complexity=1,
        min_detection_confidence=cfg.min_detection_confidence,
        min_tracking_confidence=cfg.min_tracking_confidence,
    ) as hands:
        while True:
            ok, frame = cap.read()
            if not ok:
                status = "Camera read failed"
                break

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            draw_roi(frame, cfg)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = hands.process(rgb)

            gesture = "None"
            action = "None"

            if res.multi_hand_landmarks:
                hand_lm = res.multi_hand_landmarks[0]
                mp_drawing.draw_landmarks(frame, hand_lm, mp_hands.HAND_CONNECTIONS)

                if wrist_in_roi(hand_lm, w, h, cfg):
                    if is_open_palm(hand_lm):
                        gesture = "OpenPalm"

                        now = time.time()
                        if now - last_trigger >= cfg.cooldown_sec:
                            pyautogui.press("k")
                            last_trigger = now
                            action = "Play/Pause"
                            status = "Triggered"
                        else:
                            status = "Cooldown..."
                    else:
                        status = "Hand in ROI (no gesture)"
                else:
                    status = "Move hand into ROI"
            else:
                status = "No hand detected"

            # --- Bottom-left HUD ---
            left_x = 20
            line_h = 32
            y_q = h - 20
            y_status = y_q - line_h
            y_action = y_status - line_h
            y_gesture = y_action - line_h

            put_text_outline(frame, f"Gesture: {gesture}", left_x, y_gesture, scale=0.8, thickness=2)
            put_text_outline(frame, f"Action:  {action}", left_x, y_action, scale=0.8, thickness=2)
            put_text_outline(frame, f"Status:  {status}", left_x, y_status, scale=0.8, thickness=2)
            put_text_outline(frame, "Press Q to quit", left_x, y_q, scale=0.7, thickness=2)

            cv2.imshow("Gesture YouTube Control (Sprint 1)", frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q")):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
