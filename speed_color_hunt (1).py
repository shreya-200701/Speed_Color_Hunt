import cv2
import time
import random
import numpy as np
import pygame
import sys
import subprocess


if "--popup" in sys.argv:
    import tkinter as tk

    score = sys.argv[2] if len(sys.argv) > 2 else "0"
    max_rounds = sys.argv[3] if len(sys.argv) > 3 else "10"

    score_num = int(score)
    if score_num == 10:
        feedback = "PERFECT SCORE! SPECTACULAR WORK!"
        color = "#00FF7F"
    elif score_num >= 7:
        feedback = "WELL DONE! GREAT REFLEXES!"
        color = "#00E5FF"
    elif score_num >= 4:
        feedback = "GOOD WORK! NICE ATTEMPT!"
        color = "#FFD700"
    else:
        feedback = "NICE TRY! PLAY AGAIN TO IMPROVE!"
        color = "#FF6B6B"

    root = tk.Tk()
    root.title("Game Over!")
    root.configure(bg="#1A1D24")

    # Force top-most window
    root.attributes('-topmost', True)
    root.focus_force()

    # Center window
    w, h = 480, 280
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw // 2) - (w // 2)
    y = (sh // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")

    tk.Label(root, text="GAME OVER", font=("Arial", 24, "bold"), fg="#FF4444", bg="#1A1D24").pack(pady=(20, 5))
    tk.Label(root, text=f"FINAL SCORE: {score} / {max_rounds}", font=("Arial", 18, "bold"), fg="#FFFFFF", bg="#1A1D24").pack(pady=5)
    tk.Label(root, text=feedback, font=("Arial", 13, "bold"), fg=color, bg="#1A1D24").pack(pady=10)

    def on_restart():
        print("RESTART")
        root.destroy()

    def on_quit():
        print("QUIT")
        root.destroy()

    btn_frame = tk.Frame(root, bg="#1A1D24")
    btn_frame.pack(pady=15)

    tk.Button(btn_frame, text="Play Again", font=("Arial", 11, "bold"), bg="#008CBA", fg="white", width=12, command=on_restart, cursor="hand2").pack(side="left", padx=10)
    tk.Button(btn_frame, text="Quit Game", font=("Arial", 11, "bold"), bg="#D9534F", fg="white", width=12, command=on_quit, cursor="hand2").pack(side="right", padx=10)

    root.mainloop()
    sys.exit(0)

# --- MAIN GAME LOGIC ---
pygame.init()
pygame.mixer.init()

infoObject = pygame.display.Info()
SCREEN_WIDTH, SCREEN_HEIGHT = infoObject.current_w, infoObject.current_h

# Borderless windowed fullscreen instead of exclusive pygame.FULLSCREEN.
# Exclusive fullscreen keeps other OS windows (like the Tkinter popup) from
# ever appearing on top, even with -topmost set — that was why the game-over
# window never showed up.
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME)
pygame.display.set_caption("Speed Color Hunt")

font_medium = pygame.font.SysFont("Arial", int(SCREEN_HEIGHT * 0.045), bold=True)
font_small = pygame.font.SysFont("Arial", int(SCREEN_HEIGHT * 0.03), bold=True)

def play_sound(freq_start, freq_end, duration=0.25):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, False)
    freq = np.linspace(freq_start, freq_end, n_samples)
    waveform = np.sin(2 * np.pi * freq * t) * 0.3
    sound_array = np.ascontiguousarray((waveform * 32767).astype(np.int16))
    stereo_array = np.column_stack((sound_array, sound_array))
    sound = pygame.sndarray.make_sound(stereo_array)
    sound.play()

def play_success_sound():
    play_sound(520, 880, duration=0.2)

