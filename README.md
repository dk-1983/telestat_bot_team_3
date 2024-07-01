# TELESTAT_BOT

## Проект telestat_bot - 
### это два бота собирающие статистику о пользователях из телеграмм каналов владельца каналов либо тех каналов где бот зарегистрирован как администратор.
Интерфейс управления ботом организован непосредственно через интерфейс телеграмм.\
Статистика обрабатывается и отправляется в Google spreadsheets для хранения в электронных таблицах.\
Второй бот получает собранную статистику конвертирует её в форматы на выбор пользователя CSV, xlsx и
передаёт в чат телеграмм в виде файлов, которые получает администратор бота.\
Организована ролевая система, владелец бота может создавать или удалять
администратора бота. Администратор бота в свою очередь может управлять ботом после занесения администратора в базу данных,
администраторов может быть несколько.\
Владелец программного обеспечения управляет администраторами, администраторы управляют ботом. Бот работает в канале и незаметен для пользователей канала, с которого производится сбор аналитической информации.\
Два бота работают в разных потоках, что позволяет им работать одновременно в рамках программы. После программирования ботов
администраторами боты уходят в рекурсию и по заданным временным критериям работают автономно по заданным алгоритмам.
В это время администратор ботов или владелец программного обеспечения может программировать новых ботов для работы в других каналах. Программное обеспечение написано в асинхронном стиле.

## Технологии и библиотеки

* [Python](https://www.python.org/)
* [Pyrogram](https://docs.pyrogram.org/)
* [SQLAlchemy](https://pypi.org/project/SQLAlchemy/)
* [Alembic](https://pypi.org/project/alembic/)
* [Asyncio](https://docs.python.org/3/library/asyncio.html)
* [Aiogoogle](https://aiogoogle.readthedocs.io/en/latest/)

## Установите и настройте систему контроля версий репозиториев GIT,
## создайте ключ для ssh сессий с GitHub выполните команду:

* [GIT](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git/)

```
git clone git@github.com:Studio-Yandex-Practicum/telestat_bot_team_3.git
```

## Настройка проекта и организация подключения к базе данных PostgresSQL.

### Создать рабочую директорию проекта по вашему пути на сервере, 
### my_work_directory/
### Для настройки проекта необходимо установить:

* Python версии 3.11.4 или выше

### Выполнить следующие команды для конфигурации "virtual enviroments" OS Windows
### и устанавливаем все необходимые зависимости проекта:
### Внимание для OS Linux команды будут отличаться!

```
python -m venv venv
source venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Настройка подключения SQLAlchemy и Alembic для взаимодействия с Postgres:

Необходимо выполнить команду инициализации работы Alembic из консоли
находясь в рабочей директории проекта
```
alembic init --template async alembic
```

### Создать в корневой директории проекта файл .env и заполнить в нём следующее:

```
DB_URI=postgresql+asyncpg://you_username:you_password@10.0.0.7/you_database_name
API_ID=12345678
API_HASH=9999aa9aa9a9999a99a999aa9a599a99
BOT_TOKEN=1234567890:AAAzz2z2zzzPzPPz1zVCz0zzfXz_Kzz1234
BOT2_TOKEN=7193774287:AAG5PQuCD-MsN5A4ZUx4BXG1PznRzwtxYnI
PHONE_NUMBER='+79138552500'
BOT_ACCOUNT_NAME='@KrivolapDmitriyBot'
BOT2_ACCOUNT_NAME='@SircleBot'
USER_ACCOUNT_NAME='@dk06789'

PATH_TO_DOWNLOADS='downloads/'

TYPE=service_account
PROJECT_ID=apibot12345
PRIVATE_KEY_ID=943372222222222222222222f08bbb99eb
PRIVATE_KEY=-----BEGIN PRIVATE KEY----------END PRIVATE KEY-----\n
CLIENT_EMAIL=apibot@apibot-423555.example.gserviceaccount.com
CLIENT_ID=1111111111111111111111
AUTH_URI=https://accounts.google.com/o/oauth2/auth
TOKEN_URI=https://oauth2.googleapis.com/token
AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/apibot%40apibot-423905.iam.gserviceaccount.com
UNIVERSE_DOMAIN=googleapis.com
EMAIL=examle@gmail.com
```

Где DB_URI - с параметрами подлкючения вашего сервера
    API_ID, API_HASH - это ваши данные из телеграмм для работы с api
    [Telegram APIs](https://core.telegram.org/) читайте здесь!
    BOT_TOKEN - уникальный ключ вашего бота.

### В сформированной автоматически папке Alembic необходимо внести правки в файл
### env.py следующим образом:

```
import asyncio
import os  ## Необходимо добавить-----------------------------------------------------
from logging.config import fileConfig

from dotenv import load_dotenv  ## Необходимо добавить--------------------------------
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from core.base import Base  ## Необходимо добавить------------------------------------

load_dotenv('.env')  ## Необходимо добавить-------------------------------------------

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

config.set_main_option('sqlalchemy.url', os.environ['DB_URI'])  ## Необходимо добавить

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata
```

### В сформированном в корневой директории файле Alembic.ini необходимо внести правки:
### по умолчанию параметр version_path_separator = None, Нужно исправить на os.

```
version_path_separator = os  # Use os.pathsep. Default configuration used for new projects.
```

### Когда все указанные выше настройки произведены система готова к работе и вы сможете 
### подключиться к Postgres и вносить изменения в таблицы, Виды Функции и Триггеры Postgress
### из кода Python работающего из виртуального окружения вашей копии проекта sysinfo_bot.
### Подразумевается что база данных Postgress у вас уже установлена на удалённом сервере и готова
### принимать подключения пользователей.

Для того чтобы управлять системой commit Alembic необходимо изучить alembic --help

Команды для создания необходимых таблиц счётчиков последовательностей и прочих необходимых компонентов
для работы приложения.

```
alembic revision --autogenerate -m "This Your're commit text."
alembic upgrade head

```

## Информация об авторе

[Криволап Дмитрий Александрович](https://dk.4vrs.ru)
