import time
import datetime as dt
import pytz
import pandas as pd
from sys import exit
import random
import os
import numpy as np


def localTzname():
    is_dst = time.localtime().tm_isdst
    if time.daylight and is_dst > 0:
        offsetHour = time.altzone / 3600
    else:
        offsetHour = time.timezone / 3600
    return 'Etc/GMT%+d' % offsetHour


def dt_to_utc_in_seconds(a_dt, showTimeZone=None):
    """
    dt.datetime.fromtimestamp
    the return value depends on local machine timezone!!!!
    So, dt.datetime.fromtimestamp(0) will create different time at different machine
    """
    # print (__name__+'::dt_to_utc_in_seconds: EXIT, read function comments')
    # exit()
    if a_dt.tzinfo is None:
        if showTimeZone:
            a_dt = showTimeZone.localize(a_dt)
        else:
            a_dt = pytz.utc.localize(a_dt)
            # print(__name__+'::dt_to_utc_in_seconds:EXIT, a_dt is native time, showTimeZone must be not None')
            # exit()
    return (a_dt.astimezone(pytz.utc) - dt.datetime(1970, 1, 1, 0, 0, tzinfo=pytz.utc)).total_seconds()


def if_market_is_open(dt_aTime, start='9:30', end='16:00', early_end='13:00', version='true_or_false'):
    holiday = [dt.date(2015, 11, 26), dt.date(2015, 12, 25),
               dt.date(2016, 1, 1), dt.date(2016, 1, 18), dt.date(2016, 2, 15),
               dt.date(2016, 3, 25), dt.date(2016, 5, 30), dt.date(2016, 7, 4),
               dt.date(2016, 9, 5), dt.date(2016, 11, 24), dt.date(2016, 12, 26)]
    earlyClosing = [dt.date(2015, 11, 27), dt.date(2015, 12, 24)]
    # fmt = '%Y-%m-%d %H:%M:%S %Z%z'
    if dt_aTime.tzinfo is None:
        print ('small_tools::if_market_is_open: cannot handle timezone unaware datetime', dt_aTime)
        exit()

    dt_aTime = dt_aTime.astimezone(pytz.timezone('US/Eastern'))
    if dt_aTime.weekday() == 6 or dt_aTime.weekday() == 5:
        # print 'weekend'
        if version == 'true_or_false':
            return False
        else:
            return None
    if dt_aTime.date() in holiday:
        # print 'holiday'
        if version == 'true_or_false':
            return False
        else:
            return None

    if dt_aTime.date() in earlyClosing:
        marketStartTime = dt_aTime.replace(hour=int(start.split(':')[0]), minute=int(start.split(':')[1]), second=0)
        marketCloseTime = dt_aTime.replace(hour=int(early_end.split(':')[0]), minute=int(early_end.split(':')[1]),
                                           second=0)
    else:
        marketStartTime = dt_aTime.replace(hour=int(start.split(':')[0]), minute=int(start.split(':')[1]), second=0)
        marketCloseTime = dt_aTime.replace(hour=int(end.split(':')[0]), minute=int(end.split(':')[1]), second=0)

    if version == 'market_close_time':
        return marketCloseTime
    elif version == 'market_open_time':
        return marketStartTime
    elif version == 'true_or_false':
        if dt_aTime >= marketStartTime and dt_aTime < marketCloseTime:
            # print marketStartTime.strftime(fmt)
            # print marketCloseTime.strftime(fmt)
            # print 'OPEN '+dt_aTime.strftime(fmt)
            return True
        else:
            # print marketStartTime.strftime(fmt)
            # print marketCloseTime.strftime(fmt)
            # print 'CLOSE '+dt_aTime.strftime(fmt)
            return False
    else:
        print ('small_tools::if_market_is_open: EXIT, Cannot handle version=', version)
        exit()


def market_time(dt_aTime, version):
    global tp
    if dt_aTime.tzinfo is None:
        print ('small_tools::market_time: cannot handle timezone unaware datetime', dt_aTime)
        exit()
    if version == 'open_time':
        tp = if_market_is_open(dt_aTime, version='market_open_time')
    elif version == 'close_time':
        tp = if_market_is_open(dt_aTime, version='market_close_time')
    else:
        print ('small_tools::market_time: EXIT, Cannot handle version=', version)
        exit()

    if tp is None:
        print ('market is closed today', dt_aTime)
        return None
    else:
        return tp


