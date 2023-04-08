import datetime
import os
import random
import sys
import threading
import time
import urllib.parse
import webbrowser
from subprocess import call

import configparser

try:
    import pygame
    from PyQt6 import QtCore, QtGui, QtWidgets
    from fuzzywuzzy import fuzz

    """ 
    Credit to Artem Tiumentcev for creating num2t4ru
    https://github.com/seriyps/ru_number_to_text?ysclid=lg3zu5xfuz441917268 
    """
    from num2t4ru import num2text
    from pyowm import OWM
    # OWM setup
    from pyowm.utils.config import get_default_config
    import psutil
except ModuleNotFoundError:
    print('Oops! An error occurred when loading libraries. '
          'Try launching \'setup.py\' file to install the dependencies (located in same directory)')

try:
    import config
    import stt
    import text2num
except ModuleNotFoundError:
    print('Oops! An error occurred when loading built-in libraries. Try reinstalling/redownloading the project.')

config_dict = get_default_config()
config_dict['connection']['use_ssl'] = False
config_dict['connection']["verify_ssl_certs"] = False
config_dict['language'] = "ru"
owm = OWM('a5d2de3e663a6e3f59cc45f095a0caba', config_dict)
mgr = owm.weather_manager()
observation = mgr.weather_at_place('Saint Petersburg,RU')

# config (ini file) setup
configer = configparser.ConfigParser()
configer.read('settings.ini')
if not configer.sections():
    # Default parameters   Change at your own risk
    configer['DEFAULT'] = {'voice-volume': 1.0,
                           'music-volume': 0.5,
                           'default_browser_startpage': 'https://google.com',
                           'default_browser_search_engine': 'https://google.com',
                           'default_streaming_platform': 'https://ivi.ru',
                           'tts_rate': 150,
                           'tts_gender': 'Male'}
    configer['Generals'] = {'voice-volume': 1.0,
                            'music-volume': 0.5}
    configer['Browser'] = {'default_browser_startpage': 'https://google.com',
                           'default_browser_search_engine': 'https://google.com',
                           'default_streaming_platform': 'https://ivi.ru'}
    configer['TTS'] = {'tts_rate': 150,
                       'tts_gender': 'Male'}

    with open('settings.ini', 'w') as configfile:
        configer.write(configfile)


def settingsOverride(group, setting, value):
    for i in range(len(setting)):
        configer[group][setting[i]] = str(value[i])
    with open('settings.ini', 'w') as configfile:
        configer.write(configfile)


def nounCaseChooser(forOne, forTwoToFour, forRest, digit):
    digit%=100
    if digit%10 == 1 and digit//10!=1:
        return forOne
    elif digit%10 >= 2 and digit%10 <= 4 and digit//10!=1:
        return forTwoToFour
    else:
        return forRest


# Music class
class Music:
    def __init__(self):
        pygame.mixer.init()
        self.muted = False

        self.mixer = pygame.mixer
        self.playing = False
        self.skip = False
        self.isInQueue = False

    def list_audio_files(self, directory):
        audio_files = []

        # checking available music files
        for file in os.listdir(directory):
            if file.endswith('.mp3') or file.endswith('.wav'):
                audio_files.append(os.path.join(directory, file))
        return audio_files

    def play_audio(self, file):
        if not self.playing:
            self.mixer.music.load(file)
            self.mixer.music.set_volume(float(configer['Generals']['voice-volume']))
            self.mixer.music.play()
            self.playing = True

    def pause_audio(self):
        if self.playing:
            self.playing = False
            self.mixer.music.pause()

    def unpause_audio(self):
        if not self.playing:
            self.mixer.music.unpause()

    def stop_audio(self):
        if self.playing:
            self.mixer.music.stop()
            self.playing = False


