from ccxt.base.errors import NetworkError, DDoSProtection, ExchangeNotAvailable, InvalidNonce, InvalidOrder, RequestTimeout, OrderNotFound

from utils import retry, RetrySettings

import logging_setup
logger = logging_setup.logging.getLogger(__name__)

class Order():

    def __init__(self, exchange, market, side, type, price, amount=0, cost=0, initial_cost=None, internal_id=None, id=None, status="potential"):
        self.exchange = exchange            # Exchange object
        self.market = market                # Market object
        self.side = side                    # "buy" or "sell"
        self.type = type                    # "limit", "market" etc.
        self.price = price
        self.amount = amount
        self.cost = cost
        self.initial_cost = self.cost if initial_cost is None else initial_cost
        self.internal_id = internal_id      # id used by the trading bot
        self.id = id                        # id given from exchange
        self.status = status                # status: ('potential', 'open', 'filled', 'canceled')

        # self.last_response = {}
        logger.debug(f"Initializing an order: {self}")

    @property
    def amount(self):
        if self._amount == 0:
            if self._cost == 0:
                return 0
            return self.cost / self.price
        return self._amount

    @amount.setter
    def amount(self, value):
        self._amount = value
        if value != 0:
            self._cost = 0

    @property
    def cost(self):
        if self._cost == 0:
            if self._amount == 0:
                return 0
            return self.amount * self.price
        return self._cost

    @cost.setter
    def cost(self, value):
        self._cost = value
        if value != 0:
            self._amount = 0

    def deactivate_market(self):
        self.market.deactivate()

    @retry((DDoSProtection, ExchangeNotAvailable, InvalidNonce), on_fail=RetrySettings.raise_retry_error)
    def place_order(self):
        # if not self.order_valid: logger.error("Order not valid for placing on the exchange")
        try:
            response = self.exchange.create_order(self.market.symbol, self.type, self.side, self.amount, self.price)
            # self.last_response = response
            # Update this Orders' instance attributes with the updated attributes from the response
            self.amount = response["amount"]
            self.id = response["id"]
            self.status = response["status"]            # 'open' if successful
            logger.info(f"Placed order: {self}")
        except InvalidOrder as e:
            if self.amount == 0:
                logger.error(f"Amount can't be 0. {self}")
                logging_setup.logging.exception(str(e))
            raise
        except RequestTimeout:
            # if not self.order_in_open_orders(): self.place_order()
            # else:
            raise RetrySettings.PersistentErrorAfterRetries("Just handle the RequestTimeout for create_order manually...")

    @retry(NetworkError, on_fail=RetrySettings.raise_retry_error)
    def cancel_order(self):
        try:
            response = self.exchange.cancel_order(self.id, self.market.symbol, {"type": self.side})
        except OrderNotFound as e:
            # Check first if the order is not filled by checking change in balance
            logging_setup.logging.exception(str(e))
            self.status = "canceled"
        else:
            # kucoin: response["success"]
            if "success" in response.keys():
                success = response["success"]
            # cryptopia: response["info"]["Success"]
            elif "info" in response.keys() and "Success" in response["info"].keys():
                success = response["info"]["Success"]

            if success:
                self.status = "canceled"
                logger.info(f"Order canceled: {self}")
            else:
                logger.info(f"Something went wrong canceling order: {self}")

    def order_filled(self):
        if self.status in ["potential", "filled", "canceled"]:
            return False
        elif self.status == "open" and self.order_in_open_orders():
            return False
        self.status = "filled"
        return True

    @retry(NetworkError, on_fail=deactivate_market)
    def order_in_open_orders(self):
        response = self.exchange.fetch_open_orders(self.market.symbol)
        logger.info(response)
        for order in response:
            if order["id"] == self.id:
                return True
        return False

    # Used before placing an order?
    def order_valid(self):
        if self.amount <= 0:
            return False
        if self.price <= 0:
            return False
        self.exchange.get_balance()
        if self.exchange.balance[self.market.quote]["free"] < self.cost:
            return False
        return True

    def serialize(self):
        order = {}
        for k, v in self.__dict__.items():
            if k == "_amount":
                continue
            elif k == "exchange":
                v = v.id
            elif k == "market":
                v = v.symbol
            elif k == "_cost":
                k = "cost"
                v = self.cost
            order[k] = v
        return order

    def __str__(self):
        base = self.market.base if self.market else ""
        quote = self.market.quote if self.market else ""
        exchange_id = self.exchange.id if self.exchange else ""
        s = f"({self.status}) {self.type} {self.side} order for {self.amount:.8f} {base} at price " \
            f"{self.price:.8f} {quote} with internal_id {self.internal_id}, id {self.id} on " \
            f"{exchange_id} exchange"
        return s

if __name__ == "__main__":
    TESTING = True
    if TESTING:
        from collections import namedtuple
        exch = namedtuple("Exchange", ("id"))
        mkt = namedtuple("Market", ("symbol", "base", "quote"))
        e1 = exch("kucoin")
        m1 = mkt("ADB/ETH", "ADB", "ETH")
        o = Order(e1, m1, "buy", "limit", 0.02, cost=2)