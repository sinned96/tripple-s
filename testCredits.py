import os
from google.cloud import speech

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/pi/Desktop/v2_Tripple S/cloudKey.json"
client = speech.SpeechClient()
print("Client created OK!")
