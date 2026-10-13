pyinstaller --noconsole --onefile --name "PomodoroTimer" --icon=ModernPomodoro.ico --add-data "ModernPomodoro.ico;." --add-data "tick_normal.wav;." --add-data "tick_slow.wav;." --add-data "notification.wav;." main8.py > logCompilacion.log 