def play_fail_sound():
    """Synthesized 'sad trombone' / womp-womp style fail sound —
    three descending notes, each with a bit of vibrato and a fade-out,
    to sound like the classic 'waaah waaah waaaaah' fail buzzer."""
    sample_rate = 44100
    # Each note: (frequency, duration)
    notes = [(392, 0.22), (349, 0.22), (294, 0.22), (247, 0.55)]  # G4 F4 D4 B3 (descending)

    full_waveform = []
    for freq, duration in notes:
        n_samples = int(sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)

        # slight vibrato (wobble) on top of the base frequency
        vibrato = 6 * np.sin(2 * np.pi * 5 * t)
        wave = np.sin(2 * np.pi * (freq + vibrato) * t)

        # fade in/out envelope so notes don't click against each other
        envelope = np.ones(n_samples)
        fade_len = int(n_samples * 0.15)
        envelope[:fade_len] = np.linspace(0, 1, fade_len)
        envelope[-fade_len:] = np.linspace(1, 0, fade_len)

        full_waveform.append(wave * envelope * 0.3)

    waveform = np.concatenate(full_waveform)
    sound_array = np.ascontiguousarray((waveform * 32767).astype(np.int16))
    stereo_array = np.column_stack((sound_array, sound_array))
    sound = pygame.sndarray.make_sound(stereo_array)
    sound.play()

COLOR_TARGETS = {
    "RED": {
        "text": "Show something RED!",
        "rgb": (255, 50, 50),
        "hsv_ranges": [
            (np.array([0, 120, 70]), np.array([10, 255, 255])),
            (np.array([170, 120, 70]), np.array([180, 255, 255]))
        ]
    },
    "BLUE": {
        "text": "Show something BLUE!",
        "rgb": (50, 120, 255),
        "hsv_ranges": [
            (np.array([90, 120, 70]), np.array([130, 255, 255]))
        ]
    },
    "GREEN": {
        "text": "Show something GREEN!",
        "rgb": (50, 255, 50),
        "hsv_ranges": [
            (np.array([36, 100, 70]), np.array([85, 255, 255]))
        ]
    },
    "YELLOW": {
        "text": "Show something YELLOW!",
        "rgb": (255, 255, 0),
        "hsv_ranges": [
            (np.array([20, 120, 100]), np.array([35, 255, 255]))
        ]
    },
    "ORANGE": {
        "text": "Show something ORANGE!",
        "rgb": (255, 165, 0),
        "hsv_ranges": [
            (np.array([11, 150, 100]), np.array([19, 255, 255]))
        ]
    },
    "PURPLE": {
        "text": "Show something PURPLE!",
        "rgb": (180, 50, 255),
        "hsv_ranges": [
            (np.array([130, 80, 70]), np.array([160, 255, 255]))
        ]
    },
    "BLACK": {
        "text": "Show something BLACK!",
        "rgb": (30, 30, 30),
        "hsv_ranges": [
            # Black is defined by low brightness (V), regardless of hue/saturation
            (np.array([0, 0, 0]), np.array([180, 255, 50]))
        ]
    },
    "PINK": {
        "text": "Show something PINK!",
        "rgb": (255, 105, 180),
        "hsv_ranges": [
            (np.array([145, 40, 150]), np.array([170, 160, 255]))
        ]
    }
}

MAX_ROUNDS = 10
ROUND_DURATION = 8.0
COOLDOWN_DURATION = 2.0

current_target_key = random.choice(list(COLOR_TARGETS.keys()))
score = 0
rounds_played = 0
state = "HUNTING"
round_start_time = time.time()
state_change_time = time.time()

cap = cv2.VideoCapture(0)
clock = pygame.time.Clock()
running = True

