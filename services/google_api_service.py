import csv
from datetime import datetime
from io import BytesIO

import pandas as pd
from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import ServiceAccountCreds
from openpyxl import load_workbook
from sqlalchemy.exc import IntegrityError

from core.db import async_session, engine
from crud.report import report_crud
from settings import Config, configure_logging

logger = configure_logging()

FORMAT = '%Y_%m_%d-%H:%M:%S'
ROW_COUNT = 1000
COLUMN_COUNT = 12
SHEETS_VER = 'v4'
DRIVE_VER = 'v3'
TABLE_RANGE = 'A1:L999'

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

INFO = {
    'type': Config.TYPE,
    'project_id': Config.PROJECT_ID,
    'private_key_id': Config.PRIVATE_KEY_ID,
    'private_key': Config.PRIVATE_KEY,
    'client_email': Config.CLIENT_EMAIL,
    'client_id': Config.CLIENT_ID,
    'auth_uri': Config.AUTH_URI,
    'token_uri': Config.TOKEN_URI,
    'auth_provider_x509_cert_url': Config.AUTH_PROVIDER_X509_CERT_URL,
    'client_x509_cert_url': Config.CLIENT_X509_CERT_URL
}

cred = ServiceAccountCreds(scopes=SCOPES, **INFO)


async def get_spreadsheets_id(wrapper_services: Aiogoogle, name: str):
    service = await wrapper_services.discover('drive', DRIVE_VER)
    spreadsheets = await wrapper_services.as_service_account(
        service.files.list(
            q=f"name = '{name}' and mimeType = 'application/vnd.google-apps.spreadsheet'"
        )
    )
    if len(spreadsheets['files']) >= 1:
        if len(spreadsheets['files']) > 1:
            logger.warning(
                f'Обнаружено несколько файлов с именем {name}'
            )
        return spreadsheets['files'][0]['id']
    elif len(spreadsheets['files']) == 0:
        return None


# TODO: Данная функция требется только на стадии разработки, по завершению ее можно удалить
async def delete_all_files_by_name(
        wrapper_services: Aiogoogle,
        chanal_name: str
):
    """
    Служебная функция для удаления всех файлов имеющих определенное название. 
    Нужна чтоы удалять файлы, которые были созданы, 
    но не видны у собственника аккаунта google
    """
    service = await wrapper_services.discover('drive', DRIVE_VER)
    spreadsheets = await wrapper_services.as_service_account(
        service.files.list(q=f"name = '{chanal_name}'")
    )
    for item in spreadsheets['files']:
        await wrapper_services.as_service_account(
            service.files.delete(fileId=item['id'])
        )
    print(f"All files with name {chanal_name} delete.")


async def spreadsheets_create(
        wrapper_services: Aiogoogle,
        chanal_name: str) -> str:
    now_date_time = datetime.now().strftime(FORMAT)
    service = await wrapper_services.discover('sheets', SHEETS_VER)
    sheet_title = f'report_{now_date_time}'
    spreadsheet_body = {
        'properties': {'title': f'{chanal_name}',
                       'locale': 'ru_RU'},
        'sheets': [{'properties': {'sheetType': 'GRID',
                                   'sheetId': 0,
                                   'title': sheet_title,
                                   'gridProperties': {
                                        'rowCount': ROW_COUNT,
                                        'columnCount': COLUMN_COUNT
                                    }}}]
    }
    response = await wrapper_services.as_service_account(
        service.spreadsheets.create(json=spreadsheet_body)
    )
    spreadsheetid = response['spreadsheetId']
    return spreadsheetid, sheet_title


