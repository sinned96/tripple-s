import requests
import os
import base64

TRANSCRIPT_PATH = "/home/pi/Desktop/v2_Tripple S/transkript.txt"
BILDER_DIR = "/home/pi/Desktop/v2_Tripple S/BilderVertex"
ENDPOINT = "https://vertex.googleapis.com/v1/your-endpoint"
TOKEN = "YOUR_ACCESS_TOKEN"

def main():
    if not os.path.exists(TRANSCRIPT_PATH):
        print(f"Transkript nicht gefunden: {TRANSCRIPT_PATH}")
        return

    with open(TRANSCRIPT_PATH, "r") as f:
        prompt = f.read().strip()

    if not prompt:
        print("Transkript ist leer!")
        return

    response = requests.post(
        ENDPOINT,
        json={"prompt": prompt},
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        }
    )

    try:
        response.raise_for_status()
        data = response.json()
        if "image" in data:
            img_bytes = base64.b64decode(data["image"])
            os.makedirs(BILDER_DIR, exist_ok=True)
            img_path = os.path.join(BILDER_DIR, "vertex_output.png")
            with open(img_path, "wb") as img_file:
                img_file.write(img_bytes)
            print(f"Bild erfolgreich gespeichert: {img_path}")
        else:
            print("Kein Bild in der Antwort:", data)
    except Exception as e:
        print(f"Fehler beim Vertex-Request: {e}\nAntwort: {response.text}")

if __name__ == "__main__":
    main()
