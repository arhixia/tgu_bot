для девопса:
создать .env  файл в корне проекта с:
ТГ:
TOKEN=тг токен

ДБ:
DB_HOST=...
DB_PORT=...
DB_NAME=...
DB_USER=...
DB_PASS=...

LLM:
YANDEX_CLOUD_FOLDER = "" ваша папка в yandex cloud 
YANDEX_CLOUD_API_KEY = "" апи ключ 
YANDEX_OAUTH_TOKEN="" 0auth token 

S3: (я использовал селектел,приватное хранилище)
ACCESS_KEY_S3 = ''
SECRET_KEY_S3 = ''
ENDPOINT_URL_S3 = 'https://s3.ru-1.storage.selcloud.ru'
BUCKET_NAME_S3 = ''

провести миграции в бд
в корне проекта
alembic revision --autogenerate 
alembic upgrade head (если убедились что все в порядке в migrations/version/ревизия)

сам бот запускается с корня проекта 
python -m src.main

чтобы начать работу в боте в бд мы добавляем следующее:
1) Создаем преподавателя 
insert into users (telegram_id, name, role)
VALUES ('123456789', 'Иванов Иван Иванович', 'teacher');

2) Создать группу и привязать к преподавателю
insert into groups (name, teacher_id)
VALUES ('ГРУППА1', 1); (id преподавателя в пункте 1)

3) Создать студента и добавить в группу
insert into users (telegram_id, name, role, group_id)
VALUES ('987654321', 'Петров Пётр', 'student', 1); 

4) Обновим преподавателя и присвоим ему тоже группу 
update users set group_id = 1 where id = id_преподавателя

5) Вставляем также темы
insert into themes (name, llm_prompt, theory)
VALUES (
    'Метод замены переменной',
    'промпт',
    'теория'
);

итого:
есть два юзера уже которые работают в пределах своей группы 

