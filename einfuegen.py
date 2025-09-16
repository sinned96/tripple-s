import subprocess
import time

print("Du hast jetzt 5 Sekunden Zeit, um das Textfeld zu fokussieren.")
time.sleep(5)
subprocess.run(["wtype", "<ctrl>v"])
