# -*- coding: utf-8 -*-
"""
Created on Wed Aug 22 23:50:16 2018

@author: IBridgePy@gmail.com
"""

from .data_provider import DataProvider


class InteractiveBrokers(DataProvider):

    def get_historical_data(self):
        pass

    @property
    def name(self):
        return 'InteractiveBrokers'

    def get_real_time_prices(self, security, timeNow):  # return real time price
        print(self.client)
        a = self.client.show_real_time_price(security, 'open')
        b = self.client.show_real_time_price(security, 'high')
        c = self.client.show_real_time_price(security, 'low')
        d = self.client.show_real_time_price(security, 'close')
        e = self.client.show_real_time_price(security, 'volume')
        return a, b, c, d, e
