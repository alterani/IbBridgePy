# -*- coding: utf-8 -*-
"""
Created on Wed Aug 22 23:50:16 2018

@author: IBridgePy@gmail.com
"""


class DataProvider:
    def __init__(self):
        self.log = None
        self.loadingHistPlan = set()
        # The format of self.hist should be self.hist[str_security][barSize]
        # self.hist should be loaded by self.dataProvider.get_historical_data()
        self.hist = {}
        self.client = None  # the client to the real dataProvider

    @property
    def name(self):
        """
        Name of the data provider

        :return: string name
        """
        raise NotImplementedError()

    def setLog(self, log):
        self.log = log
        return self

    def setLoadingHistPlan(self, plan):
        self.loadingHistPlan = plan
        return self

    def load_plans(self):
        raise NotImplementedError

    def setClient(self, client):
        """
        client setter. The client MUST be successfully connected.
        :param client:
        :return: void
        """
        self.client = client
        return self

    # real response
    def get_real_time_prices(self, security, timeNow):
        raise NotImplementedError

    # real response
    def getHistoricalData(self, security, str_endTime, str_goBack, str_barSize, str_whatToShow, int_useRTH,
                          int_formatDate):
        """

        :param security: IBridgePy::quantopian::Security
        :param str_endTime: request's ending time with format yyyyMMdd HH:mm:ss {TMZ} ---from IB api doc
        :param str_goBack:
        :param str_barSize: string 1 sec, 5 secs, 15 secs, 30 secs, 1 min, 2 mins, 3 mins, 5 mins, 15 mins,
                                30 mins, 1 hour, 1 day
        :param str_whatToShow:
        :param int_useRTH:
        :param int_formatDate:
        :return:
        """
        raise NotImplementedError
