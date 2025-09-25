import logging
import os
import sys
import time

import requests
from dotenv import load_dotenv
from telebot import TeleBot


load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
stdout_handler = logging.StreamHandler(stream=sys.stdout)

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
    variables = [('PRACTICUM_TOKEN', PRACTICUM_TOKEN),
                 ('TELEGRAM_TOKEN', TELEGRAM_TOKEN),
                 ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID)
                 ]
    for name, variable in variables:
        if not variable:
            logging.critical(
                'Отсутствует обязательная переменная окружения: %s', name
            )
            raise ValueError('Missing required variable')


def send_message(bot, message):
    """Отправляет сообщение пользователю."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logging.debug(f'Бот отправил сообщение: %s"{message}"')
    except Exception as error:
        logging.error(f'Сбой при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Возвращает ответ АPI в формате dict."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params={
                                'from_date': timestamp})
    except Exception as error:
        logging.error(f'Ошибка при запросе к API: {error}')
    if response.status_code == 200:
        return response.json()
    else:
        logging.ERROR(
            f'Сбой. Эндпоинт недоступен, код ответа API:'
            f'{response.status_code}'
        )


def check_response(response):
    """Проверяет ответ API на соответствие док-ции."""
    if not isinstance(response, dict):
        raise TypeError(
            f'Полученный тип данных не соответвтсвует ожидаемому'
            f' dict: {type(response)}')
    if not (
        'homeworks' in response
    ) or not (
        'current_date' in response
    ):
        raise KeyError
    try:
        if response['homeworks']:
            for homework in response['homeworks']:
                if homework['status'] not in HOMEWORK_VERDICTS:
                    hw_status = homework['status']
                    logging.error(
                        f'Неожиданный статус домашней работы: {hw_status}')
        else:
            logging.debug('Отсутствие в ответе новых статусов')
    except Exception as error:
        logging.error(f'отсутствие ожидаемых ключей в ответе API: {error}')
        raise error


def parse_status(homework):
    """Возвращает message - строку для отправки пользователю."""
    try:
        homework_name = homework['homework_name']
        hw_status = homework['status']
        verdict = HOMEWORK_VERDICTS[hw_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except Exception as error:
        logging.error(f'При извлечении статуса произошла ошибка: {error}')
        raise error('При извлечении статуса произошла ошибка')


def main():
    """Основная логика работы бота."""
    check_tokens()

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
