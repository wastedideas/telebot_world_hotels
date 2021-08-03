import gettext
import json
import os
from typing import Iterator

import emoji
import requests
from dotenv import load_dotenv

load_dotenv()


def get_emoji_flag(country_name: str) -> str:
    """
    Функция ищет по json файлу с эмодзи флагов разных стран
    подходящую по запросу страну и возращает
    соответствующее эмодзи флага
    :param country_name: str
    :return: str
    """
    with open('flags.json', 'r', encoding='utf-8') as flags_file:
        emoji_flags = json.load(
            flags_file,
        )
        for emoji, country in emoji_flags.items():
            if any(
                country_name.lower() in i_country.lower()
                for i_country in country
            ):
                return emoji
        else:
            return ''


def get_country_by_city(city: str, country, lang: str) -> dict or None:
    """
    Функция, которая делает запрос к API по введенному пользователем городу
    и возращает название страны, в которой находится данный город,
    а также destination_id, по которому осуществляется поиск отеля. Также
    производится првоерка существования указанного пользователем города.
    :param city: str
    :param country: str
    :param lang: str
    :return: dict or None
    """
    url = "https://hotels4.p.rapidapi.com/locations/search"

    querystring = {
        "query": city,
        "locale": lang,
    }

    headers = {
        'x-rapidapi-key': os.getenv('HOTELS_API_KEY'),
        'x-rapidapi-host': "hotels4.p.rapidapi.com",
        }

    response = requests.request(
        "GET",
        url,
        headers=headers,
        params=querystring,
    )

    json_request = json.loads(response.text)

    city_dict = {}

    if not json_request.get('suggestions')[0].get('entities'):
        return None

    for suggestion in json_request['suggestions']:
        if suggestion['group'] == 'CITY_GROUP':
            for entity in suggestion.get('entities'):
                if (
                    city.lower() in entity.get('name').lower() and
                    country.lower() in entity.get('caption').split(', ')[-1].lower() and
                    len(entity.get('destinationId')) <= 10
                ):
                    city_dict['destination_id'] = entity.get('destinationId')
                    city_dict['city_name'] = entity.get('name')
                    city_dict['country'] = entity.get('caption').split(', ')[-1]
                    city_dict['flag_for_tg'] = get_emoji_flag(city_dict['country'])
                    return city_dict
            else:
                return None


def get_offers_on_request(

    sort_order: str,
    city: dict,
    number_of_hotels: str,
    check_in: str,
    check_out: str,
    lang: str,
    min_price: str,
    max_price: str,
) -> Iterator[str]:
    """
    Функция-генератор, которая по введенным на всех этапах опроса
    пользователя данным делает запрос к API и выводит отели в соответствии
    с запросом
    :param sort_order: str
    :param city: dict
    :param number_of_hotels: str
    :param check_in: str
    :param check_out: str
    :param lang: str
    :param min_price: str
    :param max_price: str
    :return: Iterator[str]
    """
    url = "https://hotels4.p.rapidapi.com/properties/list"

    city_info_dict = city

    list_item_emoji = emoji.emojize(":small_orange_diamond:")

    querystring = {
        "adults1": "1",
        "pageNumber": "1",
        "destinationId": city_info_dict['destination_id'],
        "pageSize": number_of_hotels,
        "checkOut": check_out,
        "checkIn": check_in,
        "sortOrder": sort_order,
        "locale": lang,
        "currency": ('RUB' if lang == 'ru_RU' else 'USD'),
        "priceMin": min_price,
        "priceMax": max_price,
    }

    headers = {
        'x-rapidapi-key': os.getenv('HOTELS_API_KEY'),
        'x-rapidapi-host': "hotels4.p.rapidapi.com",
        }

    response = requests.request("GET", url, headers=headers, params=querystring)

    json_request = json.loads(response.text)

    search_results = json_request['data']['body']['searchResults']['results']

    if not search_results:
        return

    _ = gettext.translation(
        'chat_user_lang',
        localedir='locales',
        languages=[
            'ru',
        ],
    ).gettext

    if lang == 'en_EN':
        _ = gettext.translation(
            'chat_user_lang',
            localedir='locales',
            languages=[
                'en',
            ],
        ).gettext

    for i_search in search_results:
        hotel_address = _('Not specified.')
        hotel_rating = _('No information.')
        hotel_price = _('Not specified.')

        hotel_name = i_search.get('name')

        if i_search.get('address') and i_search.get('address').get('streetAddress'):
            hotel_address = i_search.get('address').get('streetAddress')

        if i_search.get('guestReviews') and i_search.get('guestReviews').get('rating'):
            hotel_rating = i_search.get('guestReviews').get('rating') + '/10,0'

        hotel_landmark = i_search.get('landmarks')[0].get('distance')

        if i_search.get('ratePlan'):
            hotel_price = i_search.get('ratePlan').get('price').get('current').split()[0]

        string_about_hotel = _(
            '{city_name} {country} {flag_for_tg}\n'
            '{list_item_emoji} Hotel name: {hotel_name}\n'
            '{list_item_emoji} Hotel address: {hotel_address}\n'
            '{list_item_emoji} Hotel rating: {hotel_rating}\n'
            '{list_item_emoji} Distance to the city center: {hotel_landmark}.\n'
            '{list_item_emoji} Cost of living: {hotel_price}'
        ).format(
            city_name=city_info_dict["city_name"],
            country=city_info_dict["country"],
            flag_for_tg=city_info_dict["flag_for_tg"],
            list_item_emoji=list_item_emoji,
            hotel_name=hotel_name,
            hotel_address=hotel_address,
            hotel_rating=hotel_rating,
            hotel_landmark=hotel_landmark,
            hotel_price=hotel_price,
        )

        yield string_about_hotel
