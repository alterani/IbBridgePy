#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Sat Feb 10 09:26:48 2018

@author: IBridgePy

There is a risk of loss in stocks, futures, forex and options trading. Please
trade with capital you can afford to lose. Past performance is not necessarily
indicative of future results. Nothing in this computer program/code is intended
to be a recommendation to buy or sell any stocks or futures or options or any
tradeable securities.
All information and computer programs provided is for education and
entertainment purpose only; accuracy and thoroughness cannot be guaranteed.
Readers/users are solely responsible for how they use the information and for
their results.

If you have any questions, please send email to IBridgePy@gmail.com
"""

from sys import exit
import pandas as pd
import datetime as dt
import os
import time
import pytz
from IBridgePy.quantopian import Security
from IBridgePy.constants import SymbolStatus, OrderType, RunMode


def calculate_startTime(endTime, goBack, barSize):
    # 1S = 1 second; 1T = 1 minute; 1H = 1 hour
    global startTime
    endTime = dt.datetime.strptime(endTime, "%Y%m%d %H:%M:%S %Z")  # string -> dt.datetime
    if barSize == '1 second':
        endTime = endTime.replace(microsecond=0)
    elif barSize == '1 minute':
        endTime = endTime.replace(second=0, microsecond=0)
    elif barSize == '1 hour':
        endTime = endTime.replace(minute=0, second=0, microsecond=0)
    elif barSize == '1 day':
        endTime = endTime.replace(hour=0, minute=0, second=0, microsecond=0)

    if 'S' in goBack:
        startTime = endTime - dt.timedelta(seconds=int(goBack[:-1]))
    elif 'D' in goBack:
        startTime = endTime - dt.timedelta(days=int(goBack[:-1]))
    elif 'W' in goBack:
        startTime = endTime - dt.timedelta(weeks=int(goBack[:-1]))
    elif 'Y' in goBack:
        startTime = endTime.replace(endTime.year - int(goBack[:-1]))
    return startTime, endTime


def add_exchange_primaryExchange_to_security(security):
    """
    seucity_info.csv must stay in this directory with this file
    :param security:
    :return:
    """
    stockList = pd.read_csv(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'security_info.csv'))
    if security.exchange == '':
        security.exchange = search_security_in_file(stockList, security.secType, security.symbol,
                                                    security.currency, 'exchange')
    if security.primaryExchange == '':
        security.primaryExchange = search_security_in_file(stockList, security.secType, security.symbol,
                                                           security.currency, 'primaryExchange')
    return security


def symbol(str_security):
    security = from_symbol_to_security(str_security)
    return add_exchange_primaryExchange_to_security(security)


def from_symbol_to_security(s1):
    if ',' not in s1:
        s1 = 'STK,%s,USD' % (s1,)

    secType = s1.split(',')[0].strip()
    ticker = s1.split(',')[1].strip()
    currency = s1.split(',')[2].strip()
    if secType in ['CASH', 'STK']:
        return Security(secType=secType, symbol=ticker, currency=currency)
    else:
        print('Definition of %s is not clear!' % (s1,))
        print('Please use superSymbol to define a security')
        print(r'http://www.ibridgepy.com/ibridgepy-documentation/#superSymbol')
        exit()


def superSymbol(secType=None,
                ticker=None,
                currency='USD',
                exchange='',
                primaryExchange='',
                expiry='',
                strike=0.0,
                right='',
                multiplier='',
                includeExpired=False):
    return Security(secType=secType, symbol=ticker, currency=currency, exchange=exchange,
                    primaryExchange=primaryExchange, expiry=expiry, strike=strike, right=right,
                    multiplier=multiplier, includeExpired=includeExpired, symbolStatus=SymbolStatus.SUPER_SYMBOL)


def read_in_hash_config(fileName):
    full_file_path = os.path.join(os.getcwd(), 'IBridgePy', fileName)
    return read_hash_config(full_file_path)


def read_hash_config(full_file_path):
    if os.path.isfile(full_file_path):
        with open(full_file_path) as f:
            line = f.readlines()
        return line[0].strip()
    else:
        print('hash.conf file is missing at %s. EXIT' % (str(full_file_path),))
        exit()


def search_security_in_file(df, secType, ticker, currency, param, waive=False):
    if secType == 'CASH':
        if param == 'exchange':
            return 'IDEALPRO'
        elif param == 'primaryExchange':
            return 'IDEALPRO'
        else:
            error_messages(5, secType + ' ' + ticker + ' ' + param)
    else:
        tmp_df = df[(df['Symbol'] == ticker) & (df['secType'] == secType) & (df['currency'] == currency)]
        if tmp_df.shape[0] == 1:  # found 1
            exchange = tmp_df['exchange'].values[0]
            primaryExchange = tmp_df['primaryExchange'].values[0]
            if param == 'exchange':
                if type(exchange) == float:
                    if secType == 'STK':
                        return 'SMART'
                    else:
                        error_messages(4, secType + ' ' + ticker + ' ' + param)
                else:
                    return exchange
            elif param == 'primaryExchange':
                if type(primaryExchange) == float:
                    return ''
                return primaryExchange
            else:
                error_messages(5, secType + ' ' + ticker + ' ' + param)
        elif tmp_df.shape[0] > 1:  # found more than 1
            error_messages(3, secType + ' ' + ticker + ' ' + param)
        else:  # found None
            if waive:
                return 'WAIVED'
            error_messages(4, secType + ' ' + ticker + ' ' + param)


def error_messages(n, st):
    if n == 1:
        print ('Definition of %s is not clear!' % (st,))
        print ('Please add this security in IBridgePy/security_info.csv')
        exit()
    elif n == 2:
        print ('Definition of %s is not clear!' % (st,))
        print ('Please use superSymbol to define a security')
        print (r'http://www.ibridgepy.com/ibridgepy-documentation/#superSymbol')
        exit()
    elif n == 3:
        print ('Found too many %s in IBridgePy/security_info.csv' % (st,))
        print ('%s must be unique.' % (' '.join(st.split(' ')[:-1]),))
        exit()
    elif n == 4:
        print ('Exchange of %s is missing.' % (' '.join(st.split(' ')[:-1]),))
        print ('Please add this security in IBridgePy/security_info.csv')
        exit()
    elif n == 5:
        print ('%s of %s is missing.' % (st.split(' ')[-1], ' '.join(st.split(' ')[:-1])))
        print ('Please add this info in IBridgePy/security_info.csv')
        exit()


def transform_action(amount):
    if amount > 0:
        return 'BUY', 'SELL', amount
    else:
        return 'SELL', 'BUY', -1 * amount


def special_match(target, val, version):
    if target == 'any':
        return True
    else:
        if version == 'monthWeek':
            if target >= 0:
                return target == val[0]
            else:
                return target == val[1]
        elif version == 'hourMinute':
            return target == val
        else:
            print (__name__ + '::_match: EXIT, cannot handle version=%s' % (version,))
            exit()


def print_contract(contract):
    """
    IBCpp.Contract() cannot use __str__ to print so that make a print-function
    :param contract: IBCpp.Contract()
    :return: String
    """
    base = ['secType', 'primaryExchange', 'exchange', 'symbol', 'currency']
    stkCash = base
    fut = base + ['expiry']
    other = fut + ['strike', 'right', 'multiplier']
    ans = ''
    if contract.secType in ['STK', 'CASH']:
        iterator = stkCash
    elif contract.secType in ['FUT', 'BOND']:
        iterator = fut
    else:
        iterator = other
    for para in iterator:
        ans += str(getattr(contract, para)) + ','
    return ans[:-1]


def print_IB_order(order):
    """
    IBCpp.Order() cannot use __str__ to print so that make a print-function
    :param order: IBCpp.Order()
    :return: String
    """
    action = order.action  # BUY, SELL
    amount = order.totalQuantity  # int only
    orderType = order.orderType  # LMT, MKT, STP
    tif = order.tif
    orderRef = order.orderRef

    ans = '%s %s %s %s %s' % (action, orderType, str(amount), str(tif), orderRef)
    if orderType == OrderType.MKT:
        pass
    elif orderType == OrderType.LMT:
        ans += ' limitPrice=' + str(order.lmtPrice)
    elif orderType == OrderType.STP:
        ans += ' stopPrice=' + str(order.auxPrice)
    elif orderType == OrderType.TRAIL_LIMIT:
        if order.auxPrice < 1e+307:
            ans += ' trailingAmount=' + str(order.auxPrice)
        if order.trailingPercent < 1e+307:
            ans += ' trailingPercent=' + str(order.trailingPercent)
        ans += ' trailingStopPrice=' + str(order.trailStopPrice)
    return ans


def display_all_contractDetails(contractDetails):
    for item in ['conId', 'symbol', 'secType', 'LastTradeDateOrContractMonth',
                 'strike', 'right', 'multiplier', 'exchange', 'currency',
                 'localSymbol', 'primaryExchange', 'tradingClass',
                 'includeExpired', 'secIdType', 'secId', 'comboLegs', 'underComp',
                 'comboLegsDescrip']:
        try:
            print (item, getattr(contractDetails.summary, item))
        except AttributeError:
            print (item, 'not found')
    for item in ['marketName', 'minTick', 'priceMagnifier', 'orderTypes',
                 'validExchanges', 'underConId', 'longName', 'contractMonth',
                 'industry', 'category', 'subcategory',
                 'timeZoneId', 'tradingHours', 'liquidHours',
                 'evRule', 'evMultiplier', 'mdSizeMultiplier', 'aggGroup',
                 'secIdList',
                 'underSymbol', 'underSecType', 'marketRuleIds', 'realExpirationDate',
                 'cusip', 'ratings', 'descAppend',
                 'bondType', 'couponType', 'callable', 'putable',
                 'coupon', 'convertible', 'maturity', 'issueDate',
                 'nextOptionDate', 'nextOptionType', 'nextOptionPartial',
                 'notes']:
        try:
            print (item, getattr(contractDetails, item))
        except AttributeError:
            print (item, 'not found in contractDetails')


def from_arg_to_pandas_endCheckList(args):
    ans = pd.DataFrame()
    temp = 0
    for ct in args:
        newRow = pd.DataFrame({'reqId': ct.reqId, 'status': ct.status,
                               'waiver': bool(ct.waiver), 'reqData': ct,
                               'reqType': ct.reqType, 'resendOnFailure': ct.resendOnFailure}, index=[temp])
        temp += 1
        ans = ans.append(newRow)
    return ans


def simulate_commissions(order):
    # self.log.debug(__name__ + '::simulate_commission: $0.0075 per share or $1.00')
    return max(order.totalQuantity * 0.0075, 1.0)


SHORT_PERIOD = {2, 3, 4, 5, 6, 10, 15, 20, 30}
LONG_PERIOD = {120, 180, 300, 900, 1800}


def make_fake_time(startTime=dt.datetime(2018, 1, 1, 8, 25), endTime=dt.datetime(2018, 8, 1, 10, 35)):
    # 1S = 1min; 1T = 1 minute; 1H = 1 hour
    tmp = pd.date_range(startTime, endTime, freq='1T', tz=pytz.timezone('US/Eastern'))
    for ct in tmp:
        yield ct.to_pydatetime()


def make_local_time_generator():
    while True:
        yield pytz.timezone('UTC').localize(dt.datetime.now())


class Iter:
    def __init__(self, generator):
        self.generator = generator

    def get_next(self):
        return next(self.generator)


class Repeater:
    def __init__(self, freq, do_something, stopFunc=None):
        """

        :param freq:
        :param do_something:
        :param stopFunc: True = stop repeater
        """
        self.freq = freq
        self.do_something = do_something
        if stopFunc is None:
            self.stopFunc = self.alwaysFalse
        else:
            self.stopFunc = stopFunc

    @staticmethod
    def alwaysTrue():
        return True

    @staticmethod
    def alwaysFalse():
        return False

    def run_once(self, timeNow, timePrevious):
        #
        if self.stopFunc():
            return

        if self.freq == 1:
            if timeNow.second != timePrevious.second or timeNow.minute != timePrevious.minute:
                self.do_something(timeNow, timePrevious)
        elif self.freq == 60:  # 1 minute, like quantopian style
            if timeNow.minute != timePrevious.minute or timeNow.hour != timePrevious.hour:
                self.do_something(timeNow, timePrevious)
        elif self.freq in SHORT_PERIOD:
            if timeNow.second % self.freq == 0 and timePrevious.second % self.freq != 0:
                self.do_something(timeNow, timePrevious)
        elif self.freq in LONG_PERIOD:  # 1 min,2min,3min,5min,15min,30min
            for ct in range(0, 60, int(self.freq / 60)):
                if timeNow.minute == ct and timePrevious.minute != ct:
                    self.do_something(timeNow, timePrevious)
        elif self.freq == 3600:  # hourly
            if timeNow.hour != timePrevious.hour:
                self.do_something(timeNow, timePrevious)
        else:
            print(__name__ + '::repeat_Function: cannot handle repBarFreq=%i' % (freq,))
            exit()


class RepeaterEngine:
    def __init__(self, runMode, getTimeNowFuncGlobal, stopFuncGlobal=None):
        self.repeaters = set()  # hold all individual repeaters
        self.getTimeNowFuncGlobal = getTimeNowFuncGlobal
        self.stopFuncGlobal = stopFuncGlobal
        self.timePrevious = dt.datetime(1970, 1, 1, 0, 0, 0)
        self.runMode = runMode

    def scheduler(self, repeater):
        self.repeaters.add(repeater)

    def repeat(self):
        while not self.stopFuncGlobal():
            try:
                timeNow = self.getTimeNowFuncGlobal()
            except StopIteration:
                break
            for repeater in self.repeaters:
                repeater.run_once(timeNow, self.timePrevious)

            # slow down for live mode
            if self.runMode != RunMode.BACK_TEST:
                time.sleep(0.5)
            self.timePrevious = timeNow

