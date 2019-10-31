# encoding: UTF-8

"""
包含一些开发中常用的函数
"""

import os
import decimal
import json
import traceback
from datetime import datetime, date
from math import isnan
import collections

from six import text_type

# 函数常量
MAX_NUMBER = 10000000000000

MAX_DECIMAL = 4


def json_load_byteified(file_handle):
    return _byteify(
        json.load(file_handle, object_hook=_byteify),
        ignore_dicts=True
    )


def json_loads_byteified(json_text):
    return _byteify(
        json.loads(json_text, object_hook=_byteify),
        ignore_dicts=True
    )


def _byteify(data, ignore_dicts=False):
    # if this is a unicode string, return its string representation
    if isinstance(data, unicode):
        return data.encode('utf-8')
    # if this is a list of values, return list of byteified values
    if isinstance(data, list):
        return [_byteify(item, ignore_dicts=True) for item in data]
    # if this is a dictionary, return dictionary of byteified keys and values
    # but only if we haven't already byteified it
    if isinstance(data, dict) and not ignore_dicts:
        return {
            _byteify(key, ignore_dicts=True): _byteify(value, ignore_dicts=True)
            for key, value in data.iteritems()
        }
    # if it's anything else, return it in its original form
    return data


#----------------------------------------------------------------------
def convert_keys_to_string(data):
    """Recursively converts dictionary keys to strings."""
    if isinstance(data, basestring):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(map(convert_keys_to_string, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(convert_keys_to_string, data))
    else:
        return data


#----------------------------------------------------------------------
def safeUnicode(value):
    """检查接口数据潜在的错误，保证转化为的字符串正确"""
    # 检查是数字接近0时会出现的浮点数上限
    if type(value) is int or type(value) is float:
        if value > MAX_NUMBER or isnan(value):
            value = 0
    
    # 检查防止小数点位过多
    if type(value) is float:
        d = decimal.Decimal(str(value))
        if abs(d.as_tuple().exponent) > MAX_DECIMAL:
            value = round(value, ndigits=MAX_DECIMAL)
    
    return text_type(value)


#----------------------------------------------------------------------
def todayDate():
    """获取当utc日期"""
    return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)


#----------------------------------------------------------------------
def getTempPath(name):
    """获取存放临时文件的路径"""
    tempPath = os.path.join(os.getcwd(), 'temp')
    if not os.path.exists(tempPath):
        os.makedirs(tempPath)
        
    path = os.path.join(tempPath, name)
    return path


#----------------------------------------------------------------------
def defaultformat(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()


# JSON配置文件路径
jsonPathDict = {}

#----------------------------------------------------------------------
def getJsonPath(name, moduleFile):
    """
    获取JSON配置文件的路径：
    1. 优先从当前工作目录下的setting文件夹查找
    """
    currentFolder = os.getcwd()

    currentJsonPath = os.path.join(currentFolder, 'setting', name)
    print(currentJsonPath)
    if os.path.isfile(currentJsonPath):
        jsonPathDict[name] = currentJsonPath
        return currentJsonPath


def loadJsonSetting(settingFileName):
    """加载JSON配置"""
    settingFilePath = getJsonPath(settingFileName, __file__)

    setting = {}

    try:
        with open(settingFilePath, 'rb') as f:
            setting = f.read()
            if type(setting) is not str:
                setting = str(setting, encoding='utf8')
            setting = json.loads(setting)
    except:
        traceback.print_exc()
        return None
    return setting
