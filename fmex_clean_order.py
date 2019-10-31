# encoding: UTF-8
from vnpy.event import EventEngine

from vnpy.trader.engine import MainEngine

from vnpy.gateway.fmex import FmexGateway

from vnpy.app.fcoin_clean_order import AlgoTradingApp
from vnpy.trader.object import SubscribeRequest
from vnpy.trader.constant import Exchange
from vnpy.trader.vtFunction import loadJsonSetting
import time
def main():
    """"""

    event_engine = EventEngine()

    main_engine = MainEngine(event_engine)
    main_engine.add_gateway(FmexGateway)

    gateway_name = "FMEX"
    symbol = "BTCUSD_P"
    api_key = loadJsonSetting('fmex_test.json')
    conn_setting = {
        "会话数": 3,
        "服务器": "TESTNET", #REAL
        "代理地址": "",
        "代理端口": '',
        "symbols":symbol
    }
    conn_setting = {**api_key, **conn_setting}

    req = SubscribeRequest(
        symbol=symbol, exchange=Exchange(gateway_name)
    )

    main_engine.connect(conn_setting, gateway_name)
    main_engine.subscribe(req, gateway_name)


    app_setting = {"template_name": 'MinerAlgo',
        "vt_symbol": symbol + "." + gateway_name,
        "algo_name":'FCOIN_Miner_guadan'

    }

    APP_NAME = "FcoinMiner"
    main_engine.add_app(AlgoTradingApp)
    algo_engine = main_engine.get_engine(APP_NAME)
    time.sleep(5)
    algo_engine.init_engine(app_setting)
    algo_engine.start_engine()


if __name__ == "__main__":
    main()
