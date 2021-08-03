import re
from datetime import datetime


def is_date_valid(
    user_date: str,
    user_date_2: str or None = None,
    check_two_dates: bool = False,
) -> str or bool:
    """
    Функция конвертации из привычного для пользователя
    формата даты (ДД.ММ.ГГГГ) в формат пригодный
    для запроса в API (ГГГГ-ММ-ДД)
    Также функция может проверять, что дата №2
    определена не раньше, чем дата №1
    :param user_date: str
    :param user_date_2: str or None
    :param check_two_dates: bool
    :return: str or bool
    """
    try:
        convert = datetime.strptime(user_date, '%d.%m.%Y').date()
        if abs(int(convert.year - datetime.now().year)) > 10:
            return False
        if user_date_2 or check_two_dates:
            convert_2 = datetime.strptime(user_date_2, '%d.%m.%Y').date()
            return convert_2 >= convert
    except ValueError:
        return False
    return convert


def check_name(city_name: str) -> bool:
    """
    Функция для првоерки названия города.
    В названии города не должно цифр.
    :param city_name: str
    :return: bool
    """
    return (
               re.search(r'\d+', city_name)
           ) is None


def price_check(string: str):
    try:
        price_min, price_max = string.split('-')
        if int(price_max) < int(price_min):
            return False
    except ValueError:
        return False
    return price_min, price_max
