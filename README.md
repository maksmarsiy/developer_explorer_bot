# Developer Explorer Bot

**Version 1.0 — Production**

Telegram-бот для поиска и изучения open-source проектов на GitHub. Бот развёрнут на Ubuntu VPS через Docker Compose и получает обновления Telegram в режиме long polling.

## Возможности

- Поиск по направлениям разработки (Backend, Frontend, AI/ML, Data, DevOps, Mobile, Game Development), языкам программирования и ключевым словам.
- Повторный поиск без дублирования репозиториев в рамках текущего запроса.
- Карточки проектов с описанием, языком, количеством звёзд и форков, датой обновления и ссылкой на GitHub.
- История последних 10 просмотренных репозиториев для каждого пользователя.
- Уведомления о сетевых ошибках и ограничениях GitHub API.

Текстовый поиск выдаёт до трёх новых репозиториев за запрос и просматривает до пяти страниц GitHub API по 100 репозиториев за нажатие. После исчерпания результатов бот предлагает начать новый поиск.

## Технологический стек

| Технология | Назначение |
|---|---|
| Python 3.14, asyncio | Асинхронное выполнение |
| aiogram 3, Telegram Bot API | Обработка сообщений, меню и состояний диалога |
| httpx, GitHub REST API | Асинхронные запросы к GitHub |
| SQLite, aiosqlite | Хранение истории просмотров |
| python-dotenv | Загрузка конфигурации из `.env` |
| Docker Engine, Docker Compose, Ubuntu | Сборка и запуск на VPS |
| pytest | Автоматическое тестирование |
| Git | Контроль версий |

## Архитектура и структура проекта

`main.py` инициализирует SQLite, настраивает HTTP-клиент GitHub и запускает Telegram long polling. FSM управляет диалогом, а `asyncio.Lock` и проверка актуальности запроса защищают от конфликтов при параллельных поисках. Для запросов к GitHub задан тайм-аут, а операции SQLite используют параметризованные запросы.

```text
developer_explorer_bot/
├── data/              # Справочники, модели callback и состояния FSM
├── database/          # Подключение к SQLite и история просмотров
├── handlers/          # Обработчики сообщений и кнопок Telegram
├── keyboards/         # Пользовательские меню
├── services/          # Интеграция с GitHub API
├── tests/             # Автоматические тесты
├── data_storage/      # Постоянное хранилище SQLite на хосте
├── main.py            # Точка входа
├── requirements.txt  # Зависимости Python
├── Dockerfile         # Сборка образа на базе python:3.14-slim
├── compose.yaml       # Сервис bot, хранилище и политика перезапуска
├── .dockerignore      # Исключения из контекста сборки
├── .env.example       # Шаблон конфигурации
└── README.md
```

## Установка и настройка

Клонируйте репозиторий, подставив имя его владельца, и создайте `.env` из шаблона при первой настройке.

```bash
git clone https://github.com/YOUR_USERNAME/developer_explorer_bot.git
cd developer_explorer_bot
cp .env.example .env
chmod 600 .env
```

Заполните `BOT_TOKEN` токеном Telegram-бота, а `GITHUB_TOKEN` — токеном GitHub. Храните рабочие значения в файле `.env`, исключённом из Git и контекста сборки Docker.

### Локальный запуск

Для запуска без Docker требуется Python 3.14.

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Запуск через Docker Compose на Ubuntu VPS

Подключитесь к VPS по SSH, установите Git, Docker Engine и плагин Docker Compose (`docker-compose-plugin`). Выполните шаги из раздела «Установка и настройка» на сервере. [Инструкция по установке Docker на Ubuntu](https://docs.docker.com/engine/install/ubuntu/)

Включите запуск Docker при загрузке сервера. Выполняйте команды Compose из каталога проекта с правами доступа к Docker.

```bash
sudo systemctl enable --now docker
docker compose version
mkdir -p data_storage
docker compose up -d --build
docker compose ps
docker compose logs --tail=50 bot
```

Compose собирает локальный образ, передаёт переменные из `.env` и запускает сервис `bot` в контейнере `developer-explorer-bot` без публикации портов. Для работы бота нужен исходящий HTTPS-доступ к Telegram и GitHub. Проверьте запуск командой `/start` в Telegram.

## Хранение SQLite

Бот инициализирует базу при запуске. При локальном запуске по умолчанию используется `bot.db` в корне проекта. Переменная `DB_PATH` позволяет задать другой путь, а относительные пути вычисляются от корня проекта.

В Compose значение `DB_PATH` задано в `compose.yaml` и переопределяет значение из `.env`. Файл `/app/storage/bot.db` внутри контейнера соответствует `./data_storage/bot.db` на хосте благодаря bind mount `./data_storage:/app/storage`. Каталог должен быть доступен контейнеру на запись. История сохраняется при перезапуске и пересоздании контейнера, пока сохранён каталог `data_storage/` на хосте.

## Управление контейнером

| Действие | Команда |
|---|---|
| Проверить состояние | `docker compose ps` |
| Смотреть журналы | `docker compose logs --tail=100 -f bot` |
| Перезапустить | `docker compose restart bot` |
| Остановить | `docker compose stop bot` |
| Запустить после остановки | `docker compose start bot` |
| Пересобрать после обновления кода | `docker compose up -d --build` |
| Применить изменения в `.env` | `docker compose up -d --force-recreate bot` |

Политика `restart: unless-stopped` перезапускает контейнер при завершении процесса бота и поднимает его после перезагрузки VPS при запуске Docker. После ручной остановки через `docker compose stop bot` контейнер остаётся остановленным до явного запуска. [Политики перезапуска Docker](https://docs.docker.com/engine/containers/start-containers-automatically/)

## Тестирование

Установите зависимости проекта в локальное виртуальное окружение, затем запустите тесты.

```bash
pip install pytest
python -m pytest -v
```

Тесты покрывают конфигурацию, работу с GitHub API, пагинацию и исключение дублей, историю и обновление схемы SQLite, обработку ошибок HTTP и SQLite и конкурентный поиск с FSM. Используются моки и временные базы данных без запросов к реальному GitHub API.
