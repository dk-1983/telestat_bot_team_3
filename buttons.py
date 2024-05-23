from assistants.assistants import DotNotationDict

bot_keyboard = [
    {
        'key_name': 'Добавить администратора'
    },
    {
        'key_name': 'Удалить администратора'
    },
    {
        'key_name': 'Выбрать телеграм канал'
    },
    {
        'key_name': 'Установить период сбора данных'
    },
    {
        'key_name': 'Начать сбор аналитики'
    },
    {
        'key_name': 'Автоматическое формирование отчёта'
    },
    {
        'key_name': 'Формирование отчёта'
    },
    {
        'key_name': 'Формирование графика'
    },
    {
        'key_name': '1 час'
    },
    {
        'key_name': '5 часов'
    },
    {
        'key_name': '10 часов'
    },
    {
        'key_name': '15 часов'
    },
    {
        'key_name': '24 часа'
    },
    {
        'key_name': 'Свой вариант'
    },
    {
        'key_name': "Остановить сбор аналитики"
    },
    {
        'key_name': 'csv'
    },
    {
        'key_name': 'xlsx'
    },
    {
        'key_name': "it's comming..."
    },
]

bot_keys = []
for dict_out in bot_keyboard:
    bot_keys.append(DotNotationDict(dict_out))
