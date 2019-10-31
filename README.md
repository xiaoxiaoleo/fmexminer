# fmexminer
FMEX.com Miner. Fmex挂单挖矿，薅羊毛程序。

## 环境要求
- Python3.7

## Ubuntu 环境搭建
1. apt-get install build-essential python3.7-dev
2. pip install -r requirements.txt

## 配置FMEX的API KEY
1. 将setting文件夹拷贝到$HOME目录下，在fmex_test.json里面配置自己的API KEY
```angular2
{
        "ID": "这里填key",
        "Secret": "这里填secret"

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

## 运行
- python3.7 fmex_guadan.py 


## 挂单程序关闭后，由于挂单比较多，可以执行清理订单程序取消所有挂单。
- python3.7 fmex_clean_order.py