# 2nd Thread, main events of recognize happen
class Worker(QtCore.QObject):
    _globalText = QtCore.pyqtSignal(str)
    globalText = ''

    # changes global text parameter so that text can be changed in QPlainTextEdit
    def globalizator(self, t, isYou=False, connect_to_previous=False):
        if connect_to_previous:
            self.globalText += t.capitalize() + ' '
        elif isYou:
            self.globalText += 'Вы: ' + t.capitalize() + '\n'
        else:
            self.globalText += config.official_name['ru'] + ': ' + t.capitalize() + '\n'

        self._globalText.emit(self.globalText)

    def va_respond(self, voice: str):
        # Проверяется, было ли обращение
        if voice.startswith(config.VA_CALLSIGN):
            self.global_cmd_unfiltered = voice

            self.globalizator(voice, True)

            cmd_filtered = self.filter_cmd(voice)
            cmd = self.recognize_cmd(cmd_filtered)

            # Сюда записываются р-таты обработки для доступа в других частях программы
            self.global_cmd = cmd_filtered

            if cmd['cmd'] not in config.VA_CMD_LIST.keys():
                call(["python3", "tts.py", config._misunderstand])
            else:
                self.execute_cmd(cmd['cmd'])

    # Фильтровка слов-паразитов, ненужных слов
    def filter_cmd(self, raw_voice: str):
        cmd = raw_voice

        for x in config.VA_CALLSIGN:
            cmd = cmd.replace(x, "").strip()

        for x in config.VA_TBR:
            cmd = cmd.replace(x, "").strip()
        return cmd

    # Comparing stt result to config cmds
    def recognize_cmd(self, cmd: str):
        rc = {'cmd': '', 'percent': 0}
        for c, v in config.VA_CMD_LIST.items():
            if isinstance(v, tuple):
                for x in v:
                    # print(c, v, x)
                    vrt = fuzz.ratio(cmd, x)
                    if vrt > rc['percent']:
                        rc['cmd'] = c
                        rc['percent'] = vrt
                        print(rc)
            else:
                # print(c, v)
                vrt = fuzz.ratio(cmd, v)
                if vrt > rc['percent']:
                    rc['cmd'] = c
                    rc['percent'] = vrt
                    print(rc)
        return rc

    def execute_cmd(self, cmd: str):
        if cmd == 'VA_HELP':
            text = config.VA_ABILITIES
            call(["python3", "tts.py", text])
            self.globalizator(text)
        elif cmd == 'VA_JOKE':
            call(["python3", "tts.py", config.VA_JOKES[random.randint(0, len(config.VA_JOKES))]])
            self.globalizator(config.VA_JOKES[random.randint(0, len(config.VA_JOKES))])
        elif cmd == 'VA_TTS-TEST':
            call(["python3", "tts.py", config._diagnostics])
            self.globalizator(config._diagnostics)
        elif cmd == 'VA_CTIME':
            # current time
            now = datetime.datetime.now()
            text = "Сейчас " + num2text(now.hour) + " " + nounCaseChooser("час", "часа", "часов", now.hour) + ' ' + \
                   num2text(now.minute) + " " + nounCaseChooser('минута', '', '', now.minute)
            call(["python3", "tts.py", text])
            self.globalizator(text)

        elif cmd == 'VA_GREETING':
            call(["python3", "tts.py", 'и тебе привет'])
            self.globalizator("и тебе привет")

        elif cmd == 'VA_HOWDY':
            helth = int(psutil.cpu_percent(interval=0.01))
            if helth<=40:
                text = 'у вашего компьютера все отлично как и у меня'
            elif helth<=80:
                text = 'у вашего компьютера все нормально как и у меня'
            else:
                text = 'ваш компьютер перегружен мне поплохело'
            call(["python3", "tts.py", text])
            self.globalizator(text)

        elif cmd == "VA_DOINGS":
            call(["python3", "tts.py", 'говорю с тобой как видишь'])
            self.globalizator("говорю с тобой как видишь")

        elif cmd == "VA_CHOOSE":
            cmd1 = self.global_cmd
            for i in config.VA_CMD_LIST['VA_CHOOSE']:
                if cmd1.find(i)!=-1:
                    cmd1 = cmd1.partition(i)[2]

            choices = cmd1.split('или')
            r = random.randint(0, len(choices)-1)
            t = 'я выбираю ' + choices[r]
            call(["python3", "tts.py", t])
            self.globalizator(t)


        elif cmd == 'VA_MATH':
            cmd1 = self.global_cmd.strip()
            for i in config.VA_CMD_LIST['VA_MATH']:
                print(i)
                if cmd1.find(i) != -1:
                    cmd1 = cmd1.replace(i, '')
            cmd1 = cmd1.replace(' плюс ', '+')
            cmd1 = cmd1.replace(' минус ', '-')
            cmd1 = cmd1.replace(' умножить ', '*')
            cmd1 = cmd1.replace(' делить ', '/')
            cmd1 = cmd1.replace(' квадрате ', '**два')
            cmd1 = cmd1.replace(' во второй степени ', '**два')
            cmd1 = cmd1.replace(' в кубе ', '**три')
            cmd1 = cmd1.replace(' степени ', '')
            cmd1 = cmd1.replace(' во', '**')
            cmd1 = cmd1.replace(' в', '**')

            if cmd1.find('на')!=-1 and cmd1[cmd1.find('на')-1]==' ':
                cmd1 = cmd1.replace(' на ', "*")
            print(cmd1)
            cmd2 = ''
            passnext = False
            for i, l in enumerate(cmd1):
                if passnext:
                    passnext = False
                elif l == '+':
                    cmd2 += str(text2num.numInterpriter(cmd1.partition('+')[0])) + '+'
                    cmd1 = cmd1[i + 1:]
                elif l == '-':
                    cmd2 += str(text2num.numInterpriter(cmd1.partition('+')[0])) + '+'
                    cmd1 = cmd1[i + 1:]
                elif l == '*' and cmd1[i+1]=='*':
                    cmd2 += str(text2num.numInterpriter(cmd1.partition('**')[0])) + '**'
                    cmd1 = cmd1[i + 1:]
                    passnext = True
                elif l == '*':
                    cmd2 += str(text2num.numInterpriter(cmd1.partition('+')[0])) + '+'
                    cmd1 = cmd1[i + 1:]
                elif l == '/':
                    cmd2 += str(text2num.numInterpriter(cmd1.partition('+')[0])) + '+'
                    cmd1 = cmd1[i + 1:]
            cmd2 += str(text2num.numInterpriter(cmd1))

            returnTxt = num2text(eval(cmd2))
            call(["python3", "tts.py", returnTxt])
            self.globalizator(returnTxt)


        elif cmd == 'VA_RANDOMNUM':
            if self.global_cmd.find(' от ') != -1:
                ranStr = self.global_cmd.partition(" от ")[2]
                ran = ranStr.split(' до ')
                print(ran)

                a = text2num.numInterpriter(ran[0])
                print(a)
                b = text2num.numInterpriter(ran[1])
                print(b)
                speakRan = num2text(random.randint(a, b))

                print(speakRan)
                call(["python3", "tts.py", speakRan])
                self.globalizator(speakRan)
            else:
                speakRan = "случайное число "+num2text(random.randint(0, 1000))
                call(["python3", "tts.py", speakRan])
                self.globalizator(speakRan)


        elif cmd == 'VA_TEMPERATURE':
            w = observation.weather
            outputTxt = num2text(w.temperature('celsius')['temp']) + nounCaseChooser(' градус', " градуса", " градусов", w.temperature('celsius')['temp'])
            call(["python3", "tts.py", outputTxt])
            self.globalizator(outputTxt)

        elif cmd == 'VA_HUMIDITY':
            w = observation.weather
            outputTxt = num2text(w.humidity) + nounCaseChooser(' процент',' процента',' процентов', w.humidity)
            call(["python3", "tts.py", outputTxt])
            self.globalizator(outputTxt)

        elif cmd == 'VA_DETAILED':
            w = observation.weather
            call(["python3", "tts.py", 'на улице ' + w.detailed_status])
            self.globalizator('на улице ' + w.detailed_status)

        elif cmd == 'VA_CLOUDNESS':
            w = observation.weather
            t = num2text(w.clouds) + nounCaseChooser('процент','процента','процентов', w.clouds)
            call(["python3", "tts.py", t])
            self.globalizator(t)

        elif cmd == 'VA_WIND':
            w = observation.weather
            outputTxt = 'скорость ветра ' + num2text(int(w.wind()['speed'])) + " метра в секунду"
            call(["python3", "tts.py", outputTxt])
            self.globalizator(outputTxt)


        elif cmd == 'VA_MUSIC':
            global music
            if music.isInQueue:
                music.stop_audio()
                music.isInQueue = False
            files = music.list_audio_files('music')
            if not music.isInQueue:
                call(["python3", "tts.py", 'проигрываю плейлист'])
                self.globalizator('проигрываю плейлист...')

                def musicPlaying():
                    music.isInQueue = True
                    for i in files:
                        if not music.isInQueue:
                            break

                        music.play_audio(i)
                        last_volume = float(configer['Generals']['music-volume'])
                        while True:
                            if not music.mixer.music.get_busy() and music.playing or not music.mixer.music.get_busy() and music.skip:
                                music.skip = False
                                break
                            else:
                                if last_volume != float(configer['Generals']['music-volume']):
                                    last_volume = float(configer['Generals']['music-volume'])
                                    music.mixer.music.set_volume(last_volume)
                                time.sleep(2)

                t = threading.Thread(target=musicPlaying)
                t.start()

        elif cmd == "VA_PAUSE_MUSIC":
            if music.playing:
                music.pause_audio()
                call(["python3", "tts.py", 'поставил на паузу'])
                self.globalizator('поставил на паузу')

        elif cmd == "VA_UNPAUSE_MUSIC":
            if not music.playing and music.isInQueue:
                music.unpause_audio()
                call(["python3", "tts.py", 'продолжение воспроизведения'])
                self.globalizator('продолжение воспроизведения...')

        elif cmd == "VA_SKIP_MUSIC":
            if music.isInQueue:
                music.skip = True
                music.stop_audio()
                call(["python3", "tts.py", 'пропущено'])
                self.globalizator('пропущено')

        elif cmd == 'VA_STOP_MUSIC':
            if music.isInQueue:
                music.isInQueue = False
                music.playing = True
                music.stop_audio()
                call(["python3", "tts.py", 'остановил'])
                self.globalizator('остановил')


        elif cmd == 'VA_SEARCH':
            if self.global_cmd.find('найди в интернете') != -1:
                call(["python3", "tts.py", 'провожу поиск'])
                self.globalizator('провожу поиск...')

                request = self.global_cmd.partition('найди в интернете')[2].strip()
                url = urllib.parse.quote(request)
                webbrowser.open(configer['Browser']['default_browser_search_engine'] + '/search?q=' + url, new=2)
            elif self.global_cmd.find('найди') != -1:
                call(["python3", "tts.py", 'провожу поиск'])
                self.globalizator("провожу поиск...")

                request = self.global_cmd.partition(' найди ')[2].strip()
                url = urllib.parse.quote(request)
                webbrowser.open(configer['Browser']['default_browser_search_engine'] + '/search?q=' + url, new=2)

        elif cmd == 'VA_FILM':
            webbrowser.open(configer['Browser']['default_streaming_platform'], new=2)
            self.globalizator("открываю...")
        elif cmd == 'VA_BROWSER':
            webbrowser.open(configer['Browser']['default_browser_startpage'], new=2)
            self.globalizator("открываю...")
        elif cmd == 'SM_Google':
            webbrowser.open('https://google.com', new=2)
            call(["python3", "tts.py", 'открываю'])
            self.globalizator("открываю...")
        elif cmd == 'SM_Yandex':
            webbrowser.open('https://yandex.ru', new=2)
            call(["python3", "tts.py", 'открываю'])
            self.globalizator("открываю...")
        elif cmd == 'SM_YouTube':
            webbrowser.open('https://youtube.com', new=2)
            call(["python3", "tts.py", 'открываю'])
            self.globalizator("открываю...")
        elif cmd == 'SM_OkRu':
            webbrowser.open('https://ok.ru', new=2)
            call(["python3", "tts.py", 'открываю'])
            self.globalizator("открываю...")
        elif cmd == 'SM_VK':
            webbrowser.open('https://vk.com', new=2)
            call(["python3", "tts.py", 'открываю'])
            self.globalizator("открываю...")



        elif cmd == 'VA_TIMER':
            request = self.global_cmd.partition('таймер')[2].strip()
            timer = 0
            if request:
                call(["python3", "tts.py", 'ставлю таймер'])
                if request.find('минут') != -1:
                    timer += text2num.numInterpriter(request.partition(' минут')[0]) * 60
                    request = request.replace(request.partition(' минут')[1] + request.partition(' минут')[2], '')
                if request.find('секунд') != -1:
                    timer += text2num.numInterpriter(request.partition(' секунд')[0])
                    # request = request.replace(request.partition(' секунд')[1]+request.partition(' секунд')[2], '')

                timing = time.time()
                while True:
                    if time.time() - timing > timer:
                        call(["python3", "tts.py", 'время вышло'])
                        self.globalizator('время вышло!')
                        break
            else:
                call(["python3", "tts.py", 'я не смогу поставить таймер без заданного времени'])
                self.globalizator('я не смогу поставить таймер без заданного времени!')

    def run(self):
        stt.va_listen(self.va_respond)


