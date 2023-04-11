fin = input('Запустить дигностику библиотек? (Y/N): ')
if fin=='y' or fin=='Y':
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

sin = input('Переустановить model? (Y/N): ')
if sin=='Y' or sin=='y':
    """Добавление папки model"""
    import http.client
    import zipfile, os

    url = "alphacephei.com"
    path = "/vosk/models/vosk-model-small-ru-0.22.zip"
    filename = "vosk-model-small-ru-0.22.zip"
    # https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
    conn = http.client.HTTPSConnection(url)
    conn.request("GET", path)
    response = conn.getresponse()
    data = response.read()
    with open(filename, "wb") as f:
        f.write(data)

    with zipfile.ZipFile(filename,"r") as zip_ref:
        zip_ref.extractall()

    os.rename('vosk-model-small-ru-0.22', 'model')
    os.remove('vosk-model-small-ru-0.22.zip')

os.mkdir('music')