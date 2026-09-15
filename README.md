# Livermorium

Музыкальный плеер для Windows с эквалайзером, виртуалайзером, плейлистами и загрузкой треков прямо из SoundCloud.

![Python](https://img.shields.io/badge/Python-3.14+-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📖 Описание

**Livermorium** — это лёгкий музыкальный плеер, написанный на Python с использованием pygame и sounddevice. Он умеет:

- 🎵 Воспроизводить MP3, M4A, OGG, OPUS, WAV, FLAC
- 🎚️ Применять **9-полосный эквалайзер** в реальном времени (60 Гц — 16 кГц)
- 📊 Показывать **виртуалайзер** (FFT-спектр) с плавной анимацией
- ⬇️ **Скачивать треки и плейлисты из SoundCloud** через yt-dlp
- 📁 Создавать **плейлисты**, переименовывать, добавлять треки из библиотеки
- 🔍 Искать треки по названию
- 🎨 Менять **цвета панелей, кнопок и виртуалайзера**, а также прозрачность
- 🖼️ Ставить **фоновое изображение**
- 🔀 Перемешивать треки **без повторов** (shuffle)
- 🔔 Сворачиваться **в системный трей** (крестик не закрывает — просто скрывает)
- 🚀 Добавляться в **автозапуск Windows** (кнопка в меню)

---

## 📋 Требования

- **Windows 10 / 11**
- **Python 3.14+** ([python.org](https://www.python.org/downloads/))
- **FFmpeg** — нужен для конвертации аудио при скачивании
- **yt-dlp** — нужен для загрузки из SoundCloud

---

## 🚀 Установка

 1. Установи Python
Скачай с [python.org](https://www.python.org/downloads/) и при установке **обязательно отметь галочку «Add Python to PATH»**.

Проверь в командной строке:
```bash
py --version
 2. Установи зависимости

Открой командную строку и выполни:
py -m pip install pygame-ce soundfile sounddevice scipy numpy pystray Pillow pywin32 pywinauto yt-dlp
 3. Скачай FFmpeg и yt-dlp

    FFmpeg: скачай с gyan.dev архив ffmpeg-release-essentials.zip, распакуй, положи ffmpeg.exe в папку с плеером.

    yt-dlp: скачай yt-dlp.exe с github.com/yt-dlp/yt-dlp/releases.

Оба файла должны лежать рядом с player.py:
Livermorium/
    player.py
    ffmpeg.exe
    yt-dlp.exe
    music/        (создастся автоматически)
 4. Запусти
py player.py

Управление
Верхняя панель

    ◀◀ — предыдущий трек

    ▶ / ⏸ — плей/пауза

    ▶▶ — следующий трек

    🔀 — перемешивание без повторов

    ☰ — плейлисты

    🔍 — поиск

    ⋮ — меню
Меню ⋮
Пункт	Что делает
ADD	Добавить трек или плейлист по ссылке SoundCloud
BACKGROUND	Выбрать фоновое изображение
EDIT	Режим редактирования (перетаскивание и ресайз панелей)
TRANSPARENCY	Настроить прозрачность верхней панели и остальных панелей
COLOR VIRT	Цвет виртуалайзера
COLOR PANEL	Цвет фонов панелей
COLOR TOP	Цвет верхней панели
COLOR BTN	Цвет кнопок и ползунков
AUTOSTART	Включить/выключить автозапуск с Windows
RESET	Сбросить раскладку панелей
EXIT	Полностью закрыть плеер
Горячие клавиши

    F11 — полный экран

    Esc — закрыть текущее окно / выйти

    Колесо мыши над ползунком громкости — изменить громкость

    Колесо мыши над списком треков — прокрутка

    ЛКМ по треку — воспроизвести

📁 Структура проекта

После первого запуска рядом с player.py появятся:
Livermorium/
    player.py            # основной код
    ffmpeg.exe           # (скачать отдельно)
    yt-dlp.exe           # (скачать отдельно)
    music/               # все скачанные и добавленные треки
    playlists.json       # плейлисты и распределение треков
    settings.json        # громкость, цвета, прозрачность, фон
    layout.json          # размер окна

🛠️ Сборка в .exe

Можно собрать один исполняемый файл, чтобы запускать без Python.
1. Установи PyInstaller
py -m pip install pyinstaller

2. Собери

Из папки с player.py:
py -m PyInstaller --onedir --windowed --name Livermorium ^
    --add-data "ffmpeg.exe;." ^
    --add-data "yt-dlp.exe;." ^
    --hidden-import win32com ^
    --hidden-import pythoncom ^
    --hidden-import pywintypes ^
    player.py

    На Windows символ ^ — перенос строки в командной строке. Можно написать всё одной строкой.

3. Готовый .exe

Появится в dist/Livermorium/Livermorium.exe. Всю папку dist/Livermorium/ можно копировать и запускать на любом ПК с Windows — Python не потребуется.
⚠️ Известные ограничения

    Только Windows — используется win32gui для трея и управления окном.

    Скачивание с SoundCloud работает, пока yt-dlp поддерживает SoundCloud. Если сломалось — обнови yt-dlp: py -m pip install --upgrade yt-dlp.

    Антивирусы иногда ругаются на .exe от PyInstaller — это нормально, добавь в исключения.

📜 Лицензия

MIT License — используй свободно, изменяй, распространяй.