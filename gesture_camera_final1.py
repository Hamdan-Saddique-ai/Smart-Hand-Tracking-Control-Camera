import cv2
import os
import mediapipe as mp
import numpy as np
import time

# MediaPipe setup
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

# 1. Folder banayo
if not os.path.exists('Sketches'):
    os.makedirs('Sketches')

# 2. Camera connect karo
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Camera nahi khul raha!")
    exit()

# 3. Sketch formula
def dodge(x, y):
    return cv2.divide(x, 255 - y, scale=256)

# Gesture detection functions
def get_finger_state(hand_landmarks):
    """Get state of all fingers (0=down, 1=up)"""
    finger_tips = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky
    
    finger_states = []
    for tip in finger_tips:
        if tip == 4:  # Thumb - check if extended
            # For thumb, check if it's pointing sideways (extended)
            thumb_tip = hand_landmarks.landmark[4]
            thumb_mcp = hand_landmarks.landmark[2]  # Thumb MCP
            # Check horizontal extension for gun gesture
            horizontal_ext = abs(thumb_tip.x - thumb_mcp.x) > 0.1
            vertical_ext = thumb_tip.y < thumb_mcp.y - 0.05
            
            if horizontal_ext or vertical_ext:
                finger_states.append(1)
            else:
                finger_states.append(0)
        else:  # Other fingers
            if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[tip-2].y - 0.05:
                finger_states.append(1)
            else:
                finger_states.append(0)
    
    return finger_states  # [thumb, index, middle, ring, pinky]

def detect_gesture(hand_landmarks):
    """Detect specific hand gestures"""
    finger_states = get_finger_state(hand_landmarks)
    thumb, index, middle, ring, pinky = finger_states
    
    # 1. 🔫 GUN SIGN (Index up + Thumb sideways, others down)
    # Index up + thumb up (extended sideways), middle+ring+pinky down
    if index == 1 and thumb == 1 and middle == 0 and ring == 0 and pinky == 0:
        # Additional check: thumb should be sideways (not just up)
        thumb_tip = hand_landmarks.landmark[4]
        thumb_ip = hand_landmarks.landmark[3]
        if abs(thumb_tip.x - thumb_ip.x) > 0.05:  # Thumb is sideways
            return "GUN_SIGN"
    
    # 2. ✌️ PEACE SIGN (Index + Middle up, others down)
    if index == 1 and middle == 1 and ring == 0 and pinky == 0:
        return "PEACE_SIGN"
    
    # 3. 🎧 DJ SIGN (Index + Pinky up, others down) - YO-YO HAND
    if index == 1 and pinky == 1 and middle == 0 and ring == 0:
        return "DJ_SIGN"
    
    # 4. ✊ FIST (All fingers down)
    if index == 0 and middle == 0 and ring == 0 and pinky == 0:
        return "FIST"
    
    # 5. 🖐️ OPEN HAND (All 5 fingers up)
    if index == 1 and middle == 1 and ring == 1 and pinky == 1:
        return "OPEN_HAND"
    
    # 6. 👍 THUMBS UP (Only thumb up)
    if thumb == 1 and index == 0 and middle == 0 and ring == 0 and pinky == 0:
        return "THUMBS_UP"
    
    # 7. 🤘 METAL SIGN (Index + Pinky up, thumb maybe up) - ROCK ON
    if index == 1 and pinky == 1 and middle == 0 and ring == 0:
        return "ROCK_ON"
    
    # 8. 👌 OK SIGN (Thumb and index touching)
    thumb_tip = hand_landmarks.landmark[4]
    index_tip = hand_landmarks.landmark[8]
    distance = ((thumb_tip.x - index_tip.x)**2 + (thumb_tip.y - index_tip.y)**2)**0.5
    if distance < 0.05 and middle == 0 and ring == 0 and pinky == 0:
        return "OK_SIGN"
    
    # 9. ✋ STOP SIGN (All fingers except thumb up)
    if thumb == 0 and index == 1 and middle == 1 and ring == 1 and pinky == 1:
        return "STOP_SIGN"
    
    # 10. ☝️ POINTING (Only index finger up)
    if index == 1 and middle == 0 and ring == 0 and pinky == 0:
        return "POINTING"
    
    return "UNKNOWN"

