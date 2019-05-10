from transitions import Machine
from order import Order

import logging_setup
logger = logging_setup.logging.getLogger(__name__)

class Strategy:

    def __init__(self, market, strategy_settings):
        self.market = market
        self.strategy_settings = strategy_settings

    @staticmethod
    def set_strategy(strategy_name, market, strategy_settings):
        if strategy_name.startswith("range_account_building"):
            return RangeAccountBuilding(market, strategy_settings)

    def serialize(self):
        orders = {}
        for internal_id, order in self.orders.items():
            orders[internal_id] = order.serialize()
        strategy = {
            "orders": orders
        }
        return strategy

    def __str__(self):
        orders = "\n  ".join(str(order) for order in self.orders.values())
        return f"Strategy {self.name}: current state: {self.state}, orders:\n  " \
               f"{orders}"


class RangeAccountBuilding(Strategy):

    states = ["idle", "buying", "bought", "bought_all",
              "selling", "sold", "sold_all"]
    transitions = [
        {"trigger": "price_change_event", "source": "idle", "dest": "buying",
         "conditions": ["price_below_buy_trigger"], "before": ["place_buy_orders"]},

        {"trigger": "price_change_event", "source": "buying", "dest": "idle",
         "conditions": ["price_above_buy_trigger"], "unless": ["any_sell_order_open"], "before": ["cancel_buy_orders"]},

        {"trigger": "price_change_event", "source": "buying", "dest": "selling",
         "conditions": ["price_above_buy_trigger", "any_sell_order_open"], "before": ["cancel_buy_orders"]},

        {"trigger": "balance_change_event", "source": "buying", "dest": "bought",
         "conditions": ["any_buy_order_filled"]},

        {"trigger": "price_change_event", "source": "selling", "dest": "buying",
         "conditions": ["price_below_buy_trigger"], "before": ["place_buy_orders"]},

        {"trigger": "balance_change_event", "source": "selling", "dest": "sold",
         "conditions": ["any_sell_order_filled"]}

    ]

    def __init__(self, market, strategy_settings):
        """

        :param market: Market object
        :param strategy_settings: dict:
            total_buy_cost:
            buy_price_1:
            buy_amount_percentage:
            sell_price_1:
            sell_amount_percentage:
            * Any number of buy and/or sell orders *
        """
        super().__init__(market, strategy_settings)
        for key, value in self.strategy_settings.items():
            setattr(self, key, value)

        self.bought_counter = strategy_settings.get("bought_counter", 0)
        self.amount_to_sell = strategy_settings.get("amount_to_sell", 0)
        self.orders = self.prepare_orders(strategy_settings.get("orders", {}))
        self.buy_trigger = self.set_buy_trigger()
        self.machine = Machine(model=self, states=self.states, transitions=self.transitions,
                               initial=strategy_settings.get("state", "idle"))

    def serialize(self):
        strategy = super().serialize()
        settings = {
            "total_buy_cost": self.total_buy_cost,
            "bought_counter": self.bought_counter,
            "amount_to_sell": self.amount_to_sell,
            "state": self.state
        }
        for k, v in self.__dict__.items():
            if k.startswith(("buy_price_", "buy_amount_percentage_", "sell_price_", "sell_amount_percentage_")):
                settings[k] = v
        strategy.update(settings)
        return strategy

    def set_buy_trigger(self, percentage=0.25):
        """ Calculates the price trigger for when to place the buy orders.

        :param percentage: Percentage from the first sell order price
        :return: trigger price (float)
        """

        buy_1 = self.orders["buy_order_1"].price
        sell_1 = self.orders["sell_order_1"].price
        diff = sell_1 - buy_1
        dist = diff * percentage
        return sell_1 - dist

    def prepare_orders(self, orders):
        if orders:
            orders_objects = {}
            for internal_id, order in orders.items():
                orders_objects[internal_id] = Order(self.market.exchange, self.market, order["side"], order["type"],
                                                    order["price"], cost=order["cost"], initial_cost=order["initial_cost"],
                                                    internal_id=order["internal_id"], id=order["id"], status=order["status"])
            return orders_objects

        for key, value in self.strategy_settings.items():
            if "price" in key:
                side = key.split("_")[0]
                number = key.split("_")[-1]
                cost = self.strategy_settings["total_buy_cost"] * self.strategy_settings[side + "_amount_percentage_" + number]
                price = self.strategy_settings[side + "_price_" + number]
                internal_id = side + "_order_" + number
                orders[internal_id] = Order(self.market.exchange, self.market, side, "limit", price, cost=cost, internal_id=internal_id)
        return orders

    # Conditionals
    def price_below_buy_trigger(self):
        return self.market.last_price < self.buy_trigger

    def price_above_trigger(self):
        return self.market.last_price > self.buy_trigger

    def any_buy_order_filled(self):
        for order in self.orders.values():
            if order.side == "buy" and order.order_filled():
                self.update_bought_counter(order)
                self.update_amount_to_sell(order)
                return True
        return False

    def any_sell_order_filled(self):
        for order in self.orders.values():
            if order.side == "sell" and order.order_filled():
                self.update_bought_counter(order)
                return True
        return False

    def all_buy_orders_filled(self):
        for order in self.orders.values():
            if order.side == "buy" and not order.status == "filled":
                return False
        return True

    def all_sell_orders_filled(self):
        for order in self.orders.values():
            if order.side == "sell" and not order.status == "filled":
                return False
        return True

    # Unless
    def any_sell_order_open(self):
        for order in self.orders.values():
            if order.side == "sell" and order.status == "open":
                return True
        return False

    # Before transitions
    def place_buy_orders(self):
        for order in self.orders.values():
            if order.side == "buy":
                order.place_order()

    def cancel_buy_orders(self):
        for order in self.orders.values():
            if order.side == "buy":
                order.cancel_order()

    def place_sell_orders(self):
        for order in self.orders.values():
            if order.side == "sell":
                order.place_order()

    def cancel_sell_orders(self):
        for order in self.orders.values():
            if order.side == "sell":
                order.cancel_order()

    # on_enter methods
    def on_enter_bought(self):
        # happening in any_buy_order_filled() check already
        # self.update_bought_counter()
        self.cancel_sell_orders()
        self.recalculate_sell_orders()
        self.place_sell_orders()
        if self.all_buy_orders_filled():
            self.to_bought_all()
        else:
            self.to_buying()

    def on_enter_sold(self):
        self.recalculate_buy_orders()
        if self.all_sell_orders_filled():
            self.to_idle()
        else:
            self.to_selling()

    # on_exit methods

    # After transitions

    # Other methods
    def update_bought_counter(self, order):
        if order.side == "buy":
            self.bought_counter += order.cost
        elif order.side == "sell":
            self.bought_counter -= order.cost

    def update_amount_to_sell(self, order):
        if order.side == "buy":
            self.amount_to_sell += order.amount

    def recalculate_sell_orders(self):
        for internal_id, order in self.orders.items():
            if order.side == "sell":
                number = internal_id.split("_")[-1]
                sell_amount_percentage = getattr(self, "sell_amount_percentage_" + number)
                order.amount = self.amount_to_sell * sell_amount_percentage
                order.status = "potential"
                self.amount_to_sell -= order.amount

    def recalculate_buy_orders(self):
        to_divide = self.total_buy_cost - self.bought_counter
        buy_orders = {name: order for name, order in self.orders.items() if order.side == "buy"}
        for elem in sorted(buy_orders.items(), reverse=True):
            name, order = elem[0], elem[1]
            if to_divide >= order.initial_cost:
                order.cost = order.initial_cost
            else:
                order.cost = to_divide
            order.status = "potential"
            to_divide -= order.cost
