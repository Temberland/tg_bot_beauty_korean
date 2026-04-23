# 🌸 K-Beauty Telegram Bot

## Быстрый старт

### Требования
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows / Mac / Linux)

### Установка

1. Скопируй файл `.env.example` и переименуй в `.env`:
   ```
   cp .env.example .env
   ```

2. Открой `.env` и заполни:
   ```
   BOT_TOKEN=токен_от_BotFather
   ADMIN_IDS=[твой_telegram_id]
   ```
   > Узнать свой Telegram ID можно у бота @userinfobot

3. Запусти:
   ```
   docker compose up -d
   ```

4. Готово! Бот запущен. Посмотреть логи:
   ```
   docker compose logs -f bot
   ```

### Остановка
```
docker compose down
```

### Полная остановка с удалением базы данных
```
docker compose down -v
```

---

## Структура проекта

```
├── bot/
│   ├── handlers/       # Обработчики команд и callback-ов
│   ├── keyboards/      # Inline и reply клавиатуры
│   ├── filters/        # Фильтр IsAdmin
│   ├── middlewares/    # Middleware сессии БД
│   └── states/         # FSM состояния
├── db/
│   ├── models.py       # SQLAlchemy модели
│   └── repository.py   # Репозитории для работы с БД
├── main.py             # Точка входа
├── config.py           # Настройки через pydantic-settings
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

## Примечания

- База данных хранится в Docker volume `postgres_data` — данные сохраняются между перезапусками
- При первом запуске таблицы создаются автоматически
- Если бот не подключается к Telegram — нужен VPN или прокси
