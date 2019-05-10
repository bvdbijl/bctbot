from collections import deque
from ccxt.base.errors import NetworkError
from utils import retry, RetrySettings
from strategies import Strategy

import logging_setup
logger = logging_setup.logging.getLogger(__name__)

class Market:

    def __init__(self, symbol, exchange, market_settings):
        self.symbol = symbol
        self.exchange = exchange
        self.strategies_settings = market_settings.get("strategies", {})
        self.market_data = self.exchange.markets[symbol]
        self.id = self.market_data["id"]
        self.base = self.market_data["base"]
        self.quote = self.market_data["quote"]
        self.prices = market_settings.get("prices", deque([], maxlen=500))
        self.balances = market_settings.get("balances", deque([], maxlen=100))
        self.active = market_settings.get("active", True)
        self.strategies = self.set_strategies()


    def update_balance(self):
        return self.exchange.balance.get(self.base, 0)

    def set_strategies(self):
        if not self.strategies_settings:
            return {}
        strats = {}
        for strat_name, strat_settings in self.strategies_settings.items():
            strats[strat_name] = Strategy.set_strategy(strat_name, self, strat_settings)
        return strats

    @property
    def last_price(self):
        if self.prices:
            return self.prices[-1]

    @property
    def last_balance(self):
        if self.balances:
            return self.balances[-1]

    def deactivate(self):
        logger.info(f"Deactivating {self.symbol}")
        self.active = False

    @retry(NetworkError, tries=RetrySettings.tries, delay=RetrySettings.delay, backoff=RetrySettings.backoff, on_fail=deactivate)
    def update_ticker(self):
        price = self.exchange.fetch_ticker(self.symbol)["last"]
        self.prices.append(price)
        logger.debug(f"Updated ticker: {self.symbol}, {self.exchange.id}, last price: {self.last_price:.8f}")

    def price_changed(self):
        if len(self.prices) < 2:
            return True
        return self.prices[-2] != self.last_price

    def balance_changed(self):
        if len(self.balances) < 2:
            return True
        return self.balances[-2] != self.last_balance

    def cancel_all_orders(self):
        orders = self.exchange.fetch_open_orders(self.symbol)
        for order in orders:
            self.exchange.cancel_order(order["id"], self.symbol, {
                "type": order["side"]})

    def fetch_open_orders(self):
        return self.exchange.fetch_open_orders(self.symbol)

    def serialize(self):
        strategies = {}
        for strategy_name, strategy in self.strategies.items():
            strategies[strategy_name] = strategy.serialize()
        market = {
            "strategies": strategies,
            "prices": self.prices,
            "balances": self.balances,
            "active": self.active
        }
        return market

    def __str__(self):
        strategies = "\n  ".join([str(strategy) for strategy in self.strategies])
        return f"{self.__class__.__name__}: {self.symbol}, {self.last_price:.8f}, active: {self.active}\n" \
               f"{strategies}"