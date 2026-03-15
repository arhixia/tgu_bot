# README — Деплой и первоначальная настройка

## 1. Переменные окружения

Создать файл `.env` в корне проекта:
```env
# Telegram
TOKEN=тг_токен

# База данных
DB_HOST=...
DB_PORT=...
DB_NAME=...
DB_USER=...
DB_PASS=...

# Yandex Cloud (LLM + OCR)
YANDEX_CLOUD_FOLDER=""   # папка в Yandex Cloud
YANDEX_CLOUD_API_KEY=""  # API ключ
YANDEX_OAUTH_TOKEN=""    # OAuth токен

# S3 (Selectel, приватное хранилище)
ACCESS_KEY_S3=""
SECRET_KEY_S3=""
ENDPOINT_URL_S3="https://s3.ru-1.storage.selcloud.ru"
BUCKET_NAME_S3=""
```

---

## 2. Миграции базы данных

Выполнить из корня проекта:
```bash
alembic revision --autogenerate
```

Проверить сгенерированный файл в `migrations/versions/` и если всё корректно:
```bash
alembic upgrade head
```

---

## 3. Запуск бота
```bash
python -m src.main
```

---

## 4. Первоначальное наполнение БД

Выполнять SQL-запросы строго по порядку.

### 4.1 Создать преподавателя

> `telegram_id` 
```sql
INSERT INTO users (telegram_id, name, role)
VALUES ('123456789', 'Иванов Иван Иванович', 'teacher');
```

### 4.2 Создать группу и привязать к преподавателю
```sql
INSERT INTO groups (name, teacher_id)
VALUES ('ГРУППА1', 1);
--                  ^ id преподавателя из шага 4.1
```

### 4.3 Создать студента и добавить в группу
```sql
INSERT INTO users (telegram_id, name, role, group_id)
VALUES ('987654321', 'Петров Пётр', 'student', 1);
--                                              ^ id группы из шага 4.2
```

### 4.4 Привязать преподавателя к группе
```sql
UPDATE users
SET group_id = 1        -- id группы из шага 4.2
WHERE id = 1;           -- id преподавателя из шага 4.1
```

### 4.5 Добавить темы
```sql
INSERT INTO themes (name, llm_prompt, theory)
VALUES (
    'Метод замены переменной',
    'промпт для LLM',
    'текст теории для студентов'
);
```

---

## Итог

После выполнения всех шагов в системе есть:
- один преподаватель и один студент, работающие в рамках одной группы
- темы, по которым преподаватель может генерировать задания через бота

