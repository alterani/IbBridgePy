# -*- coding: utf-8 -*-
"""
Created on Thu Aug 17 23:50:16 2017

@author: IBridgePy@gmail.com
"""
from BasicPyLib.small_tools import dt_to_utc_in_seconds
from IBridgePy.quantopian import from_security_to_contract


class Broker:
    def __init__(self):
        self.aTrader = None
        self.log = None
        self.tickTransformer = {'bid_price': 1,
                                'ask_price': 2,
                                'last_traded': 4,
                                'high': 6,
                                'low': 7,
                                'close': 9,
                                'open': 14,
                                'volume': 8
                                }

        # key is str of a security, without exchange / primaryExchange
        # str as key is a method to easier searching
        # Value is a tuple (the reqId of reqMktData, security)
        self.mktDataRequest = {}

        # to pull in historical data
        self.dataProvider = None

    @property
    def name(self):
        """
        Name of the broker

        :return: string name
        """
        raise NotImplementedError()

    def setTrader(self, aTrader):
        self.aTrader = aTrader

    def setLog(self, log):
        self.log = log

    def setDataProvider(self, dataProvider):
        self.dataProvider = dataProvider

    def get_real_time_prices(self, security, timeNow):  # return real time price
        """
        broker will get data from dataProvider
        Must stay here because all brokers need to provide this function
        :param timeNow:
        :param security:
        :return: tuple (openPrice, highPrice, lowPrice, closePrice, volume)
        """
        raise NotImplementedError

    def get_account_info(self, accountCode, tag):  # get account related info
        raise NotImplementedError

    def get_positions(self, accountCode):
        raise NotImplementedError

    def get_orders(self, accountCode):
        raise NotImplementedError

    def reqHistoricalData(self, reqId, contract, endTime, goBack, barSize, whatToShow, useRTH, formatDate):
        raise NotImplementedError

    def sendHistoricalData(self, hist, reqId, formatDate):
        for idx in hist.index:
            if formatDate == 1:
                date = idx.to_pydatetime()
                date = date.strftime("%Y%m%d %H:%M:%S")  # Must be UTC because requested time was cast to UTC
            else:
                date = str(idx)
            self.aTrader.historicalData(reqId, date, hist.loc[idx, 'open'],
                                        hist.loc[idx, 'high'],
                                        hist.loc[idx, 'low'],
                                        hist.loc[idx, 'close'],
                                        hist.loc[idx, 'volume'],
                                        None, None, None)
        self.aTrader.historicalData(reqId, 'finished', None, None, None, None, None, None, None, None)

    def placeOrder(self, orderId, contract, order):
        raise NotImplementedError
        # self.log.debug(__name__ + '::placeOrder')

    def processOrder(self):
        raise NotImplementedError

    def reqMktData(self, reqId, contract, genericTicks, snapshot):
        raise NotImplementedError

    def getMktData(self, timeNow):
        self.log.debug(__name__ + '::getMktData')
        if len(self.mktDataRequest) == 0:
            self.log.debug(__name__ + '::getMktData: Empty mktDataRequest')
            return True

        for str_security in self.mktDataRequest:
            reqId, security = self.mktDataRequest[str_security]
            openPrice, highPrice, lowPrice, closePrice, volume = self.get_real_time_prices(security, timeNow)
            if openPrice is not None:
                self.aTrader.tickPrice(reqId, self.tickTransformer['ask_price'], closePrice, canAutoExecute=False)
                self.aTrader.tickPrice(reqId, self.tickTransformer['bid_price'], closePrice, canAutoExecute=False)
                self.aTrader.tickPrice(reqId, self.tickTransformer['open'], openPrice, canAutoExecute=False)
                self.aTrader.tickPrice(reqId, self.tickTransformer['high'], highPrice, canAutoExecute=False)
                self.aTrader.tickPrice(reqId, self.tickTransformer['low'], lowPrice, canAutoExecute=False)
                self.aTrader.tickPrice(reqId, self.tickTransformer['close'], closePrice, canAutoExecute=False)
                self.aTrader.tickPrice(reqId, self.tickTransformer['last_traded'], closePrice, canAutoExecute=False)
                self.aTrader.tickSize(reqId, self.tickTransformer['volume'], volume)
            else:
                self.log.debug(__name__ + '::getMktData: No data!!!')
                return False
        return True

    def reqPositions(self):
        self.log.debug(__name__ + '::reqPositions')
        for ct in self.aTrader.PORTFOLIO.positions:
            self.aTrader.position(self.aTrader.accountCode, from_security_to_contract(ct),
                                  self.aTrader.PORTFOLIO.positions.amount,
                                  self.aTrader.PORTFOLIO.positions.cost_basis)
        self.aTrader.positionEnd()
