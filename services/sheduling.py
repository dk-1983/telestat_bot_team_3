from datetime import datetime
from typing import Literal

import matplotlib.pyplot as plt


FORMAT_SHEDULE = '%Y-%m-%d_%H_%M_%S'


async def build_shedule(
    data: dict[str, str],
    to_title: Literal['просмотров', 'реакций', 'репостов']
):
    """Сохраняет изображение графика, возвращает имя графика"""

    time_now = datetime.now().strftime(FORMAT_SHEDULE)
    times = []
    values = []

    for time, value in data.items():
        times.append(time)
        values.append(float(value))

    name = f'imgs/График {to_title} {time_now}'
    name = 'Актуальный_график'
    plt.plot(times, values)
    plt.title(f'График изменения {to_title}')
    plt.xlabel('Дата')
    plt.ylabel('Значение')
    plt.savefig(fname=name)
    return name