# UI (main window)
class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(460, 250)
        MainWindow.setMinimumSize(QtCore.QSize(460, 250))
        MainWindow.setMaximumSize(QtCore.QSize(460, 250))
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.line = QtWidgets.QFrame(self.centralwidget)
        self.line.setGeometry(QtCore.QRect(-70, 50, 591, 1))
        self.line.setStyleSheet("background:black\n")
        self.line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line.setObjectName("line")

        self.plainTextEdit = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.plainTextEdit.setGeometry(QtCore.QRect(190, 60, 261, 181))
        self.plainTextEdit.setPlainText("")
        self.plainTextEdit.setObjectName("plainTextEdit")

        self.micro = QtWidgets.QLabel(self.centralwidget)
        self.micro.setGeometry(QtCore.QRect(40, 90, 111, 121))
        self.micro.setText("")
        self.micro.setPixmap(QtGui.QPixmap("pyqt-resources/2bf2ec1ae9f290329a30629985a02eb5.png"))
        self.micro.setScaledContents(True)
        self.micro.setObjectName("micro")
        self.micro.mousePressEvent = self.onClick

        self.opt = QtWidgets.QLabel(self.centralwidget)
        self.opt.setGeometry(QtCore.QRect(405, 6, 41, 41))
        self.opt.setText("")
        self.opt.setPixmap(QtGui.QPixmap("pyqt-resources/img_144812.png"))
        self.opt.setScaledContents(True)
        self.opt.setObjectName("opt")
        self.opt.mousePressEvent = self.onSettings

        self.vol = QtWidgets.QLabel(self.centralwidget)
        self.vol.setGeometry(QtCore.QRect(350, 6, 41, 41))
        self.vol.setText("")
        self.vol.setPixmap(QtGui.QPixmap("pyqt-resources/volume.png"))
        self.vol.setScaledContents(True)
        self.vol.setObjectName("vol")
        self.vol.mousePressEvent = self.onMute

        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(10, 0, 131, 41))
        self.label.setTextFormat(QtCore.Qt.TextFormat.AutoText)
        self.label.setScaledContents(False)
        self.label.setObjectName("label")
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.label.setText(_translate("MainWindow", "<html><head/><body><p>" + config.official_name['en'] + "v. " +
                                      config.version + "</p><p>Localization: " + config.language + "</p></body></html>"))

    def onMute(self, e):
        if music.muted:
            music.muted = False
            print('unmute')
            self.vol.setPixmap(QtGui.QPixmap("pyqt-resources/volume.png"))
            if music.isInQueue:
                music.mixer.music.set_volume(float(configer['Generals']['music-volume']))
        else:
            music.muted = True
            print('mute')
            self.vol.setPixmap(QtGui.QPixmap("pyqt-resources/mute.png"))
            if music.isInQueue:
                music.mixer.music.set_volume(0)

    def onClick(self, e):
        print(stt.runFlag)
        stt.runFlag = not stt.runFlag

    def onPlainText(self, t):
        self.plainTextEdit.setPlainText(t)

    def onSettings(self, e):
        if self.settingFlag:
            self.Dialog.close()
        else:
            self.Dialog.open()

    def startTheThing(self):
        self.thread = QtCore.QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker._globalText.connect(self.onPlainText)

        self.thread.start()

        self.settingFlag = False
        self.Dialog = QtWidgets.QDialog()
        self.ui = Settings()
        self.ui.setupUi(self.Dialog)

