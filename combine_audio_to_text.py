import whisper
import os

# Dateien, die transkribiert werden sollen
audio_files = ["aufnahme.wav"]
output_text_file = "transkription.txt"

def transcribe_audio(file_path):
    """Transkribiert eine Audiodatei mit Whisper."""
    print(f"Starte Transkription für: {file_path}")
    model = whisper.load_model("tiny")  # Verwende das kleinere Modell
    result = model.transcribe(file_path, language="de")  # Sprache auf Deutsch setzen
    return result['text']

def main():
    combined_text = ""

    # Jede Audiodatei transkribieren und den Text hinzufügen
    for audio_file in audio_files:
        try:
            print(f"Überprüfe Datei: {audio_file}")
            full_path = os.path.abspath(audio_file)
            print(f"Absoluter Pfad: {full_path}")
            
            # Überprüfen, ob die Datei existiert
            if not os.path.exists(audio_file):
                print(f"Fehler: Datei '{audio_file}' wurde nicht gefunden.")
                continue

            print(f"Transkription der Datei: {audio_file} läuft...")
            text = transcribe_audio(audio_file)
            combined_text += f"--- Transkription von {audio_file} ---\n{text}\n\n"

        except Exception as e:
            print(f"Fehler bei der Transkription von {audio_file}: {e}")

    # Kombinierte Transkription in einer Textdatei speichern
    if combined_text:
        with open(output_text_file, "w", encoding="utf-8") as f:
            f.write(combined_text)
        print(f"Die Transkription wurde abgeschlossen und in '{output_text_file}' gespeichert.")
    else:
        print("Keine Transkriptionen erstellt.")

if __name__ == "__main__":
    main()
