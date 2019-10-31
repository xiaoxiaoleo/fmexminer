""""""

import hashlib
import hmac
import sys
import re
import time
import base64
import json
from copy import copy
from datetime import datetime, timedelta
from threading import Lock
from urllib.parse import urlencode

from requests import ConnectionError

from vnpy.event import Event
from vnpy.api.rest import Request, RestClient
from vnpy.api.websocket_fmex import WebsocketClient
from vnpy.trader.event import EVENT_TIMER
from vnpy.trader.constant import (
    Direction,
    Exchange,
    OrderType,
    Product,
    Status,
    Offset,
    Interval
)
from vnpy.trader.gateway import BaseGateway, LocalOrderManager
from vnpy.trader.object import (
    TickData,
    OrderData,
    TradeData,
    PositionData,
    AccountData,
    ContractData,
    BarData,
    OrderRequest,
    CancelRequest,
    SubscribeRequest,
    HistoryRequest
)

REST_HOST = "https://api.fmex.com"
WEBSOCKET_HOST = "wss://api.fmex.com/v2/ws"

TESTNET_REST_HOST = "https://api.testnet.fmex.com"
TESTNET_WEBSOCKET_HOST = "wss://api.testnet.fmex.com/v2/ws"

STATUS_FMEX2VT = {
    "PENDING": Status.NOTTRADED,
    "pending": Status.NOTTRADED,
    "PARTIAL_FILLED": Status.PARTTRADED,
    "FULLY_FILLED": Status.ALLTRADED,
    "FULLY_CANCELLED": Status.CANCELLED,
    "PARTIAL_CANCELLED": Status.CANCELLED,
    "Rejected": Status.REJECTED,
}

DIRECTION_VT2FMEX = {Direction.LONG: "LONG", Direction.SHORT: "SHORT"}
DIRECTION_FMEX2VT = {v: k for k, v in DIRECTION_VT2FMEX.items()}


ORDERTYPE_VT2FMEX = {
    OrderType.LIMIT: "LIMIT",
    OrderType.MARKET: "MARKET",
    OrderType.STOP: "Stop"
}
ORDERTYPE_FMEXX2VT = {v: k for k, v in ORDERTYPE_VT2FMEX.items()}

INTERVAL_VT2FMEX = {
    Interval.MINUTE: "1m",
    Interval.HOUR: "1h",
    Interval.DAILY: "1d",
}

TIMEDELTA_MAP = {
    Interval.MINUTE: timedelta(minutes=1),
    Interval.HOUR: timedelta(hours=1),
    Interval.DAILY: timedelta(days=1),
}


class FmexGateway(BaseGateway):
    """
    VN Trader Gateway for FMEX connection.
    """

    exchanges = [Exchange.FMEX]

    def __init__(self, event_engine):
        """Constructor"""
        super(FmexGateway, self).__init__(event_engine, "FMEX")

        self.order_manager = LocalOrderManager(self)

        self.rest_api = FmexRestApi(self)
        self.ws_api = FmexWebsocketApi(self)

        self.heartbeat_count = 0

        event_engine.register(EVENT_TIMER, self.process_timer_event)

    def connect(self, setting: dict):
        """"""
        key = setting["ID"]
        secret = setting["Secret"]
        session_number = setting["会话数"]
        server = setting["服务器"]
        proxy_host = setting["代理地址"]
        proxy_port = setting["代理端口"]

        if proxy_port.isdigit():
            proxy_port = int(proxy_port)
        else:
            proxy_port = 0

        self.rest_api.connect(key, secret, session_number,
                              server, proxy_host, proxy_port)

        self.ws_api.connect(key, secret, server, proxy_host, proxy_port)
        # websocket will push all account status on connected, including asset, position and orders.

    def subscribe(self, req: SubscribeRequest):
        """"""
        self.ws_api.subscribe(req)

    def send_order(self, req: OrderRequest):
        """"""
        return self.rest_api.send_order(req)

    def cancel_order(self, req: CancelRequest):
        """"""
        self.rest_api.cancel_order(req)

    def query_account(self):
        """"""
        pass

    def query_position(self):
        """"""
        pass

    def query_history(self, req: HistoryRequest):
        """"""
        return self.rest_api.query_history(req)

    def close(self):
        """"""
        self.rest_api.stop()
        self.ws_api.stop()

    def process_timer_event(self, event: Event):
        """"""
        self.rest_api.query_open_order()

        self.heartbeat_count += 1
        if self.heartbeat_count == 10:
            self.ws_api.heartbeat()
            self.heartbeat_count = 0