# Settings window
class Settings(object):
    def setupUi(self, Dialog):
        self.volume_assist = float(configer['Generals']['voice-volume'])
        self.volume_music = float(configer['Generals']['music-volume'])
        self.tts_rate = int(configer['TTS']['tts_rate'])
        self.tts_gender = configer['TTS']['tts_gender']

        Dialog.setObjectName("Settings")
        Dialog.resize(458, 405)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 12)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.scrollArea = QtWidgets.QScrollArea(Dialog)
        self.scrollArea.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.scrollArea.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 446, 353))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_6.setContentsMargins(12, 0, 12, 0)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)
        self.gridLayout.setContentsMargins(-1, 0, -1, -1)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.music_label = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.music_label.setMaximumSize(QtCore.QSize(16777215, 11))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.music_label.setFont(font)
        self.music_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.music_label.setObjectName("music_label")
        self.verticalLayout_3.addWidget(self.music_label)
        self.music_slider = QtWidgets.QSlider(self.scrollAreaWidgetContents)
        self.music_slider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.music_slider.setObjectName("music_slider")
        self.verticalLayout_3.addWidget(self.music_slider)
        self.gridLayout.addLayout(self.verticalLayout_3, 1, 3, 1, 1)
        self.label_7 = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                           QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_7.sizePolicy().hasHeightForWidth())
        self.label_7.setSizePolicy(sizePolicy)
        self.label_7.setMinimumSize(QtCore.QSize(0, 20))
        self.label_7.setMaximumSize(QtCore.QSize(16777215, 20))
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.label_7.setFont(font)
        self.label_7.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignLeading | QtCore.Qt.AlignmentFlag.AlignLeft)
        self.label_7.setObjectName("label_7")
        self.gridLayout.addWidget(self.label_7, 6, 1, 1, 1)
        self.streamplatform = QtWidgets.QLineEdit(self.scrollAreaWidgetContents)
        self.streamplatform.setObjectName("streamplatform")
        self.gridLayout.addWidget(self.streamplatform, 5, 3, 1, 1)
        self.label_6 = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_6.sizePolicy().hasHeightForWidth())
        self.label_6.setSizePolicy(sizePolicy)
        self.label_6.setMinimumSize(QtCore.QSize(0, 15))
        self.label_6.setMaximumSize(QtCore.QSize(16777215, 15))
        self.label_6.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignLeading | QtCore.Qt.AlignmentFlag.AlignLeft)
        self.label_6.setObjectName("label_6")
        self.gridLayout.addWidget(self.label_6, 0, 1, 1, 1)
        self.label_5 = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_5.sizePolicy().hasHeightForWidth())
        self.label_5.setSizePolicy(sizePolicy)
        self.label_5.setMinimumSize(QtCore.QSize(0, 16))
        self.label_5.setObjectName("label_5")
        self.gridLayout.addWidget(self.label_5, 5, 1, 1, 1)
        self.startpage = QtWidgets.QLineEdit(self.scrollAreaWidgetContents)
        self.startpage.setObjectName("startpage")
        self.gridLayout.addWidget(self.startpage, 3, 3, 1, 1)
        self.label_8 = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_8.sizePolicy().hasHeightForWidth())
        self.label_8.setSizePolicy(sizePolicy)
        self.label_8.setMinimumSize(QtCore.QSize(0, 16))
        self.label_8.setObjectName("label_8")
        self.gridLayout.addWidget(self.label_8, 7, 1, 1, 1)
        self.label = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setMinimumSize(QtCore.QSize(0, 16))
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 1, 1, 1, 1)
        self.label_3 = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)
        self.label_3.setMinimumSize(QtCore.QSize(0, 16))
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 3, 1, 1, 1)
        self.label_9 = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.label_9.setMinimumSize(QtCore.QSize(0, 16))
        self.label_9.setMaximumSize(QtCore.QSize(16777215, 16))
        self.label_9.setObjectName("label_9")
        self.gridLayout.addWidget(self.label_9, 8, 1, 1, 1)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.Male = QtWidgets.QRadioButton(self.scrollAreaWidgetContents)
        self.Male.setObjectName("Male")
        self.horizontalLayout.addWidget(self.Male)
        self.Female = QtWidgets.QRadioButton(self.scrollAreaWidgetContents)
        self.Female.setObjectName("Female")
        self.horizontalLayout.addWidget(self.Female)
        self.gridLayout.addLayout(self.horizontalLayout, 7, 3, 1, 1)
        self.searcheng = QtWidgets.QLineEdit(self.scrollAreaWidgetContents)
        self.searcheng.setObjectName("searcheng")
        self.gridLayout.addWidget(self.searcheng, 4, 3, 1, 1)
        self.label_4 = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy)
        self.label_4.setMinimumSize(QtCore.QSize(0, 16))
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 4, 1, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding,
                                           QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout.addItem(spacerItem, 2, 2, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        self.label_2.setMinimumSize(QtCore.QSize(0, 16))
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 2, 1, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding,
                                            QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout.addItem(spacerItem1, 1, 2, 1, 1)
        self.verticalLayout_5 = QtWidgets.QVBoxLayout()
        self.verticalLayout_5.setSpacing(0)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.rate_label = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.rate_label.setMaximumSize(QtCore.QSize(16777215, 11))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.rate_label.setFont(font)
        self.rate_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.rate_label.setObjectName("rate_label")
        self.verticalLayout_5.addWidget(self.rate_label)
        self.rate_slider = QtWidgets.QSlider(self.scrollAreaWidgetContents)
        self.rate_slider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.rate_slider.setObjectName("rate_slider")
        self.verticalLayout_5.addWidget(self.rate_slider)
        self.gridLayout.addLayout(self.verticalLayout_5, 8, 3, 1, 1)
        self.verticalLayout_4 = QtWidgets.QVBoxLayout()
        self.verticalLayout_4.setSpacing(0)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.voice_label = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.voice_label.setMaximumSize(QtCore.QSize(16777215, 11))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.voice_label.setFont(font)
        self.voice_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.voice_label.setObjectName("voice_label")
        self.verticalLayout_4.addWidget(self.voice_label)
        self.voice_slider = QtWidgets.QSlider(self.scrollAreaWidgetContents)
        self.voice_slider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.voice_slider.setObjectName("voice_slider")
        self.verticalLayout_4.addWidget(self.voice_slider)
        self.gridLayout.addLayout(self.verticalLayout_4, 2, 3, 1, 1)
        self.verticalLayout_6.addLayout(self.gridLayout)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout_2.addWidget(self.scrollArea)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.StandardButton.Apply | QtWidgets.QDialogButtonBox.StandardButton.Cancel | QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.RestoreDefaults)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout_2.addWidget(self.buttonBox)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.label_7.setText(_translate("Dialog", "Synthesizer settings"))
        self.label_6.setText(_translate("Dialog",
                                        "<html><head/><body><p><span style=\" font-weight:600;\">General</span></p></body></html>"))
        self.label_5.setText(_translate("Dialog", "default streaming platofrm"))
        self.label_8.setText(_translate("Dialog", "Voice gender"))
        self.label.setText(_translate("Dialog", "music volume"))
        self.label_3.setText(_translate("Dialog", "browser startpage"))
        self.label_9.setText(_translate("Dialog", "Speak rate"))
        self.Male.setText(_translate("Dialog", "Male"))
        self.Female.setText(_translate("Dialog", "Female"))
        self.label_4.setText(_translate("Dialog", "default search engine"))
        self.label_2.setText(_translate("Dialog", "voice volume"))

        self.searcheng.setText(_translate("Dialog", configer['Browser']['default_browser_search_engine']))
        self.startpage.setText(_translate("Dialog", configer['Browser']['default_browser_startpage']))
        self.streamplatform.setText(_translate("Dialog", configer['Browser']['default_streaming_platform']))
        self.rate_label.setText(_translate("Dialog", str(self.tts_rate) + '%'))
        self.voice_label.setText(_translate("Dialog", str(int(self.volume_assist * 100)) + '%'))
        self.music_label.setText(_translate("Dialog", str(int(self.volume_music)) + '%'))

        self.rate_slider.setRange(0, 200)
        self.rate_slider.setValue(self.tts_rate)
        self.rate_slider.valueChanged.connect(self.onRateChange)

        self.music_slider.setRange(0, 120)
        self.music_slider.setValue(int(self.volume_music * 100))
        self.music_slider.valueChanged.connect(self.onMusicChange)

        self.voice_slider.setRange(0, 120)
        self.voice_slider.setValue(int(self.volume_assist * 100))
        self.voice_slider.valueChanged.connect(self.onVoiceChange)

        self.buttonBox.clicked.connect(self.onButtonBoxClick)

        self.Male.clicked.connect(self.onMale)
        self.Female.clicked.connect(self.onFemale)

    def onMale(self):
        self.tts_gender = 'Male'

    def onFemale(self):
        self.tts_gender = 'Female'
        print('FEM!')

    def onButtonBoxClick(self, button):
        role = self.buttonBox.buttonRole(button)
        if role == QtWidgets.QDialogButtonBox.ButtonRole.ApplyRole:
            self.onApply()
        elif role == QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole:
            self.onApply()
            ui.Dialog.close()
        elif role == QtWidgets.QDialogButtonBox.ButtonRole.ResetRole:
            self.onDefaults()
        elif role == QtWidgets.QDialogButtonBox.ButtonRole.RejectRole:
            ui.Dialog.close()

    def onRateChange(self, i):
        self.tts_rate = i
        self.rate_label.setText(str(i) + '%')

    def onVoiceChange(self, i):
        self.volume_assist = i / 100
        self.voice_label.setText(str(i) + '%')

    def onMusicChange(self, i):
        self.volume_music = i / 100
        self.music_label.setText(str(i) + '%')

    def onDefaults(self):
        settingsOverride('Generals',
                         ['voice-volume', 'music-volume'],
                         [configer['DEFAULT']['voice-volume'], configer['DEFAULT']['music-volume']])
        settingsOverride('Browser',
                         ['default_browser_startpage', 'default_browser_search_engine', 'default_streaming_platform'],
                         [configer['DEFAULT']['default_browser_startpage'],
                          configer['DEFAULT']['default_browser_search_engine'],
                          configer['DEFAULT']['default_streaming_platform']])
        settingsOverride('TTS',
                         ['tts_rate', 'tts_gender'],
                         [configer['DEFAULT']['tts_rate'], configer['DEFAULT']['tts_gender']])

        self.volume_assist = float(configer['DEFAULT']['voice-volume'])
        self.volume_music = float(configer['DEFAULT']['music-volume'])
        self.tts_rate = int(configer['DEFAULT']['tts_rate'])
        self.tts_gender = configer['DEFAULT']['tts_gender']

        self.searcheng.setText(configer['DEFAULT']['default_browser_search_engine'])
        self.startpage.setText(configer['DEFAULT']['default_browser_startpage'])
        self.streamplatform.setText(configer['DEFAULT']['default_streaming_platform'])
        self.rate_label.setText(str(self.tts_rate) + '%')
        self.voice_label.setText(str(int(self.volume_assist * 100)) + '%')
        self.music_label.setText(str(int(self.volume_music * 100)) + '%')

        self.rate_slider.setValue(self.tts_rate)
        self.music_slider.setValue(int(self.volume_music * 100))
        self.voice_slider.setValue(int(self.volume_assist * 100))

    def onApply(self):
        settingsOverride('Generals', ['voice-volume', 'music-volume'],
                         [self.volume_assist, self.volume_music])
        settingsOverride('Browser',
                         ['default_browser_startpage', 'default_browser_search_engine', 'default_streaming_platform'],
                         [self.startpage.text(), self.searcheng.text(), self.streamplatform.text()])
        settingsOverride('TTS', ['tts_rate', 'tts_gender'],
                         [self.tts_rate, self.tts_gender])


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()

    music = Music()

    ui.startTheThing()

    sys.exit(app.exec())
