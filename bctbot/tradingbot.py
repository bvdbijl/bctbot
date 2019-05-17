from superjson import json
import time

from ccxt.base.errors import ExchangeError
from exchange import Exchange

import logging_setup
logger = logging_setup.logging.getLogger(__name__)

class TradingBot:

    def __init__(self, bot_settings=None):
        logger.info(f"Initializing Tradingbot with the following settings: {bot_settings}")
        self.config_file_path = "trading_bot_config.json"
        self.cycles = 0
        self.LOOP_SLEEP = 10
        self.active = True
        self.bot_settings = {} if bot_settings is None else bot_settings
        self.exchanges = self.load_exchanges()

    def load_exchanges(self):
        if not self.bot_settings:
            return {}
        exchanges = {}
        for exch_name, settings in self.bot_settings.items():
            exchanges[exch_name] = Exchange(exch_name, settings)
        return exchanges

    def loop(self):
        logger.debug(self)
        for exchange in self.exchanges.values():
            try:
                exchange.get_balance()
                for market in exchange.traded_markets.values():
                    market.update_balance()
                    if market.balance_changed():
                        for strategy in market.strategies:
                            strategy.balance_change_event()
                    market.update_ticker()
                    if market.price_changed():
                        for strategy in market.strategies:
                            strategy.price_change_event()
            except ExchangeError as e:
                logging_setup.logging.exception(str(e))
                continue
        self.save_session(self.config_file_path)
        self.cycles += 1
        time.sleep(self.LOOP_SLEEP)

    def save_session(self, file_path=None):
        # Copy the config that the bot was initialized with
        file_path = self.config_file_path if file_path is None else file_path
        logger.debug(f"Saving current session to {file_path}")
        session_settings = {}
        for exch_name, exchange in self.exchanges.items():
            session_settings[exch_name] = exchange.serialize()
        json.dump(session_settings, file_path, pretty=True, overwrite=True)

    def load_session(self, file_path=None):
        file_path = self.config_file_path if file_path is None else file_path
        logger.debug(f"Loading session from {file_path}")
        bot_settings = json.load(file_path)
        self.__init__(bot_settings)

    def __str__(self):
        exchanges = "\n  ".join([str(exchange) for exchange in self.exchanges.values()])
        return f"{self.__class__.__name__}: cycle {self.cycles}\n" \
               f"{exchanges}"
