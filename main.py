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





# Face Mesh Indices for Eyes (P1..P6)
LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]





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
    
    if dist_tip > dist_ip:
        thumb_extended = True
            
    return extended_count == 4 and thumb_extended


if __name__ == "__main__":
    main()
