# text to speech (tts)
import sys, pyttsx3, configparser
config = configparser.ConfigParser()
config.read('settings.ini')
engine = pyttsx3.init() # object creation

"""RATE"""
rate = engine.getProperty('rate')   # getting details of current speaking rate
engine.setProperty('rate', int(config['TTS']['tts_rate']))     # setting up new voice rate
# print(config['TTS']['tts_rate'])
"""VOLUME"""
volume = engine.getProperty('volume')   # getting to know current volume level (min=0 and max=1)
engine.setProperty('volume', float(config['Generals']['voice-volume']))    # setting up volume level  between 0 and 1
print(engine.getProperty('volume'))
"""VOICES"""
voices = engine.getProperty('voices')
if config['TTS']['tts_gender'] == "Male":
    voiceGenders = filter(lambda voices: voices.gender == 'VoiceGenderMale', voices)
elif config['TTS']['tts_gender'] == "Female":
    voiceGenders = filter(lambda voices: voices.gender == 'VoiceGenderFemale', voices)
for voice in voiceGenders:
    if voice.languages == ['ru_RU']:
        engine.setProperty('voice', voice.id)

def va_speak(phrase):
    print(phrase)
    engine.say(phrase)
    engine.runAndWait()
    # engine.stop()

va_speak(str(sys.argv[1]))