def launch_popup(final_score, max_rounds):
    # Screen is already a normal borderless window, so nothing special
    # needs to happen before spawning the popup subprocess.
    cmd = [sys.executable, __file__, "--popup", str(final_score), str(max_rounds)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout.strip()

    # Surfaces any crash in the popup process instead of failing silently.
    if result.returncode != 0:
        print("Popup subprocess failed:", result.stderr)

    return "restart" if "RESTART" in output else "quit"

while running and cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    h_cam, w_cam, _ = frame.shape
    now = time.time()

    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    target_info = COLOR_TARGETS[current_target_key]

    if state == "HUNTING":
        mask = np.zeros((h_cam, w_cam), dtype=np.uint8)
        for lower, upper in target_info["hsv_ranges"]:
            mask |= cv2.inRange(hsv_frame, lower, upper)

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        color_pixel_count = cv2.countNonZero(mask)
        min_required_pixels = int((h_cam * w_cam) * 0.03)

        if color_pixel_count > min_required_pixels:
            state = "SUCCESS"
            score += 1
            rounds_played += 1
            state_change_time = now
            play_success_sound()
        elif (now - round_start_time) > ROUND_DURATION:
            state = "FAILED"
            rounds_played += 1
            state_change_time = now
            play_fail_sound()

    elif state in ["SUCCESS", "FAILED"]:
        if (now - state_change_time) > COOLDOWN_DURATION:
            if rounds_played < MAX_ROUNDS:
                remaining_colors = [c for c in COLOR_TARGETS.keys() if c != current_target_key]
                current_target_key = random.choice(remaining_colors)
                state = "HUNTING"
                round_start_time = now
            else:
                state = "GAME_OVER"

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_rgb = np.rot90(frame_rgb)
    cam_surface = pygame.surfarray.make_surface(frame_rgb)
    cam_surface = pygame.transform.scale(cam_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(cam_surface, (0, 0))

    if state != "GAME_OVER":
        banner_height = int(SCREEN_HEIGHT * 0.16)
        banner = pygame.Surface((SCREEN_WIDTH, banner_height), pygame.SRCALPHA)
        banner.fill((15, 15, 15, 230))
        screen.blit(banner, (0, 0))

        swatch_size = int(banner_height * 0.6)
        pygame.draw.rect(screen, target_info["rgb"], (30, 20, swatch_size, swatch_size))
        pygame.draw.rect(screen, (255, 255, 255), (30, 20, swatch_size, swatch_size), 4)

        target_txt = font_medium.render(target_info["text"], True, (255, 255, 255))
        screen.blit(target_txt, (50 + swatch_size, 30))

        round_txt = font_small.render(f"ROUND: {min(rounds_played + 1, MAX_ROUNDS)} / {MAX_ROUNDS}", True, (200, 200, 200))
        score_txt = font_medium.render(f"SCORE: {score}", True, (0, 255, 255))
        screen.blit(round_txt, (SCREEN_WIDTH - 350, 20))
        screen.blit(score_txt, (SCREEN_WIDTH - 350, 60))

        if state == "HUNTING":
            time_left = max(0.0, ROUND_DURATION - (now - round_start_time))
            bar_w = int((SCREEN_WIDTH - 60) * (time_left / ROUND_DURATION))
            pygame.draw.rect(screen, (0, 200, 255), (30, banner_height - 18, bar_w, 12))
        elif state == "SUCCESS":
            msg = font_small.render("✓ CORRECT COLOR MATCH! +1 POINT", True, (0, 255, 0))
            screen.blit(msg, (30, banner_height - 35))
        elif state == "FAILED":
            msg = font_small.render("✗ TIME'S UP!", True, (255, 50, 50))
            screen.blit(msg, (30, banner_height - 35))

        pygame.display.flip()

    else:
        # --- LAUNCH INDEPENDENT POPUP PROCESS ---
        choice = launch_popup(score, MAX_ROUNDS)
        if choice == "restart":
            score = 0
            rounds_played = 0
            current_target_key = random.choice(list(COLOR_TARGETS.keys()))
            state = "HUNTING"
            round_start_time = time.time()
        else:
            running = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_q, pygame.K_ESCAPE]:
                running = False

    clock.tick(30)

cap.release()
pygame.quit()
