# Upload Server Dokumentation

## Überblick

Der Upload-Server ermöglicht es, Dateien über eine Web-Oberfläche hochzuladen, die über QR-Code oder direkte URL-Eingabe erreichbar ist.

## Konfiguration

### Port-Einstellung

Der Upload-Server läuft standardmäßig auf Port **8080**. Sie können den Port auf verschiedene Weise ändern:

#### Option 1: In main.py (Zeile ~75)
```python
# Upload Server Configuration
UPLOAD_PORT = 8080  # Ändern Sie diesen Wert auf gewünschten Port
```

#### Option 2: Umgebungsvariable
```bash
export UPLOAD_PORT=8000
python3 main.py
```

### Empfohlene Ports

- **8080** (Standard) - Typischer Web-Server Port
- **8000** - Alternative für Entwicklung
- **8001, 8002, ...** - Bei Port-Konflikten
- **9000** - Höhere Port-Nummer

## Verwendung

### Server-Start

Der Upload-Server startet automatisch beim Start der Hauptanwendung (`main.py`). 

### QR-Code Zugriff

1. Starten Sie die Aufnahme-Funktion in der App
2. Klicken Sie auf den **"📱 QR-Code (Port XXXX)"** Button
3. Scannen Sie den QR-Code mit einem Smartphone
4. Die Upload-Seite öffnet sich im Browser

### Direkte URL

```
http://[IP-ADRESSE]:[PORT]/upload
```

Beispiele:
- `http://192.168.1.100:8080/upload`
- `http://localhost:8080/upload`

## Fehlerbehebung

### "Address already in use" Fehler

**Problem**: Port ist bereits belegt

**Lösung**:
1. Ändern Sie `UPLOAD_PORT` in `main.py` auf einen anderen Wert
2. Oder verwenden Sie eine Umgebungsvariable:
   ```bash
   UPLOAD_PORT=8000 python3 main.py
   ```

### Server startet nicht

**Mögliche Ursachen**:
- Port bereits von anderem Programm verwendet
- Firewall blockiert Port
- Keine Berechtigung für Port (nur bei Ports < 1024)

**Lösung**:
- Verwenden Sie einen höheren Port (> 1024)
- Prüfen Sie die Logs in der Konsole
- Stellen Sie sicher, dass der Port verfügbar ist

### QR-Code wird nicht angezeigt

**Ursache**: `qrcode` Bibliothek fehlt

**Installation**:
```bash
pip install qrcode[pil]
```

## Technische Details

### Unterstützte Features

- ✅ Konfigurierbare Port-Einstellung
- ✅ Automatische Port-Konflikt-Erkennung
- ✅ QR-Code Generierung
- ✅ Web-basierte Upload-Oberfläche
- ✅ Fehlerbehandlung und Logging
- ✅ Sauberes Herunterfahren

### Upload-Verzeichnis

Hochgeladene Dateien werden gespeichert in:
```
[APP_DIR]/uploads/
```

### Sicherheitshinweis

⚠️ **Wichtig**: Der Upload-Server ist nur für lokale Netzwerke gedacht. Verwenden Sie ihn nicht in öffentlichen oder unsicheren Netzwerken ohne zusätzliche Sicherheitsmaßnahmen.

## Beispiel-Anwendung

```python
# main.py Beispiel
UPLOAD_PORT = 8000  # Port auf 8000 ändern

# Der Server startet automatisch und zeigt:
# "Upload-Server läuft auf: http://192.168.1.100:8000/upload"
```

## Support

Bei Problemen:
1. Prüfen Sie die Konsolen-Ausgabe für Fehlermeldungen
2. Stellen Sie sicher, dass der gewählte Port verfügbar ist
3. Testen Sie mit einem anderen Port
4. Prüfen Sie die Netzwerkverbindung zwischen Geräten