class FmexRestApi(RestClient):
    """
    FMEX REST API
    """

    def __init__(self, gateway: BaseGateway):
        """"""
        super(FmexRestApi, self).__init__()

        self.gateway = gateway
        self.gateway_name = gateway.gateway_name
        self.order_manager = gateway.order_manager

        self.key = ""
        self.secret = ""
        self.REST_HOST = ""

        self.orders = {}
        self.order_count = 1_000_000
        self.order_count_lock = Lock()

        self.connect_time = 0

        # Use 60 by default, and will update after first request
        self.rate_limit_limit = 60
        self.rate_limit_remaining = 60
        self.rate_limit_sleep = 0

    def connect(
        self,
        key: str,
        secret: str,
        session_number: int,
        server: str,
        proxy_host: str,
        proxy_port: int,
    ):
        """
        Initialize connection to REST server.
        """
        self.key = key
        self.secret = secret

        self.connect_time = (
            int(datetime.now().strftime("%y%m%d%H%M%S")) * self.order_count
        )

        if server == "REAL":
            self.REST_HOST = REST_HOST
            self.init(REST_HOST, proxy_host, proxy_port)
            self.host, _ = _split_url(REST_HOST)
        else:
            self.REST_HOST = TESTNET_REST_HOST
            self.init(TESTNET_REST_HOST, proxy_host, proxy_port)
            self.host, _ = _split_url(TESTNET_REST_HOST)

        self.start(session_number)

        self.gateway.write_log("REST API启动成功")

        self.query_contract()
        self.query_account_balance()
        self.query_open_order()


    def sign(self, request):
        """
        Generate FCOIN signature.
        """
        timestamp = str(int(time.time() * 1000))
        _PATH = request.path

        if request.params:
            param = ''
            sort_pay = sorted(request.params.items())
            for k in sort_pay:
                param += '&' + str(k[0]) + '=' + str(k[1])
            param = param.lstrip('&')
            _PATH += param

        POST_URL = ''
        if request.data:
            POST_URL = urlencode(sorted(request.data.items()))
            request.data = json.dumps(request.data)

        msg = request.method + self.REST_HOST + _PATH + timestamp + POST_URL
        msg = base64.b64encode(msg.encode(encoding='utf-8'))

        signature = hmac.new(self.secret.encode(), msg, digestmod=hashlib.sha1).digest()
        signature = base64.b64encode(signature).decode('utf-8')

        request.headers = {
        'FC-ACCESS-TIMESTAMP' : timestamp,
        'FC-ACCESS-KEY' : self.key,
        'FC-ACCESS-SIGNATURE' : signature,
        "Content-Type" : "application/json"
        }
        return request

    def query_open_order(self):
        """查询挂单"""
        self.add_request(
            method="GET",
            path="/v3/contracts/orders/open",
            callback=self.on_open_order
        )

    def on_open_order(self, data, request):
        """"""
        if len(data["data"]['results']) == 0:
            self.gateway.on_empty_open_order()
        orders = {}
        for d in data["data"]['results']:
            order = self.on_single_order(d)
            #self.gateway.on_order(order)
            orders[order.vt_orderid] = order

        self.gateway.on_orders(orders)

        self.gateway.write_log("挂单查询成功")

    def on_send_order(self, data, request):
        """"""
        d = data['data']
        sys_orderid = d["id"]
        order = self.orders.get(sys_orderid, None)
        if not order:
            order = self.on_single_order(d)
            self.gateway.on_order(order)
        self.gateway.write_log(f"委托发送成功{order.price}")
        #self.gateway.write_log("委托发送成功")

    def on_single_order(self, d):
        sys_orderid = d["id"]
        order = self.orders.get(sys_orderid, None)

        if not order:
            order_type = ORDERTYPE_FMEXX2VT[d["type"].upper()]
            direction = DIRECTION_FMEX2VT[d["direction"].upper()]
            dt = datetime.fromtimestamp(d["created_at"] / 1000)
            time = dt.strftime("%H:%M:%S")

            if "symobol" in d.keys():
                symbol = d["symbol"].upper()
            else:
                symbol = "BTCUSD_P"

            status = STATUS_FMEX2VT.get(d["status"], None)
            order = OrderData(
                sysordid=sys_orderid,
                orderid=sys_orderid,
                symbol=symbol,
                exchange=Exchange.FMEX,
                price=d["price"],
                volume=d["quantity"],
                type=order_type,
                direction=direction,
                traded=0,
                status=status,
                time=time,
                gateway_name=self.gateway_name,
            )

            self.orders[sys_orderid] = order

        traded = d["quantity"] - d['unfilled_quantity']
        status = STATUS_FMEX2VT.get(d["status"], None)
        order.traded = traded
        order.status = status

        return order

    def query_contract(self):
        """"""
        self.add_request(
            method="GET",
            path="/v2/public/contracts/symbols",
            callback=self.on_contract
        )

    def on_contract(self, data, request):
        """"""

        for d in data["data"]:
            contract = ContractData(
                symbol=d['name'].upper(),
                exchange=Exchange.FMEX,
                name=d["name"],
                product=Product.FUTURES,
                pricetick=d['minimum_price_increment'],
                size=1,
                min_volume=1,
                gateway_name=self.gateway_name,
            )
            self.gateway.on_contract(contract)

        self.gateway.write_log("合约信息查询成功")

    def query_account_balance(self):
        """"""
        self.add_request(
            method="GET",
            path="/v3/contracts/accounts",
            callback=self.on_query_account_balance
        )

    def on_query_account_balance(self, data, request):
        """"""
        for k,v in data["data"].items():
            account = AccountData(
                accountid= k,
                balance=  v[0],
                frozen= v[1],
                gateway_name=self.gateway_name,
            )

            if account.balance:
                self.gateway.on_account(account)


    def send_order(self, req: OrderRequest):
        """"""
        local_orderid = 1111111

        order = req.create_order_data(local_orderid, self.gateway_name)
        order.time = datetime.now().strftime("%H:%M:%S")

        data = {
            "symbol": req.symbol.upper(),
            "direction": DIRECTION_VT2FMEX[req.direction],
            "type": ORDERTYPE_VT2FMEX[req.type],
            "quantity": int(req.volume)
        }

        inst = []   # Order special instructions

        # Only add price for limit order.
        if req.type == OrderType.LIMIT:
            data["price"] = req.price
        elif req.type == OrderType.STOP:
            data["trigger_on"] = req.price
            inst.append("LastPrice")

        self.add_request(
            "POST",
            "/v3/contracts/orders",
            callback=self.on_send_order,
            data=data,
            extra=order,
            on_failed=self.on_send_order_failed,
            on_error=self.on_send_order_error,
        )

        #
        return order.vt_orderid

    def cancel_order(self, req: CancelRequest):
        """"""
        self.add_request(
            "POST",
            f"/v3/contracts/orders/{req.sysordid}/cancel",
            callback=self.on_cancel_order,
            on_error=self.on_cancel_order_error,
        )

    def on_cancel_order(self, data, request):
        """Websocket will push a new order status"""
        d = data['data']
        order = self.on_single_order(d)
        self.gateway.on_order(order)
        #self.gateway.write_log("委托取消成功")
        self.gateway.write_log(f"委托取消成功{order.price}")

    def query_history(self, req: HistoryRequest):
        """"""
        pass


    def on_send_order_failed(self, status_code: str, request: Request):
        """
        Callback when sending order failed on server.
        """
        self.update_rate_limit(request)

        order = request.extra
        order.status = Status.REJECTED
        #self.gateway.on_order(order)

        if request.response.text:
            data = request.response.json()
            msg = f"委托失败： {status_code} {data}"
        else:
            msg = f"委托失败，状态码：{status_code}"

        self.gateway.write_log(msg)

    def on_send_order_error(
        self, exception_type: type, exception_value: Exception, tb, request: Request
    ):
        """
        Callback when sending order caused exception.
        """
        order = request.extra
        order.status = Status.REJECTED
        self.gateway.on_order(order)

        # Record exception if not ConnectionError
        if not issubclass(exception_type, ConnectionError):
            self.on_error(exception_type, exception_value, tb, request)


    def on_cancel_order_error(
        self, exception_type: type, exception_value: Exception, tb, request: Request
    ):
        """
        Callback when cancelling order failed on server.
        """
        # Record exception if not ConnectionError
        if not issubclass(exception_type, ConnectionError):
            self.on_error(exception_type, exception_value, tb, request)


    def on_failed(self, status_code: int, request: Request):
        """
        Callback to handle request failed.
        """
        data = request.response.json()
        msg = f"请求失败，状态码：{status_code} {data}"
        self.gateway.write_log(msg)

    def on_error(
        self, exception_type: type, exception_value: Exception, tb, request: Request
    ):
        """
        Callback to handler request exception.
        """
        msg = f"触发异常，状态码：{exception_type}，信息：{exception_value}"
        self.gateway.write_log(msg)

        sys.stderr.write(
            self.exception_detail(exception_type, exception_value, tb, request)
        )

    def update_rate_limit(self, request: Request):
        """
        Update current request limit remaining status.
        """
        pass

    def reset_rate_limit(self):
        """
        Reset request limit remaining every 1 second.
        """
        pass

    def check_rate_limit(self):
        """
        Check if rate limit is reached before sending out requests.
        """
        pass