async def spreadsheets_create_new_list(
        wrapper_services: Aiogoogle,
        spreadsheetid: str
):
    now_date_time = datetime.now().strftime(FORMAT)
    service = await wrapper_services.discover('sheets', SHEETS_VER)
    sheet_title = f'report_{now_date_time}'
    spreadsheet_body = {
        'requests': [
            {
                'addSheet': {
                    'properties': {
                        'title': sheet_title,
                        'gridProperties': {
                            'rowCount': ROW_COUNT,
                            'columnCount': COLUMN_COUNT
                        }
                    }
                }
            }
        ]
    }
    await wrapper_services.as_service_account(
        service.spreadsheets.batchUpdate(
            spreadsheetId=spreadsheetid,
            json=spreadsheet_body
        )
    )

    return sheet_title


async def set_user_permissions(
        spreadsheetid: str,
        wrapper_services: Aiogoogle
) -> None:
    #На релизе поменять обратно.
    permissions_body = {'type': 'user',
                        'role': 'writer',
                        'emailAddress': Config.EMAIL}
    # permissions_body = {'type': 'anyone',
    #                     'role': 'reader'}
    service = await wrapper_services.discover('drive', DRIVE_VER)
    await wrapper_services.as_service_account(
        service.permissions.create(
            fileId=spreadsheetid,
            json=permissions_body,
            fields='id'
        ))


async def spreadsheets_update_value(
        spreadsheetid: str,
        sheet_title: str,
        data: dict,
        wrapper_services: Aiogoogle
) -> None:
    service = await wrapper_services.discover('sheets', SHEETS_VER)
    table_values = []
    # Запись информации об активности
    logger.debug('Подготовка информации об активности для записи в таблицу')
    table_values.append(['Активность', 'Среднее количество'])
    for activity, amount in data['Активности'].items():
        new_row = [
            activity, amount
        ]
        table_values.append(new_row)
    logger.debug(
        'Подготовка информации об активности для записи в таблицу завершена'
    )
    table_values.append([])  # Пустая строка

    # Запись информации подписчиках
    logger.debug('Подготовка информации о подписчиках для записи в таблицу')
    table_values.append(
        ['ID', 'Username', 'Имя', 'Язык пользователя',
         'Дата подписки на канал', 'Статус подписчика', 'Это бот?', 'Фото'])

    for follower in data['Подписчики']:
        new_row = [
            follower['ID'],
            follower['Username'],
            follower['Имя'],
            follower['Язык пользователя'],
            follower['Дата вступления'],
            follower['Статус подписчика'],
            follower['Это бот ?'],
            follower['Фото']
        ]
        table_values.append(new_row)
    logger.debug(
        'Подготовка информации о подписчиках для записи в таблицу завершена'
    )

    update_body = {
        "valueInputOption": "USER_ENTERED",
        "data": [
            {
                "range": f'{sheet_title}!{TABLE_RANGE}',
                "majorDimension": "ROWS",
                "values": table_values
            }
        ]
    }
    await wrapper_services.as_service_account(
        service.spreadsheets.values.batchUpdate(
            spreadsheetId=spreadsheetid,
            json=update_body
        )
    )


async def get_report(
    data: dict
):
    """Создание отчета в Google spreadsheets."""
    async with Aiogoogle(service_account_creds=cred) as aiogoogle:
        reports_url = []
        for chanal_name, data in data.items():
            # await delete_all_files_by_name(aiogoogle, chanal_name) # TODO Не забыть удалить перед релизом
            spreadsheetid = await get_spreadsheets_id(aiogoogle, chanal_name)
            if spreadsheetid is None:
                spreadsheetid, sheet_title = await spreadsheets_create(
                    aiogoogle, chanal_name
                )
                logger.info(
                    f'Создана таблица {chanal_name} с листом {sheet_title}'
                )
                await set_user_permissions(spreadsheetid, aiogoogle)
                logger.info(
                    f'Таблице {chanal_name} установлены разрешения'
                )
            else:
                sheet_title = await spreadsheets_create_new_list(
                    aiogoogle, spreadsheetid
                )
                logger.info(
                    f'В таблицу {chanal_name} добавлен лист {sheet_title}'
                )
            await spreadsheets_update_value(spreadsheetid,
                                            sheet_title,
                                            data,
                                            aiogoogle)
            url = f'https://docs.google.com/spreadsheets/d/{spreadsheetid}'
            logger.info(
                f'Отчет по каналу {chanal_name} сформирован: URL {url}'
            )
            async with async_session() as session:
                async with engine.connect():
                    try:
                        await report_crud.create(
                            {
                                'link': url,
                                'group': chanal_name,
                                'sheet_id': spreadsheetid
                            },
                            session=session
                        )
                    except IntegrityError:
                        logger.info(f'Ссылка {url} уже существует, не '
                                    'записываем!')
                reports_url.append(
                    f'Отчет по каналу {chanal_name} сформирован: {url}'
                )
        return reports_url

