import time
import random
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
        self.write_log("Fmex clean 算法交易引擎启动")
        self.algo = setting['algo_name']

        self.contract = self.get_contract(self.vt_symbol)

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

        open_order_list = self.main_engine.engines['oms'].orders

        for vt_orderid,vt_order in open_order_list.items():
            self.cancel_order(self.algo,vt_orderid)



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
        pass

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