def detect_hand_movement(hand_landmarks, movement_history):
    """Detect hand movements for YO-YO motion"""
    if len(movement_history) < 5:
        return "NO_MOVEMENT"
    
    wrist_y = hand_landmarks.landmark[0].y
    movement_history.append(wrist_y)
    
    if len(movement_history) > 15:
        movement_history.pop(0)
    
    # Calculate up-down movement pattern
    if len(movement_history) >= 10:
        # Check for rapid direction changes
        direction_changes = 0
        for i in range(2, len(movement_history)):
            diff1 = movement_history[i-1] - movement_history[i-2]
            diff2 = movement_history[i] - movement_history[i-1]
            if diff1 * diff2 < 0:  # Direction changed
                direction_changes += 1
        
        if direction_changes >= 4:  # Multiple up-down movements
            return "YO_YO_MOVEMENT"
    
    return "NO_MOVEMENT"

# Variables
count = 1
mode = "NORMAL"
mode_message = "📷 NORMAL MODE - Show hand gestures"
movement_history = []
gesture_cooldown = 0
frame_count = 0

print("=" * 60)
print("ADVANCED GESTURE CONTROL CAMERA")
print("=" * 60)
print("\n🎯 HAND GESTURES DETECTION:")
print("1. 🔫 GUN SIGN    (Index + Thumb sideways)  -> GUN MODE")
print("2. ✌️  PEACE SIGN  (Index + Middle up)      -> PEACE MODE")
print("3. 🤘 DJ SIGN     (Index + Pinky up)       -> DJ MODE")
print("4. ✊ FIST        (Closed hand)            -> FIGHT MODE")
print("5. 🖐️  OPEN HAND   (All 5 fingers)         -> NORMAL MODE")
print("6. 👍 THUMBS UP   (Only thumb up)          -> LIKE MODE")
print("7. 👌 OK SIGN     (Thumb+Index touch)      -> OK MODE")
print("8. ✋ STOP SIGN   (All except thumb)       -> STOP MODE")
print("9. ☝️  POINTING    (Only index finger)      -> POINT MODE")
print("10.🔄 Yo-yo Motion (Up-down hand movement) -> MUSIC MODE")
print("\n⌨️  KEYBOARD CONTROLS:")
print("   SPACEBAR - Save sketch as photo")
print("   'q' key  - Quit program")
print("=" * 60)

# Color codes for different modes
mode_colors = {
    "NORMAL": (0, 255, 0),     # Green
    "GUN": (0, 0, 255),        # Red
    "PEACE": (255, 255, 0),    # Cyan
    "DJ": (255, 0, 255),       # Magenta
    "FIGHT": (255, 0, 0),      # Blue
    "LIKE": (0, 255, 255),     # Yellow
    "OK": (255, 255, 0),       # Cyan
    "STOP": (0, 165, 255),     # Orange
    "POINT": (255, 255, 255),  # White
    "MUSIC": (128, 0, 128)     # Purple
}

