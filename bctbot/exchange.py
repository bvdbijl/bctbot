import ccxt
from ccxt.base.errors import NetworkError
from utils import retry, RetrySettings
from market import Market

import logging_setup
logger = logging_setup.logging.getLogger(__name__)

class Exchange:

    def __new__(cls, name, settings):
        base_class = getattr(ccxt, name)
        x = type(base_class.__name__, (Exchange, base_class), {})
        return super(Exchange, cls).__new__(x)

    def __init__(self, name, settings):
        ccxt_config = settings.get("ccxt_config", {})
        super().__init__(ccxt_config)
        self.markets = self.load_markets()
        self.traded_markets_settings = settings.get("traded_markets", {})
        self.traded_markets = self.set_traded_markets()

    def set_traded_markets(self):
        if not self.traded_markets_settings:
            return {}
        markets = {}
        for mkt_name, market_settings in self.traded_markets_settings.items():
            markets[mkt_name] = Market(mkt_name, self, market_settings)
        return markets

    @retry(NetworkError, on_fail=RetrySettings.raise_retry_error)
    def load_markets(self):
        return super().load_markets()

    @retry(NetworkError, on_fail=RetrySettings.raise_retry_error)
    def get_balance(self):
        self.balance = self.fetch_balance()
        balance = {coin: value for coin, value in self.balance["free"].items() if value > 0.001}
        logger.debug(f"Updated balance for {self.id}: {balance}")

    def serialize(self):
        traded_markets = {}
        for mkt_name, market in self.traded_markets.items():
            traded_markets[mkt_name] = market.serialize()
        exchange = {
            "ccxt_config": {
                "apiKey": self.apiKey,
                "secret": self.secret,
                "verbose": self.verbose,
                "enableRateLimit": self.enableRateLimit
            },
            "traded_markets": traded_markets
        }
        return exchange

    def __str__(self):
        markets = "\n  ".join([str(market) for market in self.traded_markets.values()])
        return f"{self.__class__.__name__}: {self.name}\n  " \
               f"{markets}"