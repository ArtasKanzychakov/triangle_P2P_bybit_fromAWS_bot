# src/bybit_client.py
from pybit.unified_trading import HTTP
from .config import BYBIT_API_KEY, BYBIT_API_SECRET, logger

class BybitClient:
    """
    Клиент для взаимодействия с API Bybit.
    """
    def __init__(self):
        try:
            self.session = HTTP(
                testnet=False,
                api_key=BYBIT_API_KEY,
                api_secret=BYBIT_API_SECRET,
            )
            logger.info("Успешное подключение к Bybit API.")
        except Exception as e:
            logger.error(f"Ошибка при подключении к Bybit API: {e}")
            self.session = None

    def get_spot_instruments(self):
        """
        Получает информацию о всех спотовых инструментах (пары и их правила).
        """
        if not self.session:
            return None
        try:
            result = self.session.get_instruments_info(category="spot")
            if result['retCode'] == 0:
                logger.info(f"Найдено {len(result['result']['list'])} спотовых инструментов на Bybit.")
                return result['result']['list']
            else:
                logger.error(f"Ошибка API Bybit при получении инструментов: {result['retMsg']}")
                return None
        except Exception as e:
            logger.error(f"Исключение при запросе инструментов Bybit: {e}")
            return None

    def get_tickers(self, symbols: list):
        """
        Получает актуальные цены (тикеры) для списка символов одним запросом.
        """
        if not self.session:
            return None
        try:
            # Bybit API ожидает строку символов, разделенных запятой
            symbols_str = ",".join(symbols)
            result = self.session.get_tickers(category="spot", symbol=symbols_str)
            
            if result['retCode'] == 0:
                # Преобразуем список в словарь для быстрого доступа по символу
                tickers_dict = {ticker['symbol']: ticker for ticker in result['result']['list']}
                return tickers_dict
            else:
                logger.error(f"Ошибка API Bybit при получении тикеров: {result['retMsg']}")
                return None
        except Exception as e:
            logger.error(f"Исключение при запросе тикеров Bybit: {e}")
            return None

    def get_usdt_balance(self):
        """
        Получает баланс USDT на едином торговом аккаунте.
        """
        if not self.session:
            return None
        try:
            result = self.session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
            if result['retCode'] == 0 and result['result']['list']:
                balance = result['result']['list'][0]['coin'][0]['walletBalance']
                return float(balance)
            else:
                logger.error(f"Ошибка API Bybit при получении баланса: {result.get('retMsg', 'Баланс не найден')}")
                return 0.0
        except Exception as e:
            logger.error(f"Исключение при запросе баланса Bybit: {e}")
            return 0.0

# Создаем один экземпляр клиента, который будет использоваться во всем приложении
bybit_client = BybitClient()