# Main loop
try:
    while True:
        # Frame capture
        success, img = cap.read()
        if not success:
            print("Frame capture error!")
            break
        
        frame_count += 1
        
        # Flip for mirror effect
        img = cv2.flip(img, 1)
        height, width = img.shape[:2]
        
        # Convert to RGB for MediaPipe
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        results = hands.process(rgb_img)
        
        current_gesture = "No hand detected"
        current_movement = ""
        gesture_cooldown = max(0, gesture_cooldown - 1)
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw hand landmarks
                mp_drawing.draw_landmarks(
                    img, 
                    hand_landmarks, 
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=3, circle_radius=4),
                    mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=3)
                )
                
                # Detect gesture and movement
                gesture = detect_gesture(hand_landmarks)
                movement = detect_hand_movement(hand_landmarks, movement_history)
                
                current_gesture = gesture
                current_movement = movement
                
                # Change mode based on gesture/movement
                if gesture_cooldown == 0:
                    if gesture == "GUN_SIGN" and mode != "GUN":
                        mode = "GUN"
                        mode_message = "🔫 GUN MODE - Pew! Pew!"
                        gesture_cooldown = 40
                        print("🔫 GUN MODE ACTIVATED! (Index + Thumb sideways)")
                    
                    elif gesture == "PEACE_SIGN" and mode != "PEACE":
                        mode = "PEACE"
                        mode_message = "✌️ PEACE MODE - Love & Peace"
                        gesture_cooldown = 40
                        print("✌️ PEACE MODE ACTIVATED! (Index + Middle fingers)")
                    
                    elif gesture == "DJ_SIGN" and mode != "DJ":
                        mode = "DJ"
                        mode_message = "🎧 DJ MODE - Drop the beat!"
                        gesture_cooldown = 40
                        print("🎧 DJ MODE ACTIVATED! (Index + Pinky fingers)")
                    
                    elif gesture == "FIST" and mode != "FIGHT":
                        mode = "FIGHT"
                        mode_message = "🥊 FIGHT MODE - Let's fight!"
                        gesture_cooldown = 40
                        print("🥊 FIGHT MODE ACTIVATED! (Closed fist)")
                    
                    elif gesture == "OPEN_HAND" and mode != "NORMAL":
                        mode = "NORMAL"
                        mode_message = "📷 NORMAL MODE - Camera ready"
                        gesture_cooldown = 40
                        print("📷 NORMAL MODE ACTIVATED! (Open hand)")
                    
                    elif gesture == "THUMBS_UP" and mode != "LIKE":
                        mode = "LIKE"
                        mode_message = "👍 LIKE MODE - Awesome!"
                        gesture_cooldown = 40
                        print("👍 LIKE MODE ACTIVATED! (Thumbs up)")
                    
                    elif gesture == "OK_SIGN" and mode != "OK":
                        mode = "OK"
                        mode_message = "👌 OK MODE - All good!"
                        gesture_cooldown = 40
                        print("👌 OK MODE ACTIVATED! (OK sign)")
                    
                    elif gesture == "STOP_SIGN" and mode != "STOP":
                        mode = "STOP"
                        mode_message = "✋ STOP MODE - Halt!"
                        gesture_cooldown = 40
                        print("✋ STOP MODE ACTIVATED! (Stop sign)")
                    
                    elif gesture == "POINTING" and mode != "POINT":
                        mode = "POINT"
                        mode_message = "☝️ POINT MODE - Look there!"
                        gesture_cooldown = 40
                        print("☝️ POINT MODE ACTIVATED! (Pointing finger)")
                    
                    elif movement == "YO_YO_MOVEMENT" and mode != "MUSIC":
                        mode = "MUSIC"
                        mode_message = "🔄 MUSIC MODE - Yo-yo motion!"
                        gesture_cooldown = 40
                        print("🔄 MUSIC MODE ACTIVATED! (Yo-yo hand movement)")
        
        # Get color for current mode
        color = mode_colors.get(mode, (255, 255, 255))
        
        # 1. Draw semi-transparent overlay for mode
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (width, 100), (0, 0, 0), -1)
        img = cv2.addWeighted(overlay, 0.5, img, 0.5, 0)
        
        # 2. Display current mode
        cv2.putText(img, mode_message, (20, 40), 
                   cv2.FONT_HERSHEY_DUPLEX, 0.9, color, 2)
        
        # 3. Display current gesture
        cv2.putText(img, f"Gesture: {current_gesture}", (20, 75), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 4. Mode-specific visual effects
        if mode == "GUN":
            # Gun sight and bullets
            cv2.circle(img, (width//2, height//2), 70, (0, 0, 255), 2)
            cv2.line(img, (width//2-80, height//2), (width//2+80, height//2), (0, 0, 255), 3)
            cv2.line(img, (width//2, height//2-80), (width//2, height//2+80), (0, 0, 255), 3)
            
            # Bullet trails animation
            if frame_count % 10 == 0:
                for i in range(5):
                    x = np.random.randint(width//2-100, width//2+100)
                    y = np.random.randint(height//2-100, height//2+100)
                    cv2.circle(img, (x, y), 5, (0, 0, 255), -1)
            
            cv2.putText(img, "PEW! PEW! PEW!", (width//2-120, 200), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        
        elif mode == "PEACE":
            # Peace symbols and doves
            cv2.putText(img, "✌️ PEACE ✌️", (width//2-100, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 3)
            
            # Peace sign circles
            for i in range(3):
                radius = 50 + i*30
                cv2.circle(img, (width//2, height//2), radius, (255, 255, 0), 2)
        
        elif mode == "DJ":
            # DJ turntables and music waves
            cv2.putText(img, "🎧 DJ TIME 🎶", (width//2-120, 100), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 255), 3)
            
            # Music equalizer bars
            bar_width = 15
            for i in range(15):
                x = i * 25 + 50
                bar_height = np.random.randint(30, 250)
                bar_color = (np.random.randint(150, 255), 
                            np.random.randint(0, 255), 
                            np.random.randint(150, 255))
                cv2.rectangle(img, (x, height-bar_height), (x+bar_width, height), bar_color, -1)
            
            # Turntables
            cv2.circle(img, (width//3, height//2), 60, (255, 0, 255), 3)
            cv2.circle(img, (2*width//3, height//2), 60, (255, 0, 255), 3)
        
        elif mode == "FIGHT":
            # Boxing ring and gloves
            cv2.rectangle(img, (width//4, height//4), (3*width//4, 3*height//4), (255, 0, 0), 4)
            cv2.line(img, (width//2, height//4), (width//2, 3*height//4), (255, 0, 0), 2)
            
            # Boxing gloves
            cv2.circle(img, (width//3, height//2), 70, (255, 0, 0), -1)
            cv2.circle(img, (2*width//3, height//2), 70, (255, 0, 0), -1)
            
            cv2.putText(img, "🥊 FIGHT! 🥊", (width//2-100, height//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        
        elif mode == "LIKE":
            # Thumbs up animation
            cv2.putText(img, "👍", (width//2-50, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 255, 255), 5)
            cv2.putText(img, "AWESOME!", (width//2-100, 220), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
        
        elif mode == "OK":
            # OK sign circles
            cv2.circle(img, (width//2, height//2), 90, (255, 255, 0), 3)
            cv2.putText(img, "👌 OK! 👌", (width//2-80, height//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 3)
        
        elif mode == "MUSIC":
            # Animated music notes
            cv2.putText(img, "🎵 YO-YO MUSIC 🎵", (width//2-150, 120), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.3, (128, 0, 128), 3)
            
            # Floating music notes
            for i in range(8):
                x = (width//8 * i + frame_count * 2) % width
                y = (height//2 + 100 * np.sin(frame_count * 0.1 + i * 0.5)) % height
                cv2.putText(img, "♪", (int(x), int(y)), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (128, 0, 128), 2)
        
        # 5. Instructions at bottom
        instructions = [
            "GESTURE GUIDE:",
            "🔫 Gun: Index+Thumb sideways",
            "✌️ Peace: Index+Middle up", 
            "🎧 DJ: Index+Pinky up",
            "✊ Fight: Closed fist",
            "🖐️ Normal: Open hand",
            "SPACE=Save  q=Quit"
        ]
        
        # Draw instruction box
        cv2.rectangle(img, (10, height-180), (400, height-10), (0, 0, 0, 0.7), -1)
        cv2.rectangle(img, (10, height-180), (400, height-10), (0, 255, 0), 2)
        
        y_offset = height - 150
        for i, text in enumerate(instructions):
            text_color = (0, 255, 0) if i == 0 else (200, 255, 200)
            cv2.putText(img, text, (20, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
            y_offset += 25
        
        # 6. Frame counter
        cv2.putText(img, f"Frame: {frame_count}", (width-150, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        # Display the image
        cv2.imshow('Advanced Gesture Camera', img)
        
        # Keyboard controls
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):  # Quit
            break
        
        elif key == 32:  # Spacebar - Save sketch
            # Create sketch from current frame
            imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            imgGrayInv = 255 - imgGray
            imgBlur = cv2.GaussianBlur(imgGrayInv, (21, 21), 5)
            finalImg = dodge(imgGray, imgBlur)
            
            # Save the sketch
            filename = f'Sketches/sketch_{count:04d}.jpg'
            cv2.imwrite(filename, finalImg)
            
            # Show confirmation
            cv2.putText(img, "✓ SKETCH SAVED!", (width//2-120, height//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
            cv2.imshow('Advanced Gesture Camera', img)
            cv2.waitKey(300)
            
            print(f"📸 Sketch saved: {filename}")
            count += 1

finally:
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("\n" + "=" * 60)
    print("🎬 PROGRAM ENDED SUCCESSFULLY!")
    print(f"📁 Total sketches saved: {count-1}")
    print("=" * 60)