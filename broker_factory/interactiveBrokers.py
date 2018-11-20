# -*- coding: utf-8 -*-
"""
Created on Thu Aug 17 23:50:16 2017

@author: IBridgePy@gmail.com
"""

from .broker import Broker


class InteractiveBrokers(Broker):
    @property
    def name(self):
        return "InteractiveBrokers"

    def get_real_time_prices(self, security):  # return real time price
        raise NotImplementedError

    def get_historical_data(self):
        raise NotImplementedError

    def place_order(self, accountCode, security, amount, orderType):  # to place order
        raise NotImplementedError

    def get_account_info(self, accountCode, tag):  # get account related info
        raise NotImplementedError

    def get_positions(self, accountCode):
        raise NotImplementedError

    def get_orders(self, accountCode):
        raise NotImplementedError



