# src/arbitrage_finder.py
import time
from itertools import combinations
from .config import logger, ADMIN_CHAT_ID

class ArbitrageFinder:
    def __init__(self, bybit_client):
        self.bybit_client = bybit_client
        self.instruments_info = {}  # {'BTCUSDT': {'minOrderQty': '0.0001', ...}}
        self.all_pairs = []         # ['BTCUSDT', 'ETHUSDT', ...]
        self.triangular_chains = [] # [['USDT', 'BTC', 'ETH'], ...]
        self.tickers = {}           # {'BTCUSDT': {'ask1Price': '...', 'bid1Price': '...'}}
        self.start_amount = 100.0   # Сумма для расчета по умолчанию
        self.min_profit_percent = 0.5 # Минимальный % прибыли для уведомления

    def load_market_data(self):
        """
        Загружает с биржи все торговые пары и их правила, затем формирует арбитражные цепочки.
        """
        logger.info("Загрузка данных о рынках...")
        instruments = self.bybit_client.get_spot_instruments()
        if not instruments:
            logger.error("Не удалось загрузить инструменты с Bybit. Проверьте ключи API и соединение.")
            return False

        unique_currencies = set()
        for instrument in instruments:
            if instrument['status'] == 'Trading':
                symbol = instrument['symbol']
                base_coin = instrument['baseCoin']
                quote_coin = instrument['quoteCoin']
                
                self.all_pairs.append(symbol)
                unique_currencies.add(base_coin)
                unique_currencies.add(quote_coin)
                
                # Сохраняем правила торговли, особенно minOrderQty
                self.instruments_info[symbol] = {
                    'minOrderQty': instrument['lotSizeFilter']['minOrderQty'],
                    'baseCoin': base_coin,
                    'quoteCoin': quote_coin
                }
        
        logger.info(f"Загружено {len(self.all_pairs)} активных пар.")
        logger.info("Формирование треугольных арбитражных цепочек...")
        self._form_triangular_chains(list(unique_currencies))
        logger.info(f"Найдено {len(self.triangular_chains)} возможных цепочек.")
        return True

    def _form_triangular_chains(self, currencies):
        """
        Формирует все возможные треугольные цепочки из списка валют.
        Пример: [USDT, BTC, ETH]
        """
        # Генерируем все уникальные комбинации из 3 валют
        for combo in combinations(currencies, 3):
            # Проверяем, существуют ли торговые пары для всех трех "ног" цепочки
            c1, c2, c3 = combo[0], combo[1], combo[2]
            
            # Вариант 1: c1 -> c2 -> c3 -> c1
            if f"{c2}{c1}" in self.all_pairs and f"{c3}{c2}" in self.all_pairs and f"{c3}{c1}" in self.all_pairs:
                self.triangular_chains.append([c1, c2, c3, 'reverse']) # c3/c1 - обратная пара
            
            # Вариант 2: c1 -> c3 -> c2 -> c1
            if f"{c3}{c1}" in self.all_pairs and f"{c2}{c3}" in self.all_pairs and f"{c2}{c1}" in self.all_pairs:
                self.triangular_chains.append([c1, c3, c2, 'reverse']) # c2/c1 - обратная пара

            # ... и так далее для всех 6 возможных комбинаций (для простоты реализуем 2 самых частых)
            # Полная реализация проверит все 6 путей для каждой тройки
            # Например, c1/c2, c2/c3, c1/c3
            if f"{c2}{c1}" not in self.all_pairs and f"{c1}{c2}" in self.all_pairs: c2, c1 = c1, c2 # Нормализуем первую пару
            
            pair1 = f"{c2}{c1}"
            pair2_1, pair2_2 = f"{c3}{c2}", f"{c2}{c3}"
            pair3_1, pair3_2 = f"{c3}{c1}", f"{c1}{c3}"

            if pair1 in self.all_pairs:
                if pair2_1 in self.all_pairs and pair3_1 in self.all_pairs:
                    self.triangular_chains.append([c1, c2, c3])
                if pair2_2 in self.all_pairs and pair3_2 in self.all_pairs:
                    self.triangular_chains.append([c1, c3, c2])


    async def check_arbitrage_opportunities(self, context):
        """
        Основной цикл мониторинга. Вызывается по расписанию.
        """
        try:
            # 1. Получаем свежие цены для всех пар одним запросом
            self.tickers = self.bybit_client.get_tickers(self.all_pairs)
            if not self.tickers:
                logger.warning("Не удалось обновить цены (тикеры). Пропуск цикла.")
                return

            # 2. Итерируемся по всем найденным цепочкам
            for chain in self.triangular_chains:
                await self._check_single_chain(context, chain)
                
        except Exception as e:
            logger.error(f"Критическая ошибка в цикле мониторинга: {e}")

    async def _check_single_chain(self, context, chain):
        """
        Проверяет одну арбитражную цепочку.
        """
        # Пример цепочки: [USDT, BTC, ETH]
        # 1. USDT -> BTC (покупка BTC за USDT, пара BTCUSDT)
        # 2. BTC -> ETH (покупка ETH за BTC, пара ETHBTC)
        # 3. ETH -> USDT (продажа ETH за USDT, пара ETHUSDT)
        
        c1, c2, c3 = chain[0], chain[1], chain[2]

        try:
            # Определяем пары и направление сделки
            pair1, leg1_is_reversed = self._get_pair_info(c1, c2)
            pair2, leg2_is_reversed = self._get_pair_info(c2, c3)
            pair3, leg3_is_reversed = self._get_pair_info(c3, c1)

            if not all([pair1, pair2, pair3]): return # Если какая-то пара не найдена

            # Получаем цены Ask/Bid для каждой пары
            price1 = float(self.tickers[pair1]['ask1Price']) if not leg1_is_reversed else 1 / float(self.tickers[pair1]['bid1Price'])
            price2 = float(self.tickers[pair2]['ask1Price']) if not leg2_is_reversed else 1 / float(self.tickers[pair2]['bid1Price'])
            price3 = float(self.tickers[pair3]['bid1Price']) if not leg3_is_reversed else 1 / float(self.tickers[pair3]['ask1Price'])
            
            # --- Расчет профита ---
            amount_c2 = self.start_amount / price1
            amount_c3 = amount_c2 / price2
            final_amount = amount_c3 * price3

            profit = final_amount - self.start_amount
            profit_percent = (profit / self.start_amount) * 100

            # --- Проверка на минимальный профит ---
            if profit_percent > self.min_profit_percent:
                
                # --- Динамическая проверка торговых лимитов ---
                # leg1: Покупаем amount_c2 (базовая валюта)
                qty1 = amount_c2 if not leg1_is_reversed else self.start_amount
                min_qty1 = float(self.instruments_info[pair1]['minOrderQty'])
                
                # leg2: Покупаем amount_c3 (базовая валюта)
                qty2 = amount_c3 if not leg2_is_reversed else amount_c2
                min_qty2 = float(self.instruments_info[pair2]['minOrderQty'])

                # leg3: Продаем amount_c3 (базовая валюта)
                qty3 = amount_c3 if not leg3_is_reversed else final_amount
                min_qty3 = float(self.instruments_info[pair3]['minOrderQty'])

                if qty1 < min_qty1 or qty2 < min_qty2 or qty3 < min_qty3:
                    logger.info(f"Найден спред {profit_percent:.4f}% в {chain}, но объем ниже минимума.")
                    return
                
                # Если все проверки пройдены, отправляем уведомление
                message = (
                    f"🚀 **Найдена арбитражная возможность!**\n\n"
                    f"**Цепочка:** `{c1} → {c2} → {c3} → {c1}`\n"
                    f"**Профит:** `{profit:.4f} {c1}` ({profit_percent:.4f}%)\n"
                    f"**Стартовая сумма:** `{self.start_amount} {c1}`\n\n"
                    f"**Шаг 1 ({pair1}):** Купить `{c2}` за `{c1}`\n"
                    f"**Шаг 2 ({pair2}):** Купить `{c3}` за `{c2}`\n"
                    f"**Шаг 3 ({pair3}):** Продать `{c3}` за `{c1}`\n\n"
                    f"**Объемы (Qty > MinQty):**\n"
                    f"1. `{qty1:.6f}` > `{min_qty1}`\n"
                    f"2. `{qty2:.6f}` > `{min_qty2}`\n"
                    f"3. `{qty3:.6f}` > `{min_qty3}`"
                )
                await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message, parse_mode='Markdown')

        except (KeyError, ZeroDivisionError, TypeError) as e:
            # Эти ошибки ожидаемы, если тикер для пары временно недоступен
            pass
        except Exception as e:
            logger.error(f"Ошибка при проверке цепочки {chain}: {e}")
            
    def _get_pair_info(self, c_from, c_to):
        """ Вспомогательная функция для определения имени пары и ее направления """
        if f"{c_to}{c_from}" in self.all_pairs:
            return f"{c_to}{c_from}", False # Прямая пара (e.g., BTC/USDT)
        elif f"{c_from}{c_to}" in self.all_pairs:
            return f"{c_from}{c_to}", True # Обратная пара (e.g., USDT/BTC)
        else:
            return None, None
