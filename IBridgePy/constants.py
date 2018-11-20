# -*- coding: utf-8 -*-
"""
Created on Wed Aug 21 23:50:16 2018

@author: IBridgePy@gmail.com
"""


class BrokerName:
    LOCAL_BROKER = 'LocalBroker'
    IB = 'InteractiveBrokers'

    def __init__(self):
        pass


class DataProviderName:
    LOCAL_FILE = 'LocalFile'
    RANDOM = 'Random'
    IB = 'InteractiveBrokers'

    def __init__(self):
        pass


class RUNNING_MODE:
    LIVE = 1
    BACKTEST = 2

    def __init__(self):
        pass


class SymbolStatus:
    DEFAULT = 0
    SUPER_SYMBOL = 1
    ADJUSTED = 2

    def __init__(self):
        pass


class RunMode:
    REGULAR = 'regular'
    RUN_LIKE_QUANTOPIAN = 'run_like_quantopian'
    SUDO_RUN_LIKE_QUANTOPIAN = 'sudo_run_like_quantopian'
    LIVE = [REGULAR, RUN_LIKE_QUANTOPIAN, SUDO_RUN_LIKE_QUANTOPIAN]
    BACK_TEST = 'back_test'

    def __init__(self):
        pass


class OrderStatus:
    PRESUBMITTED = 'PreSubmitted'
    SUBMITTED = 'Submitted'
    CANCELLED = 'Cancelled'

    def __init__(self):
        pass


class OrderType:
    MKT = 'MKT'
    LMT = 'LMT'
    STP = 'STP'
    TRAIL_LIMIT = 'TRAIL LIMIT'

    def __init__(self):
        pass


class FollowUpRequest:
    FOLLOW_UP = False  # used in ReqData, waiver = False means Need to follow up
    DO_NOT_FOLLOW_UP = True

    def __init__(self):
        pass


class Default:
    DEFAULT = 'default'

    def __init__(self):
        pass


class ReqHistParam:
    def __init__(self):
        pass

    class Name:
        def __init__(self):
            pass

        BAR_SIZE = 'barSize'
        GO_BACK = 'goBack'
        END_TIME = 'endTime'

    class BarSize:
        def __init__(self):
            pass

        ONE_MIN = '1 min'

    class GoBack:
        def __init__(self):
            pass

        ONE_DAY = '1 day'


class ExchangeName:
    ISLAND = 'ISLAND'

    def __init__(self):
        pass


