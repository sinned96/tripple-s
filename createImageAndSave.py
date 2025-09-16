import os
from google.cloud import aiplatform

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/pfad/zu/deinem/cloudKey.json"

PROJECT_ID = "DEIN_PROJECT_ID"
LOCATION = "us-central1"
MODEL_ID = "imagen-001"

def generate_image(prompt):
    aiplatform.init(project=PROJECT_ID, location=LOCATION)
    model = aiplatform.VertexAIModel(model_name=MODEL_ID)
    response = model.predict(instances=[{"prompt": prompt}])
    # Bild als Base64-String extrahieren
    b64img = response.predictions[0]["bytesBase64Encoded"]
    with open("output.png", "wb") as f:
        f.write(base64.b64decode(b64img))
    print("Bild gespeichert als output.png")

if __name__ == "__main__":
    import base64
    generate_image("Ein Hund mit Sonnenbrille am Strand")
