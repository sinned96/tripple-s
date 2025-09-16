import os
import time
import shutil

# Pfade anpassen
DOWNLOAD_DIR = os.path.expanduser("~/Downloads")
IMAGE_DIR = "/home/pi/meinprojekt-venv/Bilder1/"
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')

def get_images_in_folder(folder):
    return set(f for f in os.listdir(folder)
               if f.lower().endswith(IMAGE_EXTENSIONS) and os.path.isfile(os.path.join(folder, f)))

def move_new_images():
    print("Überwache neue Bilder im Download-Ordner ...")
    already_seen = get_images_in_folder(DOWNLOAD_DIR)

    while True:
        time.sleep(3)  # Alle 3 Sekunden prüfen
        current_files = get_images_in_folder(DOWNLOAD_DIR)
        new_files = current_files - already_seen

        for filename in new_files:
            src = os.path.join(DOWNLOAD_DIR, filename)
            dst = os.path.join(IMAGE_DIR, filename)
            print(f"Neues Bild gefunden: {filename} — wird verschoben.")
            try:
                shutil.move(src, dst)
                print(f"{filename} wurde nach {IMAGE_DIR} verschoben.")
            except Exception as e:
                print(f"Fehler beim Verschieben von {filename}: {e}")

        already_seen = get_images_in_folder(DOWNLOAD_DIR)

if __name__ == "__main__":
    move_new_images()