# -*- coding: utf-8 -*-
"""
Created on Thu Aug 17 23:50:16 2017

@author: IBridgePy@gmail.com
"""

from IBridgePy.constants import BrokerName


def get_broker(name):
    if name == BrokerName.IB:
        from .interactiveBrokers import InteractiveBrokers
        return InteractiveBrokers


