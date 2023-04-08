import subprocess, sys

def install(package):
    """Установка библиотеки с помощью pip"""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


# Список необходимых библиотек
required_packages = ['pyowm','pygame','PyQt6','fuzzywuzzy', 'psutil',
                     'pyaudio','sounddevice','vosk','pyttsx3']

# Проверка наличия библиотек и установка их при необходимости
for package in required_packages:
    try:
        __import__(package)

    except ImportError or ModuleNotFoundError:
        print(f"Библиотека \"{package}\" не найдена, установка...")
        install(package)
        __import__(package)
