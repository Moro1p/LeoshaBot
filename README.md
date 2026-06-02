# LeoshaBot

<div align="center">

### 🎵 Twitch бот для отображения текущего трека из Яндекс Музыки

Показывает зрителям, какая музыка играет у стримера прямо сейчас.

</div>

---

## Возможности

* 🎶 Получение текущего трека из Яндекс Музыки
* 💬 Интеграция с Twitch Chat
* 🔄 Автоматическое обновление Twitch OAuth токенов
* 🔐 Авторизация в Яндекс Музыке через встроенное GUI-окно
* 🧩 Гибкая система регистрации команд
* 📝 Логирование в консоль и файл
* 🔗 Автоматическое сокращение ссылок на треки

## Поддерживаемые команды

| Команда   | Описание              |
| --------- | --------------------- |
| `!np`     | Показать текущий трек |
| `!song`   | Показать текущий трек |
| `!music`  | Показать текущий трек |
| `!песня`  | Показать текущий трек |
| `!музыка` | Показать текущий трек |

### Пример ответа

```text
Bring Me The Horizon - Kingslayer: clck.ru/xxxxx
```

---

## Как это работает

```text
Twitch Chat
     │
     ▼
CommandRegistry
     │
     ▼
YandexMusicService
     │
     ▼
Yandex Music
     │
     ▼
Информация о треке
     │
     ▼
Ответ в Twitch Chat
```

---

## Стек технологий

* Python 3.11+
* twitchAPI
* yandex-music
* aiohttp
* python-dotenv
* PyQt6
* PyQt6-WebEngine

---

## Структура проекта

```text
LeoshaBot/
│
├── commands/
│   └── np.py
│
├── core/
│   ├── command_registry.py
│   ├── twitch_bot_service.py
│   └── yandex_music_service.py
│
├── utils/
│   ├── get_ya_token.py
│   └── short_url.py
│
├── main.py
├── logging_config.py
├── bot.log
└── .env
```

---

## Установка

### Клонирование репозитория

```bash
git clone https://github.com/Moro1p/LeoshaBot.git
cd LeoshaBot
```

### Создание виртуального окружения

```bash
python -m venv .venv
```

### Активация

#### Windows

```bash
.venv\Scripts\activate
```

#### Linux / macOS

```bash
source .venv/bin/activate
```

### Установка зависимостей

```bash
pip install -r requirements.txt
```

---

## Настройка Twitch

1. Перейдите на https://dev.twitch.tv/console/apps
2. Создайте новое приложение.
3. Получите:

   * Client ID
   * Client Secret

Создайте файл `.env`:

```env
APP_ID=your_client_id
APP_SECRET=your_client_secret
TARGET_CHANNEL=your_channel_name

TW_REF_TOKEN=
YA_AC_TOKEN=
```

### Параметры

| Переменная     | Описание                        |
| -------------- | ------------------------------- |
| APP_ID         | Client ID приложения Twitch     |
| APP_SECRET     | Client Secret приложения Twitch |
| TARGET_CHANNEL | Канал для подключения           |
| TW_REF_TOKEN   | Refresh Token Twitch            |
| YA_AC_TOKEN    | Токен Яндекс Музыки             |

---

## Настройка Яндекс Музыки

При первом запуске бот проверяет наличие переменной:

```env
YA_AC_TOKEN=
```

Если токен отсутствует:

1. Автоматически откроется окно авторизации.
2. Выполните вход в аккаунт Яндекс.
3. Токен будет сохранён в `.env`.

Повторная авторизация обычно не требуется.

---

## Запуск

```bash
python main.py
```

После успешного запуска в логах появится сообщение:

```text
App is ready to work
```

---

## Добавление собственных команд

Создайте обработчик:

```python
async def hello_handler(cmd):
    await cmd.send("Hello, chat!")
```

Зарегистрируйте его:

```python
registry.register("hello", hello_handler)
```

После запуска команда станет доступна в чате:

```text
!hello
```

---

## Логирование

Используется встроенная система логирования Python.

Логи записываются:

* в консоль
* в файл `bot.log`

Особенности:

* ротация файлов
* максимальный размер файла: 10 МБ
* хранение до 5 архивов

---

## Пример использования API команд

```python
async def np_handler(cmd):
    await execute(cmd, ym_service)

registry.register("np", np_handler)
```

Получение текущего трека:

```python
track = await ym_service.get_track()
```

Результат:

```python
{
    "success": True,
    "title": "Track Name",
    "artists": ["Artist"],
    "album": "Album",
    "link": "clck.ru/xxxxx"
}
```

---

## Известные ограничения

* Работает только с аккаунтом Яндекс Музыки.
* Для получения информации о треке требуется активное воспроизведение.
* Требуется GUI для первичной авторизации Яндекс Музыки.

---

## Планы развития

* [ ] Docker поддержка
* [ ] Поддержка Spotify
* [ ] Веб-интерфейс управления
* [ ] Горячая перезагрузка команд
* [ ] Конфигурация через YAML
* [ ] Поддержка нескольких Twitch-каналов
* [ ] Кэширование данных о треках

---

## Лицензия

Проект распространяется по лицензии MIT.

---

## Автор

**Moro1p**

GitHub: https://github.com/Moro1p