class FmexWebsocketApi(WebsocketClient):
    """"""

    def __init__(self, gateway):
        """"""
        super(FmexWebsocketApi, self).__init__()

        self.gateway = gateway
        self.gateway_name = gateway.gateway_name

        self.key = ""
        self.secret = ""

        self.callbacks = {}

        self.ticks = {}

    def connect(
        self, key: str, secret: str, server: str, proxy_host: str, proxy_port: int
    ):
        """"""
        self.key = key
        self.secret = secret.encode()

        if server == "REAL":
            self.init(WEBSOCKET_HOST, proxy_host, proxy_port)
        else:
            self.init(TESTNET_WEBSOCKET_HOST, proxy_host, proxy_port)

        self.start()

    def subscribe(self, req: SubscribeRequest):
        """
        Subscribe to tick data upate.
        """
        tick = TickData(
            symbol=req.symbol,
            exchange=req.exchange,
            name=req.symbol,
            datetime=datetime.now(),
            gateway_name=self.gateway_name,
        )
        self.ticks[req.symbol] = tick



    def on_connected(self):
        """"""
        self.gateway.write_log("Websocket API连接成功")

    def on_disconnected(self):
        """"""
        self.gateway.write_log("Websocket API连接断开")

    def on_packet(self, packet: dict):
        """"""
        if packet['type'] == "hello":
            self.gateway.write_log("Websocket API验证授权成功")
            self.subscribe_topic()

        elif 'ticker' in packet['type']:
            self.on_ticker(packet)

        elif 'depth' in packet['type']:
            self.on_depth(packet)

    def on_ticker(self, d):
        """"""
        symbol = d['type'].split('.')[-1]
        tick = self.ticks.get(symbol, None)

        if not tick:
            return

        ticker = d['ticker']
        tick.open = ticker[6]
        tick.high = ticker[7]
        tick.low = ticker[8]
        tick.last_price = ticker[0]
        tick.volume = ticker[9]

    def on_error(self, exception_type: type, exception_value: Exception, tb):
        """"""
        msg = f"触发异常，状态码：{exception_type}，信息：{exception_value}"
        self.gateway.write_log(msg)

        sys.stderr.write(self.exception_detail(
            exception_type, exception_value, tb))

    def subscribe_topic(self):
        """
        Subscribe to all private topics.
        """
        req = {"cmd": "sub", "args": ["depth.L20.btcusd_p"]}
        self.send_packet(req)

    def heartbeat(self):
        timestamp = int(time.time())
        req = {"cmd":"ping","args":[timestamp],"id":"coray1912"}
        self.send_packet(req)

    def on_depth(self, d):
        """"""
        symbol = d['type'].split('.')[-1].upper()
        tick = self.ticks.get(symbol, None)
        if not tick:
            return

        bids = d["bids"]
        asks = d["asks"]

        tick.bid_price_1 = bids[0]
        tick.bid_price_2 = bids[2]
        tick.bid_price_3 = bids[4]
        tick.bid_price_4 = bids[6]
        tick.bid_price_5 = bids[8]
        tick.bid_price_6 = bids[10]
        tick.bid_price_7 = bids[12]
        tick.bid_price_8 = bids[14]
        tick.bid_price_9 = bids[16]
        tick.bid_price_10 = bids[18]
        tick.bid_volume_1 = bids[1]
        tick.bid_volume_2 = bids[3]
        tick.bid_volume_3 = bids[5]
        tick.bid_volume_4 = bids[7]
        tick.bid_volume_5 = bids[9]
        tick.bid_volume_6 = bids[11]
        tick.bid_volume_7 = bids[13]
        tick.bid_volume_8 = bids[15]
        tick.bid_volume_9 = bids[17]
        tick.bid_volume_10 = bids[19]

        tick.ask_price_1 = asks[0]
        tick.ask_price_2 = asks[2]
        tick.ask_price_3 = asks[4]
        tick.ask_price_4 = asks[6]
        tick.ask_price_5 = asks[8]
        tick.ask_price_6 = asks[10]
        tick.ask_price_7 = asks[12]
        tick.ask_price_8 = asks[14]
        tick.ask_price_9 = asks[16]
        tick.ask_price_10 = asks[18]
        tick.ask_volume_1 = asks[1]
        tick.ask_volume_2 = asks[3]
        tick.ask_volume_3 = asks[5]
        tick.ask_volume_4 = asks[7]
        tick.ask_volume_5 = asks[9]
        tick.ask_volume_6 = asks[11]
        tick.ask_volume_7 = asks[13]
        tick.ask_volume_8 = asks[15]
        tick.ask_volume_9 = asks[17]
        tick.ask_volume_10 = asks[19]
        tick.datetime = datetime.fromtimestamp(d['ts'] / 1000)

        self.gateway.on_tick(copy(tick))


    def on_trade(self, d):
        """"""
        pass

def _split_url(url):
    """
    将url拆分为host和path
    :return: host, path
    """
    result = re.match("\w+://([^/]*)(.*)", url)  # noqa
    if result:
        return result.group(1), result.group(2)
