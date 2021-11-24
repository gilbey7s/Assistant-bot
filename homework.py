import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s',
    filename='HW.log',
    filemode='w',
)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения в чат Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение отправлено в чат')
    except telegram.TelegramError as error:
        logger.error(f'Невозможно отправить сообщение в чат: {error}')


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту YandexPracticum."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    logger.info(f'Попытка запроса к эндпоинту {ENDPOINT}')
    try:
        response = requests.get(ENDPOINT, params=params, headers=HEADERS)
    except requests.exceptions.HTTPError as error:
        text = f'Ошибка, статус запроса - {error}'
        logger.error(text)
    if response.status_code != 200:
        text = (
            f'От эндпоинта: {ENDPOINT}, пришел ответ отличный от нормы.'
            f' Код ответа: {response.status_code}.'
        )
        logger.error(text)
        raise ConnectionError(text)
    logger.info(f'Успешный ответ от эндпоинта {ENDPOINT}')
    return response.json()


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response['homeworks'], list):
        text = 'В ответе значения не приведены к list'
        raise TypeError(text)
    return response['homeworks']


def parse_status(homework):
    """Парсинг статуса работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return (
        f'Изменился статус проверки работы "{homework_name}".'
        f'{verdict}'
    )


def check_tokens():
    """Проверка переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID is not None:
        return True
    logger.critical('Переменные окружения не доступны,'
                    'проверьте их наличие в файле .env'
                    )
    return False


def main():
    """Основная логика работы бота."""
    tokens_access = check_tokens()
    if not tokens_access:
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    logger.info('Бот инициирован.')
    current_timestamp = int(time.time())
    re_msg = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                logger.debug('У работы не изменился статус.')
            else:
                msg = parse_status(homeworks[0])
                if msg != re_msg:
                    send_message(bot, msg)
            current_timestamp = response['current_date']
        except Exception as error:
            msg = f'Сбой в работе программы: {error}'
            logging.error(f'Ошибка в работе бота: {msg}')
            if msg != re_msg:
                send_message(bot, msg)
                re_msg = msg
        re_msg = None
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