# async def list_files():
#     async with Aiogoogle(service_account_creds=cred) as aiogoogle:
#         service = await aiogoogle.discover('drive', 'v3')
#         json_res = await aiogoogle.as_service_account(
#             service.files.list(),
#         )
#         for file in json_res['files']:
#             print(file['name'])


async def get_one_spreadsheet(
        spreadsheetId,
        path: str,
        format: str = 'xlsx'
        ):
    """Получает данные одного документа из Google."""

    async with Aiogoogle(service_account_creds=cred) as aiogoogle:
        service = await aiogoogle.discover('drive', DRIVE_VER)
        file = await aiogoogle.as_service_account(
            service.files.export(
                fileId=spreadsheetId,
                mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                ),
        )
        xlsx = load_workbook(filename=BytesIO(file))
        xlsx.save(f'{path}.xlsx')
        if format == 'CSV':
            df = pd.DataFrame(pd.read_excel(f'{path}.xlsx'))
            df.to_csv(f'{path}.csv')
        return file


async def get_spreadsheet_data(spreadsheetId):
    """
    Для одиночного отчета.
    Получение данных по spreadsheetId
    Возвращает словарь для формирования текстового отчета
    """

    async with Aiogoogle(service_account_creds=cred) as aiogoogle:
        service = await aiogoogle.discover('sheets', SHEETS_VER)

        data = (await aiogoogle.as_service_account(
            service.spreadsheets.values.get(
                spreadsheetId=spreadsheetId,
                range='A1:B4'
            )
        ))['values']

        return {
            'avr_views': data[1][1],
            'avr_reaction': data[2][1],
            'avr_reposts': data[3][1]
        }


async def get_sheets_title(spreadsheetId):
    """Получение списка тайтлов листов из файла."""

    async with Aiogoogle(service_account_creds=cred) as aiogoogle:
        service = await aiogoogle.discover('sheets', SHEETS_VER)

        data = await aiogoogle.as_service_account(
            service.spreadsheets.get(spreadsheetId=spreadsheetId)
        )
        sheet_titles = []
        for sheet in data['sheets']:
            sheet_titles.append(sheet['properties']['title'])
        return sheet_titles


async def get_data_from_sheet(sheet, spreadsheetId):
    """Получение информации из листа."""

    async with Aiogoogle(service_account_creds=cred) as aiogoogle:
        service = await aiogoogle.discover('sheets', SHEETS_VER)

        return (await aiogoogle.as_service_account(
            service.spreadsheets.values.get(
                spreadsheetId=spreadsheetId,
                range=f'{sheet}!A1:B4'
            )
        ))


async def get_data_for_shedule(spreadsheetId):
    """Сбор информации для графиков."""

    sheets = await get_sheets_title(spreadsheetId)
    avr_views = {}
    avr_reactions = {}
    avr_reposts = {}

    for sheet in sheets:
        data_from_sheet = await get_data_from_sheet(sheet, spreadsheetId)
        date = sheet.lstrip('report_')
        avr_views[date] = data_from_sheet['values'][1][1]
        avr_reactions[date] = data_from_sheet['values'][2][1]
        avr_reposts[date] = data_from_sheet['values'][3][1]

    return avr_views, avr_reactions, avr_reposts
