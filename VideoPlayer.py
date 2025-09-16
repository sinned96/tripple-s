import cv2
import pygame
import time

# Initialisiere pygame
pygame.init()

# Video-Dateiname
VIDEO_PATH = "Eis_Werbung.mp4"

# Displaygroesse (1024x600, spezifisch fuer dein 7-Zoll-Display)
DISPLAY_WIDTH = 1024
DISPLAY_HEIGHT = 600

# Zeit in Sekunden, nach der die Pfeile verschwinden
HIDE_ARROWS_AFTER = 3

# Oeffne das Video
cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    print(f"Fehler: Das Video '{VIDEO_PATH}' konnte nicht geoeffnet werden.")
    exit()

# Erstelle ein pygame-Fenster im Vollbildmodus (ohne Rahmen)
screen = pygame.display.set_mode((DISPLAY_WIDTH, DISPLAY_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Video Player")

# Lade Pfeil-Grafiken (hier kannst du deine eigenen Bilder verwenden)
arrow_image = pygame.Surface((50, 50))
arrow_image.fill((255, 0, 0))  # Beispiel: Roter Platzhalter

# Variablen zur Steuerung der Pfeile
show_arrows = False
last_touch_time = 0

# Haupt-Loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Pruefen, ob auf das Display getippt wurde
        if event.type == pygame.MOUSEBUTTONDOWN:
            show_arrows = True
            last_touch_time = time.time()

        # Abbruch, wenn 'x' gedrueckt wird
        if event.type == pygame.KEYDOWN and event.key == pygame.K_x:
            running = False

    # Verstecke Pfeile nach ein paar Sekunden
    if show_arrows and time.time() - last_touch_time > HIDE_ARROWS_AFTER:
        show_arrows = False

    # Lies den naechsten Frame aus dem Video
    ret, frame = cap.read()
    if not ret:
        # Wenn das Video zu Ende ist, starte es neu
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        continue

    # Drehe das Video um 180 Grad (zweimal 90 Grad)
    frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

    # Spiegele das Video horizontal
    frame = cv2.flip(frame, 1)

    # Konvertiere das OpenCV-Bild (BGR -> RGB)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Skaliere das Video exakt auf die Displaygroesse
    frame_surface = pygame.surfarray.make_surface(frame)
    frame_surface = pygame.transform.scale(frame_surface, (DISPLAY_WIDTH, DISPLAY_HEIGHT))

    # Zeige das Video im Vollbildmodus
    screen.blit(frame_surface, (0, 0))

    # Falls Pfeile sichtbar sein sollen, zeige sie an
    if show_arrows:
        screen.blit(arrow_image, (10, DISPLAY_HEIGHT // 2 - 25))  # Linker Pfeil
        screen.blit(arrow_image, (DISPLAY_WIDTH - 60, DISPLAY_HEIGHT // 2 - 25))  # Rechter Pfeil

    pygame.display.flip()

# Ressourcen freigeben
cap.release()
pygame.quit()
