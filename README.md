# Fmex Miner
FMEX.com Miner. Fmex挂单挖矿程序，薅羊毛程序。

## 环境要求
- Python3.7

## Ubuntu 环境搭建
1. apt-get install build-essential python3.7-dev
2. pip install -r requirements.txt

## 配置FMEX的API KEY
1. 将setting文件夹拷贝到$HOME目录下，并在setting/fmex_test.json里面配置自己的API KEY
```angular2
{
        "ID": "这里填key",
        "Secret": "这里填secret"

}
```
## 切换成生产环境，编辑fmex_guadan.py
```
    conn_setting = {
        "会话数": 3,
        "服务器": "REAL", #REAL是生产环境 TESTNET是测试环境
        "代理地址": "",
        "代理端口": '',
        "symbols":symbol
    }
```
## 配置挂单参数
- 根据自己需求更改fmex_guadan.py
```angular2

        "volume": 900,                  #一笔挂单量，单位USD
        "interval":2,                   #每隔多少秒循环一次挂单函数
        "minimum_distance": 40,         #离盘口的最小距离，单位USD
        "guadan_max_count": 15,         #单方向挂单最大数量
```
- *guadan_max_count 设置范围15-25，也就是说总挂单量在30-50左右差不多，minimum_distance 取决于行情波动大不大，一般35左右即可，volume越大越好，interval 2秒左右没问题。该程序目的是挂单避免成交，所以项目中并没有自动处理仓位代码。
- *本程序基于vnpy框架，所有逻辑都在fmexminer/vnpy/app/fmex_miner_guadan/engine.py文件中。

## 运行
- python3.7 fmex_guadan.py 


## 挂单程序关闭后，由于挂单比较多，可以执行清理订单程序取消所有挂单。
- python3.7 fmex_clean_order.py