def add_realtimeBar_to_hist(data, sec, hist_frame):
    data[sec].hist[hist_frame] = data[sec].hist[hist_frame].drop(
        data[sec].hist[hist_frame].index[-1])  # remove the last line, potential uncompleted data
    # print data[context.sec].hist[hist_frame].tail()
    # print data[context.sec].realTimeBars

    tmp = pd.DataFrame(data[sec].realTimeBars,
                       columns=['sysTime', 'datetime', 'open', 'high', 'low', 'close', 'volume', 'wap', 'count'])
    tmp['datetime'] = tmp['datetime'].apply(lambda x: dt.datetime.fromtimestamp(x))
    tmp = tmp.set_index('datetime')
    tmp = tmp.resample('30s', how={'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'})

    for idx in tmp.index:
        if idx in data[sec].hist[hist_frame].index:
            # print 'drop',idx
            tmp = tmp.drop(idx)
        else:
            break
    # print tmp
    if len(tmp) >= 1:
        data[sec].hist[hist_frame] = data[sec].hist[hist_frame].append(tmp)
    # print data[context.sec].hist[hist_frame].tail()
    if len(data[sec].hist[hist_frame]) > 100:
        data[sec].hist[hist_frame] = data[sec].hist[hist_frame].drop(data[sec].hist[hist_frame].index[0])


def get_system_info():
    import platform
    import sys
    platform = platform.system()
    if 'Anaconda' in sys.version:
        python = 'Anaconda'
    else:
        python = 'native Python'
    version = str(sys.version_info.major) + '.' + str(sys.version_info.minor)
    return platform, python, version


def rounding(num, miniTick=0.01):
    if miniTick != 0:
        return int(num / miniTick) * miniTick
    else:
        return int(num)


def create_random_hist(startTime, endTime, barSize, miniTick):
    """

    :param startTime: dt.datetime
    :param endTime: dt.datetime
    :param barSize: 1S = 1 second; 1T = 1 minute; 1H = 1 hour
    :param miniTick: float, 0.01, 0.05, 0.1, etc.
    :return: pd.DataFrame('open', 'high', 'low', 'close', 'volume'), index = datetime
    """
    ans = pd.DataFrame()
    index = pd.date_range(startTime, endTime, freq=barSize, tz=pytz.timezone('US/Eastern'))
    for dateTime in index:
        openPrice = random.uniform(50, 100)
        closePrice = openPrice * random.uniform(0.95, 1.05)
        highPrice = max(openPrice, closePrice) * random.uniform(1, 1.05)
        lowPrice = max(openPrice, closePrice) * random.uniform(0.95, 1)

        newRow = pd.DataFrame({'open': rounding(openPrice, miniTick),
                               'high': rounding(highPrice, miniTick),
                               'low': rounding(lowPrice, miniTick),
                               'close': rounding(closePrice, miniTick),
                               'volume': random.randint(10000, 50000)},
                              index=[int(dt_to_utc_in_seconds(dateTime))])
        ans = ans.append(newRow)
    return ans


class TimeParser:
    def __init__(self):
        pass

    @property
    def strToDatetime(self):
        return lambda x: pytz.timezone('US/Eastern').localize(
            dt.datetime.strptime(x[:-6], '%Y-%m-%d %H:%M:%S'))

    @property
    def none(self):
        return None


def read_file_to_dataFrame(fullFilePath):
    return pd.read_csv(fullFilePath, index_col=0)


def save_dataFrame_to_file(df, saveTo='default'):
    if saveTo == 'default':
        saveTo = os.path.join(os.getcwd(), 'testData.csv')
    df.to_csv(saveTo)


def TEST_creat_hist_and_save():
    startTime = dt.datetime(2018, 8, 1, 9, 30)
    endTime = dt.datetime(2018, 8, 1, 16, 0)
    barSize = '1 min'
    miniTick = 0.01
    df = create_random_hist(startTime, endTime, barSize, miniTick)
    save_dataFrame_to_file(df)


def TEST_read_file_to_dataFrame(path):
    df = read_file_to_dataFrame(path)
    print(df.tail())

    a_datetime = pytz.timezone('US/Eastern').localize(dt.datetime(2018, 8, 1, 16, 0))

    a_dt = np.int64(dt_to_utc_in_seconds(a_datetime))
    # tm = pytz.timezone('US/Pacific').localize(a_dt)
    #tm = pytz.timezone('US/Eastern').localize(a_dt)
    print(type(a_dt), a_dt)
    print(type(df.index[-1]))
    print(a_dt in df.index)


class Data:
    def __init__(self, limit=100):
        self.data = list()  # data list to save values
        self.limit = limit  # the max number of the length of the data list

    def add(self, value):
        """
        Add value to the data list and remove the 1st value if the length of the list is too long
        :param value: value to be added to the list
        :return: void
        """
        self.data.append(value)
        if len(self.data) > self.limit:
            self.data = self.data[1:]

    def calculate(self, n):
        """
        User-defined the calculation
        :param n: user-defined xTime
        :return: calculated value
        """

        if n <= 1:
            print("n must >= 2")
            exit()
        if len(self.data) < n:
            return 0.0
        average = sum(self.data[-n:]) / n * 1.0
        return (average - self.data[-n]) / (n - 1) * 100.0

    def length(self):
        return len(self.data)

if __name__ == '__main__':
    #TEST_creat_hist_and_save()

    TEST_read_file_to_dataFrame('/Users/huiliu/Documents/YellowstoneIBridgePy/BasicPyLib/testData.csv')
