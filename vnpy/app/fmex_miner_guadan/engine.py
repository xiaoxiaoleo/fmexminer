import time
from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine
from vnpy.trader.event import (
    EVENT_TICK, EVENT_TIMER, EVENT_ORDER, EVENT_TRADE)
from vnpy.trader.constant import (Direction, Offset, OrderType)
from vnpy.trader.object import (OrderRequest)



APP_NAME = "FcoinMiner"

EVENT_ALGO_LOG = "eAlgoLog"
EVENT_ALGO_SETTING = "eAlgoSetting"
EVENT_ALGO_VARIABLES = "eAlgoVariables"
EVENT_ALGO_PARAMETERS = "eAlgoParameters"


class AlgoEngine(BaseEngine):
    """"""

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        """Constructor"""
        super().__init__(main_engine, event_engine, APP_NAME)
        self.price_tick =0
        self.interval = 999999
        self.vt_symbol = None
        self.volume = 0
        self.last_tick = None
        self.register_event()
        self.timer_count = 1
        self.start_pcent=1
        self.end_pcent=1
        self.algo = 'algoname'
        self.guadan_max_count = 0
        self.sleep = 0
        self.contract = None


    def init_engine(self, setting: dict):
        """"""
        self.write_log("算法交易引擎启动")
        self.vt_symbol = setting["vt_symbol"]
        self.volume =  setting["volume"]
        self.interval = setting["interval"]
        self.minimum_distance = setting['minimum_distance']
        self.guadan_max_count = int(setting['guadan_max_count'])
        self.algo = setting['algo_name']

        self.contract = self.get_contract(self.vt_symbol)

        while not self.contract:
            time.sleep(2)

        self.price_tick = self.get_contract(self.vt_symbol).pricetick

    def start_engine(self):
        pass


    def register_event(self):
        """"""
        self.event_engine.register(EVENT_TICK, self.process_tick_event)
        self.event_engine.register(EVENT_TIMER, self.process_timer_event)
        self.event_engine.register(EVENT_ORDER, self.process_order_event)
        self.event_engine.register(EVENT_TRADE, self.process_trade_event)

    def process_tick_event(self, event: Event):
        """"""
        self.last_tick = event.data

    def process_timer_event(self, event: Event):
        """"""
        if not self.last_tick:
            return

        self.timer_count += 1

        if self.timer_count < self.interval:
            return

        self.timer_count = 0

        price_list_old = []

        if self.volume == 0:
            self.write_log('Order volume == 0')
            return

        open_order_list = self.main_engine.engines['oms'].orders

        # x个挂单应该是程序紊乱，全撤
        if len(open_order_list) > (self.guadan_max_count*2 + 4):
            for vt_orderid,vt_order in open_order_list.items():
                self.cancel_order(self.algo,vt_orderid)
            return

        short_start_price = self.last_tick.ask_price_1 + self.minimum_distance
        short_end_price = short_start_price + 15
        long_start_price = self.last_tick.bid_price_1 - self.minimum_distance
        long_end_price = long_start_price - 15

        range_price = 5

        for vt_orderid, vt_order in open_order_list.items():
            price_list_old.append(vt_order.price)
            if vt_order.direction == Direction.SHORT:
                if ((vt_order.price <   (short_start_price - range_price)) or ( vt_order.price  > (short_end_price + range_price))):
                    self.cancel_order(self.algo,vt_orderid)
            if vt_order.direction == Direction.LONG:
                if ((vt_order.price >   (long_start_price + range_price)) or ( vt_order.price  <   (long_end_price - range_price))):
                    self.cancel_order(self.algo,vt_orderid)

        if (self.guadan_max_count*2 - len(open_order_list)) < 4:
            return

        for i in range(0, self.guadan_max_count):
            self.sell_new_short_order(short_start_price + 0.5 * i, price_list_old)
            self.sell_new_long_order(long_start_price - 0.5 * i, price_list_old)

    def sell_new_short_order(self, price, price_list_old):
        if price not in price_list_old:
            self.send_order(self.algo, self.vt_symbol, Direction.SHORT, price, self.volume, OrderType.LIMIT, offset=Offset)

    def sell_new_long_order(self, price, price_list_old):
        if price not in price_list_old:
            self.send_order(self.algo, self.vt_symbol, Direction.LONG, price, self.volume, OrderType.LIMIT, offset=Offset)

    def process_trade_event(self, event: Event):
        """"""
        pass

    def process_order_event(self, event: Event):
        """"""
        pass


    def subscribe(self):
        """"""
        pass

    def send_order(
        self,
        algo: str,
        vt_symbol: str,
        direction: Direction,
        price: float,
        volume: float,
        order_type: OrderType,
        offset: Offset
    ):
        """"""
        contract = self.main_engine.get_contract(vt_symbol)
        if not contract:
            self.write_log(f'委托下单失败，找不到合约：{vt_symbol}', algo)
            return

        req = OrderRequest(
            symbol=contract.symbol,
            exchange=contract.exchange,
            direction=direction,
            type=order_type,
            volume=volume,
            price=price,
            offset=offset
        )
        self.main_engine.send_order(req, contract.gateway_name)


    def cancel_order(self, algo: str, vt_orderid: str):
        """"""
        order = self.main_engine.get_order(vt_orderid)

        if not order:
            self.write_log(f"委托撤单失败，找不到委托：{vt_orderid}", algo)
            return

        req = order.create_cancel_request()
        self.main_engine.cancel_order(req, order.gateway_name)

    def get_tick(self, vt_symbol: str):
        """"""
        pass

    def get_contract(self, vt_symbol: str):
        """"""
        contract = self.main_engine.get_contract(vt_symbol)

        if not contract:
            self.write_log(f"查询合约失败，找不到合约：{vt_symbol}")

        return contract

    def get_order(self, vt_orderid: str):
        pass


    def write_log(self, msg: str, algo: str = None):
        """"""
        if algo:
            msg = f"{algo}：{msg}"

        event = Event(EVENT_ALGO_LOG)
        event.data = msg
        self.event_engine.put(event)

