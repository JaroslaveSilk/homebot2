import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import (
    ApiConnectionError,
    EmptyAPIResponseError,
    MissingRequiredVarsError,
    IncorrectDataReceivedError
)


load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
stdout_handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(stdout_handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет наличие всех обязательных переменных."""
    variables = {'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
                 'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
                 'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
                 }
    missing_vars = []
    for name, variable in variables.items():
        if not variable:
            missing_vars.append(name)
    return missing_vars


def send_message(bot, message):
    """Отправляет сообщение пользователю."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logger.debug('Бот отправил сообщение: %s', message)
    except Exception as error:
        logger.error('Сбой при отправке сообщения: %s', error)


def get_api_answer(timestamp):
    """Возвращает ответ АPI в формате dict."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params={
                                'from_date': timestamp})
    except Exception as error:
        logger.error('Ошибка при запросе к API: %s',
                     error, ENDPOINT, HEADERS)
    if response.status_code == HTTPStatus.OK:
        try:
            return response.json()
        except Exception as error:
            logger.error('Сбой приведения ответа к формату dict: %s', error)
    logger.error(
        'Сбой. Эндпоинт недоступен, код ответа API: %s',
        response.status_code
    )
    raise ApiConnectionError(
        'Сбой. Эндпоинт недоступен, код ответа API: ',
        response.status_code
    )


def check_response(response):
    """Проверяет ответ API на соответствие док-ции."""
    if not isinstance(response, dict):
        raise TypeError(
            'Полученный тип данных не соответвтсвует ожидаемому dict: ',
            type(response))
    if not (
        'homeworks' in response
    ) or not (
        'current_date' in response
    ):
        logger.error('отсутствие ожидаемых ключей в ответе API: %s',
                     EmptyAPIResponseError
                     )
        raise EmptyAPIResponseError
    if not isinstance(response['homeworks'], list):
        raise TypeError
    homeworks = response['homeworks']
    if not homeworks:
        logger.debug('Отсутствие в ответе новых статусов')


def parse_status(homework):
    """Возвращает message - строку для отправки пользователю."""
    if 'homework_name' not in homework or 'status' not in homework:
        logger.error('Отсутствуют данные статуса/названия в ответе',
                     EmptyAPIResponseError
                     )
        raise EmptyAPIResponseError(
            'Отсутствуют данные статуса/названия в ответе')
    hw_status = homework['status']
    if hw_status not in HOMEWORK_VERDICTS:
        logger.error('Получен недействительный статус: ',
                     IncorrectDataReceivedError
                     )
        raise IncorrectDataReceivedError
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[hw_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if checker := check_tokens():
        logger.critical(
            'Отсутствуют обязательные переменные окружения: %s', checker
        )
        raise MissingRequiredVarsError(
            'Отсутствуют обязательные переменные окружения',
            checker
        )

    # Создаем объект класса бота
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = None

    while True:
        try:

            response = get_api_answer(timestamp)
            if response:
                check_response(response)
                for homework in response['homeworks']:
                    message = parse_status(homework)
                    send_message(bot, message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != last_message:
                send_message(bot, message)
                last_message = message
        else:
            timestamp = response['current_date']
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
