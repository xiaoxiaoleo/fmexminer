# encoding: UTF-8
from vnpy.event import EventEngine

from vnpy.trader.engine import MainEngine

from vnpy.gateway.fmex import FmexGateway

from vnpy.app.fmex_miner_guadan import AlgoTradingApp
from vnpy.trader.object import SubscribeRequest
from vnpy.trader.constant import Exchange
from vnpy.trader.vtFunction import loadJsonSetting

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
        "服务器": "TESTNET", #REAL,TESTNET
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
        "volume": 900,                  #一笔挂单量，单位USD
        "interval":2,                   #每隔多少秒循环一次挂单函数
        "minimum_distance": 40,         #离盘口的最小距离，单位USD
        "guadan_max_count": 15,         #单方向挂单最大数量
        "algo_name":'FCOIN_Miner_guadan'

    }

    APP_NAME = "FcoinMiner"
    main_engine.add_app(AlgoTradingApp)
    algo_engine = main_engine.get_engine(APP_NAME)
    algo_engine.init_engine(app_setting)
    algo_engine.start_engine()


if __name__ == "__main__":
    main()
