# TikTok Studio — локальный помощник для theDĀW (бета)

Сайт theDĀW работает на GitHub Pages, поэтому **сам не может управлять приложениями и файлами на твоём Windows-компьютере**. Этот скрипт запускается локально. Он открывает браузер TikTok Studio, пытается выбрать экспортированный MP4 и, если распознаёт поле, добавить подпись. **Сам не нажимает «Опубликовать».**

### Подготовка на Windows

1. Установи [Node.js LTS](https://nodejs.org/).
2. Скачай проект ZIP: https://github.com/lunarinkee-dmg/thedaw_studio/archive/refs/heads/main.zip — распакуй его.
3. В папке проекта открой PowerShell или терминал Windows.
4. Выполни:

```powershell
npm install --no-save playwright
npx playwright install chromium
```

5. В theDĀW Studio нажми **Подготовить для TikTok Studio**, дождись скачивания MP4.
6. Запусти помощник, указав путь к своему файлу:

```powershell
node tools/tiktok-studio-upload.mjs "C:\Users\USERNAME\Downloads\theDAW-reels.mp4"
```

Для подписи создай UTF-8 текстовый файл и укажи его вторым аргументом:

```powershell
node tools/tiktok-studio-upload.mjs "C:\Users\USERNAME\Downloads\theDAW-reels.mp4" "C:\Users\USERNAME\Downloads\caption.txt"
```

Скрипт откроет отдельное окно браузера. **Войди в TikTok вручную**, открой Upload в Studio, если нужно. Проверь заполнение, разрешения на музыку и публикацию; финальную кнопку нажми сам.

### Ограничения

- TikTok может изменить страницу, ограничить автоматизацию или потребовать CAPTCHA. **Не обходи такие проверки.** Если скрипт не сработал — пользуйся обычной загрузкой в TikTok Studio.
- Пароли и токены скрипт не запрашивает. Браузерный профиль хранится локально в `%USERPROFILE%\.thedaw\tiktok-studio-browser`; никому не передавай эту папку.
- Возможность использования автоматизации зависит от правил TikTok, региона и аккаунта. Проверяй их перед использованием.
- **Никакая публикация не выполняется автоматически.** Успех на конкретном аккаунте ещё не проверен.
