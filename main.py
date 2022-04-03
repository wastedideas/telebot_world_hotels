import gettext
import os
from typing import Any, Callable

import telebot
from dotenv import load_dotenv
from flask import Flask
from flask import request

from checks import *
from hotels_api_utils import (
    get_offers_on_request,
    get_country_by_city,
)
from peewee_models import UserModel

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
PROJECT_URL = os.getenv('PROJECT_URL')

bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)


@app.route('/' + BOT_TOKEN, methods=['POST'])
def get_message():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "ok", 200


@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=PROJECT_URL + BOT_TOKEN)
    return "ok", 200


@bot.message_handler(commands=['start'])
def start_message(message: Any):
    """
    Функция обратки команды /start и вывода приветственного сообщения
    :param message: Any
    :return:
    """
    keyboard = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    keyboard.row('/lowprice', '/highprice', '/bestdeal')
    keyboard.row('/help')
    keyboard.row('/en', '/ru')

    chat_id = message.chat.id
    user_nickname = message.chat.username

    try:
        chat_user = UserModel.get(
            (UserModel.chat_id == chat_id) &
            (UserModel.user_nickname == user_nickname)
        )
    except UserModel.DoesNotExist:
        chat_user = UserModel.create(
            chat_id=chat_id,
            user_nickname=user_nickname,
        )

    if not chat_user[1]:
        _ = gettext.translation(
            'chat_user_lang',
            localedir='locales',
            languages=[
                chat_user[0].get_language_display()
            ],
        ).gettext
    else:
        if message.from_user.language_code == 'ru':
            _ = gettext.translation(
                'chat_user_lang',
                localedir='locales',
                languages=[
                    chat_user[0].get_language_display()
                ],
            ).gettext

        else:
            chat_user[0].language = 'en_EN'
            chat_user[0].save()
            _ = gettext.translation(
                'chat_user_lang',
                localedir='locales',
                languages=[
                    chat_user[0].get_language_display()
                ],
            ).gettext

    start_text = _(
        'Hi, {username}! ✋\n'
        'I am ready to select hotels according to your request!\n'
        'For command help, use */help*\n'
        'To select a language, use the command */en* or */ru*').format(
        username=message.chat.first_name,
    )

    bot.send_message(
        message.chat.id, start_text,
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


@bot.message_handler(commands=['en', 'ru'])
def get_language(message: Any):
    """
    Функция обратки команд /en и /ru и установки языка
    для пользователя
    :param message: Any
    :return:
    """
    chat_user = UserModel.get(chat_id=message.chat.id)
    if message.text == '/en':
        chat_user.language = chat_user.EN
    elif message.text == '/ru':
        chat_user.language = chat_user.RU

    _ = gettext.translation(
        'chat_user_lang',
        localedir='locales',
        languages=[
            chat_user.get_language_display()
        ],
    ).gettext
    chat_user.save()
    change_language_text = _('Language changed successfully!')
    bot.send_message(message.chat.id, change_language_text)


@bot.message_handler(commands=['help'])
def help_message(message: Any):
    """
    Функция обработки команды /help, и вывода доступных команд
    :param message: Any
    :return:
    """
    chat_user = UserModel.get(chat_id=message.chat.id)
    _ = gettext.translation(
        'chat_user_lang',
        localedir='locales',
        languages=[
            chat_user.get_language_display()
        ],
    ).gettext
    help_string = _("*/help* — help with commands\n"
                    "*/lowprice* — listing of the cheapest hotels in the city\n"
                    "*/highprice* — conclusion of the most expensive hotels in the city\n"
                    "*/bestdeal* — conclusion of hotels with the closest location from the center")
    bot.send_message(
        message.chat.id,
        help_string,
        parse_mode='Markdown',
    )


@bot.message_handler(
    commands=[
        'lowprice',
        'highprice',
        'bestdeal',
    ]
)
def create_new_request(message: Any):
    """
    Функция обработки команд /lowprice, /highprice, /bestdeal
    И запуска функции запроса города для поиска
    :param message: Any
    :return:
    """
    chat_user = UserModel.get(chat_id=message.chat.id)

    if message.text == '/lowprice':
        chat_user.sort_order = 'PRICE'
    elif message.text == '/highprice':
        chat_user.sort_order = 'PRICE_HIGHEST_FIRST'
    elif message.text == '/bestdeal':
        chat_user.sort_order = 'DISTANCE_FROM_LANDMARK'

    _ = gettext.translation(
        'chat_user_lang',
        localedir='locales',
        languages=[
            chat_user.get_language_display()
        ],
    ).gettext

    country_text = _('Enter the country to search for a hotel:')

    country_message = bot.send_message(
        message.chat.id,
        country_text,
    )
    bot.register_next_step_handler(
        country_message,
        country_answer,
        _,
        chat_user,
    )


def incorrect_name(message: Any, _: gettext, chat_user: UserModel):
    """
    Функции обработки ввода некорректного
    названия города пользователем
    :param message: Any
    :param _: gettext
    :param chat_user: UserModel
    :return:
    """
    incorrect_city_text = _(
        'Incorrect name.\n'
        'Enter the country name in Latin.'
    )

    incorrect_city_message = bot.send_message(
        message.chat.id,
        incorrect_city_text,
    )
    bot.register_next_step_handler(
        incorrect_city_message,
        country_answer,
        _,
        chat_user,
    )


def country_answer(message: Any, _: gettext, chat_user: UserModel):
    """
    Функция обработки полученного названия страны от пользователя.
    И при корректности ввода запуска вопроса о рассматриваемом городе
    :param message: Any
    :param _: gettext
    :param chat_user: UserModel
    :return:
    """
    if message.text == 'rmh':
        cancel_registered_handlers(message)
        return
    chat_user.country = message.text

    city_text = _('Enter the city to search for a hotel:')

    city_message = bot.send_message(
        message.chat.id,
        city_text,
    )
    bot.register_next_step_handler(
        city_message,
        city_answer,
        _,
        chat_user,
    )


def city_answer(message: Any, _: gettext, chat_user: UserModel):
    """
    Функция обработки полученного названия города от пользователя.
    И при корректности ввода запуска вопроса о количестве
    расмматриваемых отелей
    :param message: Any
    :param _: gettext
    :param chat_user: UserModel
    :return:
    """
    if message.text == 'rmh':
        cancel_registered_handlers(message)
        return
    bot.send_message(
        message.chat.id,
        _('Checking the correctness of the city entry... ⚡'),
    )
    city_country_flag_dict = get_country_by_city(
        city=message.text,
        country=chat_user.country,
        lang=chat_user.language,
    )
    if not city_country_flag_dict:
        incorrect_name(message, _, chat_user)
    else:
        chat_user.city = city_country_flag_dict

        number_of_hotels_text = _('Enter the number of hotels you want to see (no more than 25):')

        number_of_hotels_message = bot.send_message(
            message.chat.id,
            number_of_hotels_text,
        )
        bot.register_next_step_handler(
            number_of_hotels_message,
            number_of_hotels_answer,
            _,
            chat_user
        )


def incorrect_hotels_number(message: Any, _: gettext, chat_user: UserModel):
    """
    Функции обработки ввода некорректного
    количества отелей пользователем
    :param message: Any
    :param _: gettext
    :param chat_user: UserModel
    :return:
    """
    incorrect_hotels_number_text = _(
        'Invalid format.\n'
        'Please enter a quantity not exceeding 25.'
    )
    incorrect_hotels_number_message = bot.send_message(
        message.chat.id,
        incorrect_hotels_number_text,
    )
    bot.register_next_step_handler(
        incorrect_hotels_number_message,
        number_of_hotels_answer,
        _,
        chat_user,
    )


def number_of_hotels_answer(message: Any, _: gettext, chat_user: UserModel):
    """
    Функция обработки полученного количества отелей от пользователя.
    При корректности ввода запуска вопроса
    о дате начала поиска
    :param message: Any
    :param _: gettext
    :param chat_user: UserModel
    :return:
    """
    if message.text == 'rmh':
        cancel_registered_handlers(message)
        return
    try:
        if not 0 < int(message.text) <= 25:
            incorrect_hotels_number(message, _, chat_user)
        else:
            chat_user.number_of_hotels = message.text

            check_in_text = _('Enter the search start date (DD.MM.YYYY):')

            check_in_message = bot.send_message(
                message.chat.id,
                check_in_text,
            )
            bot.register_next_step_handler(
                check_in_message,
                check_in_answer,
                _,
                chat_user,
            )

    except ValueError:
        incorrect_hotels_number(message, _, chat_user)


def incorrect_date(message: Any, from_func: Callable, _: gettext, chat_user: UserModel):
    """
    Функции обработки ввода некорректной
    даты поиска пользователем
    :param message: Any
    :param from_func: Callable
    :param _: gettext
    :param chat_user: UserModel
    :return:
    """
    incorrect_date_text = _('Invalid date format.')

    if from_func == check_in_answer:
        incorrect_date_text = _(
            'Date does not exist or is not in the correct format.\n'
            'Date format: DD.MM.YYYY.\n'
            'Enter search start date:'
        )
    elif from_func == check_out_answer:
        incorrect_date_text = _(
            'Date does not exist or is not in the correct format.\n'
            'Date format: DD.MM.YYYY\n'
            'The end date of the search must be later than the start date.\n'
            'Enter the end date of the search:'
        )
    incorrect_date_message = bot.send_message(
        message.chat.id,
        incorrect_date_text,
    )
    bot.register_next_step_handler(
        incorrect_date_message,
        from_func,
        _,
        chat_user,
    )


def check_in_answer(message: Any, _: gettext, chat_user: UserModel):
    """
    Функция обработки полученной даты начала поиска от пользователя.
    При корректности ввода запуска вопроса
    о дате конца поиска
    :param message: Any
    :param _: gettext
    :param chat_user: UserModel
    :return:
    """
    if message.text == 'rmh':
        cancel_registered_handlers(message)
        return
    if not is_date_valid(user_date=message.text):
        incorrect_date(message, check_in_answer, _, chat_user)
    else:
        chat_user.check_in = message.text

        check_out_text = _('Enter the end date of the search (DD.MM.YYYY):')

        check_out_message = bot.send_message(
            message.chat.id,
            check_out_text,
        )
        bot.register_next_step_handler(
            check_out_message,
            check_out_answer,
            _,
            chat_user,
        )


def check_out_answer(message: Any, _: gettext, chat_user: UserModel):
    """
    Функция обработки полученной даты конца поиска от пользователя.
    При корректности ввода и, если нет необходимости
    запрашивать у пользователя ценовой диапозон
    переходит к завершающей
    функции для выведения соответствующих
    критериям запроса отелей в указанном городе
    :param message: Any
    :param _: gettext
    :param chat_user: UserModel
    :return:
    """
    if message.text == 'rmh':
        cancel_registered_handlers(message)
        return
    check_in_date = chat_user.check_in

    check_out_date = message.text

    if not is_date_valid(
        user_date=check_in_date,
        user_date_2=check_out_date,
        check_two_dates=True,
    ):
        incorrect_date(
            message,
            check_out_answer,
            _,
            chat_user,
        )
    else:
        chat_user.check_out = is_date_valid(check_out_date)
        chat_user.check_in = is_date_valid(check_in_date)

        if chat_user.sort_order == 'DISTANCE_FROM_LANDMARK':
            price_range_text = _('Enter search price range in dollars\n'
                                 '(For example: "50-100"):')

            price_range_message = bot.send_message(
                message.chat.id,
                price_range_text,
            )
            bot.register_next_step_handler(
                price_range_message,
                price_range_answer,
                _,
                chat_user,
            )
        else:
            chat_user.min_price = ''
            chat_user.max_price = ''
            search_hotels_result(message, _, chat_user)


def incorrect_price(message: Any, _: gettext, chat_user: UserModel):
    """
    Функции обработки некорректного
    диапазона цен введенного пользователем
    :param message: Any
    :param _: gettext
    :param chat_user: UserModel
    :return:
    """
    incorrect_price_text = _('Incorrect price.\n'
                             'Please, enter price range\n'
                             'in dollars again:\n')

    incorrect_price_message = bot.send_message(
        message.chat.id,
        incorrect_price_text,
    )
    bot.register_next_step_handler(
        incorrect_price_message,
        price_range_answer,
        _,
        chat_user,
    )


def price_range_answer(message: Any, _: gettext, chat_user: UserModel):
    """
    Функция обработки полученного диапазона цен поиска отелей от пользователя.
    При корректности ввода инициации поиска и переходу к завершающей
    функции для выведения соответствующих
    критериям запроса отелей в указанном городе
    :param message: Any
    :param _: gettext
    :param chat_user: UserModel
    :return:
    """
    if message.text == 'rmh':
        cancel_registered_handlers(message)
        return
    get_prices_from_message = price_check(message.text)
    if not get_prices_from_message:
        incorrect_price(message, _, chat_user)
    else:
        chat_user.min_price, chat_user.max_price = get_prices_from_message
        search_hotels_result(message, _, chat_user)


def search_hotels_result(message: Any, _: gettext, chat_user: UserModel):
    """
    Функция по поиску отелей и предоставлению результатов поиска
    пользователю в виде отдельных сообщений для каждого отеля
    В случае, если город существует, но отелей в нем не обнаружено,
    будет выдано соответствующее сообщение
    :param message: Any
    :param _: gettext
    :param chat_user: UserModel
    :return:
    """
    search_text = _('Searching for hotels. 🔍 It may take a few seconds ...')
    bot.send_message(
        message.chat.id,
        search_text
    )

    get_offers_on_request_list = list(
        get_offers_on_request(
            sort_order=chat_user.sort_order,
            city=chat_user.city,
            number_of_hotels=chat_user.number_of_hotels,
            check_in=chat_user.check_in,
            check_out=chat_user.check_out,
            lang=chat_user.language,
            min_price=chat_user.min_price,
            max_price=chat_user.max_price,
        ),
    )
    chat_user.save()
    if not get_offers_on_request_list:
        bot.send_message(
            message.chat.id,
            _('No hotels found for your request.'),
        )
    else:
        for i_gen_item in get_offers_on_request_list:
            bot.send_message(
                message.chat.id,
                i_gen_item,
                disable_web_page_preview=False,
            )
        bot.next_step_backend.handlers[message.chat.id] = []


def cancel_registered_handlers(msg: Any):
    bot.send_message(chat_id=msg.chat.id, text='Canceled 🚫')
    bot.next_step_backend.handlers = {}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
