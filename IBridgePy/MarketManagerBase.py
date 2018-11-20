# -*- coding: utf-8 -*-
"""
Module MarketManager

"""
import datetime as dt
from IBridgePy.IbridgepyTools import special_match, Repeater, Iter, make_fake_time, make_local_time_generator, \
    RepeaterEngine
from sys import exit
import time
import broker_factory as broker_factory
from IBridgePy.constants import BrokerName, DataProviderName, RunMode
import data_provider_factory
from IBridgePy.loading_historical_data import create_a_loading_plan
import os

BEFORE_TRADING_START = {'run_like_quantopian', 'sudo_run_like_quantopian', 'test_run'}


class MarketManager:
    """
    Market Manager will run trading strategies according to the market hours.
    It should contain a instance of IB's client, properly initialize the connection
    to IB when market starts, and properly close the connection when market closes
    """

    def __init__(self, trader, marketCalendar, runMode, host='', port=7496, clientId=99,
                 brokerName=BrokerName.IB, dataProviderName=DataProviderName.IB):
        self.host = host
        self.port = port
        self.clientId = clientId
        self.aTrader = trader
        self.aTrader.log.notset(__name__ + '::__init__')

        self.lastCheckConnectivityTime = dt.datetime.now()
        self.numberOfConnection = 0

        # a flag to know if before_trading_start should run
        self.beforeTradingStartFlag = True

        # get market open/close time every day
        # run_like_quantopian will run following these times
        self.marketCalendar = marketCalendar

        # It will be checked only once at the beginning of a new day
        # then, the status will be saved for the whole day
        # Only use in run_like_quantopian mode
        self.runScheduledOrHandleDataToday = True
        self.todayMarketOpenTime = None
        self.todayMarketCloseTime = None

        # Record the last display message
        # When a new message is to be displayed, it will compare with the last
        # message. If they are not same, then display it
        self.lastDisplayMessage = ''

        self.runMode = runMode

        self.brokerName = brokerName
        self.brokerService = broker_factory.get_broker(self.brokerName)()

        self.dataProviderName = dataProviderName
        self.dataProvider = data_provider_factory.get_data_provider(self.dataProviderName)()

    # prepare before real actions
    def get_connected_to_IB(self):
        """
        initialization of the connection to IB
        updated account
        """
        self.aTrader.log.notset(__name__ + '::get_connected_to_IB')
        self.aTrader.disconnect()
        self.numberOfConnection += 1
        if self.aTrader.connect(self.host, self.port, self.clientId):  # connect to server
            self.aTrader.log.debug(__name__ + ": " + "Connected to IB, port = " +
                                   str(self.port) + ", ClientID = " + str(self.clientId))
            self.numberOfConnection = 0  # reset counter after a successful connection
            self.aTrader.connectionGatewayToServer = True  # it will be used in run_regular
            return True
        else:
            self.aTrader.log.error(__name__ + '::get_connected_to_IB: Not connected')
        time.sleep(1)
        return False

    # clean up after real actions
    def disconnect(self):
        """
        disconnect from IB and close log file
        """
        self.aTrader.log.info('IBridgePy: Disconnect')
        self.aTrader.disconnect()

    def before_run(self):
        self.aTrader.log.debug(__name__ + '::before_run:')
        self.aTrader.log.info('brokerName = %s; dataProviderName = %s' % (self.brokerName, self.dataProviderName))
        if self.brokerName == BrokerName.LOCAL_BROKER:

            # Set up dataProvider, needs to set up log, loadingHistPlan
            self.dataProvider.setLog(self.aTrader.log)
            folderPath = os.path.join(self.aTrader.rootFolderName, 'Input')  # all data files must stay in Input folder
            loadingPlan = create_a_loading_plan(folderPath).getFinalPlan()  # this is a Set()
            self.dataProvider.setLoadingHistPlan(loadingPlan)
            self.dataProvider.load_plans()

            # Set up brokerService
            self.brokerService.setLog(self.aTrader.log)  # set log
            self.brokerService.setDataProvider(self.dataProvider)  # set dataProvider

            # set aTrader to brokerService and set brokerService to aTrader
            # so that they can call each other's functions, for example, Test_trader_single_account
            self.brokerService.setTrader(self.aTrader)  # so that brokerService can call aTrader.xxx
            self.aTrader.brokerService = self.brokerService  # so that aTrader can call brokerService.reqMktData in TEST

    def run(self):
        self.aTrader.log.debug(__name__ + '::run: START')

        # Prepare for backtesting
        self.before_run()

        # live trading
        if self.runMode in RunMode.LIVE:  # a list
            self.aTrader.setRunningMode(1)  # 1: live mode 2: backtesting mode
            if self.get_connected_to_IB():  # if not get connected, IBridgePy will exit when errorCode comes in
                if self.runMode == RunMode.RUN_LIKE_QUANTOPIAN:
                    self.aTrader.log.info('runMode = run_like_quantopian;' + ' marketCalendarName = %s'
                                          % (self.marketCalendar.marketCalendarName,))
                else:
                    self.aTrader.log.info('runMode = %s' % (self.runMode,))

                c = Iter(make_local_time_generator())  # generate real time series for live trading
                self.aTrader.setLocalMachineTime(c.get_next())
                self.aTrader.initialize_Function()

                # c.get_next() + self.aTrader.localServerTimeDiff is used to simulate IB server time
                # r = Repeater(self.runMode,
                #             getTimeNowFunc=(lambda: c.get_next() + self.aTrader.localServerTimeDiff),
                #             stopFunc=self.aTrader.getWantToEnd)
                # r.repeat(self.aTrader.repBarFreq, self.base_process)

                re = RepeaterEngine(RunMode.LIVE,
                                    (lambda: c.get_next() + self.aTrader.localServerTimeDiff),
                                    self.aTrader.getWantToEnd)
                repeater1 = Repeater(1, self.aTrader.process_messages)
                repeater2 = Repeater(self.aTrader.repBarFreq, self.base_process)
                re.scheduler(repeater1)
                re.scheduler(repeater2)
                re.repeat()

        # backtesting
        elif self.runMode == RunMode.BACK_TEST:
            self.aTrader.setRunningMode(2)  # 1: live mode 2: backtesting mode
            c = Iter(make_fake_time())  # prepare the backtesting time series

            # before initialize, it needs to set time. The first time in the backtesting time series is consumed
            self.aTrader.setLocalMachineTime(c.get_next())

            # set money value in account to start backtest
            self.aTrader.context.portfolio.cash = 100000.00
            self.aTrader.context.portfolio.portfolio_value = 100000.00
            self.aTrader.context.portfolio.positions_value = 0.0

            self.aTrader.initialize_Function()

            #
            r = Repeater(self.runMode, getTimeNowFunc=c.get_next, stopFunc=self.aTrader.getWantToEnd)
            r.repeat(self.aTrader.repBarFreq, self.base_process)
        else:
            print(__name__ + '::run: Cannot handle runMode = %s' % (self.runMode,))
            exit()

    def before_base_process(self, timeNow, timePrevious):
        """
        backtest mode, need to fill in real time data before every handle_data()
        :param timeNow:
        :param timePrevious:
        :return: True= get real time data, False= no real time data
        """
        self.aTrader.log.debug(__name__ + '::before_base_process' + str(timeNow) + ' ' + str(timePrevious))

        # set simulated real time prices
        # if return True, it means got real time data
        if self.brokerService.getMktData(timeNow):

            # simulated processing orders
            self.brokerService.processOrder()
            return True
        else:
            return False

    def base_process(self, timeNow, timePrevious):
        self.aTrader.log.debug(__name__ + '::base_process' + str(timeNow) + ' ' + str(timePrevious))
        self.aTrader.processMessages()
        self.aTrader.setLocalMachineTime(timeNow)
        if self.runMode == RunMode.REGULAR:
            self.aTrader.repeat_Function()
        else:
            self.base_process_QUANTOPIAN(timeNow, timePrevious)

    def base_process_QUANTOPIAN(self, timeNow, timePrevious):
        self.aTrader.log.debug(__name__ + '::base_process_QUANTOPIAN' + str(timeNow) + ' ' + str(timePrevious))

        # check if today is a trading day when a new day starts
        # return:
        # self.runScheduledOrHandleDataToday
        # return marketOpenTime and marketCloseTime if it is a trading day
        if timeNow.day != timePrevious.day or timeNow.month != timePrevious.month or timeNow.year != timePrevious.year:
            self._check_at_beginning_of_a_day(timeNow)

        # if today is not a trading day and nothing is scheduled today, just do nothing
        if not self.runScheduledOrHandleDataToday:
            self._display_message('%s is not a trading day and nothing is scheduled today, IBridgePy is still running'
                                  % (str(self.aTrader.get_datetime().date(),)))
            return

        # run handle_data and scheduledFunc if market opens
        if self.todayMarketOpenTime <= timeNow < self.todayMarketCloseTime:
            if self.runMode == RunMode.BACK_TEST:
                if self.before_base_process(timeNow, timePrevious):
                    self.aTrader.repeat_Function()
            else:
                self.aTrader.repeat_Function()

        # if the market is closed now
        else:
            # run before_trading_start_function if market is closed now.
            if self.runMode in BEFORE_TRADING_START:
                self._run_before_trading_start_quantopian(timeNow, spotHour=9, spotMinute=20)

    def _run_before_trading_start_quantopian(self, timeNow, spotHour, spotMinute):
        self.aTrader.log.notset(__name__ + '::_run_before_trading_start_quantopian:' + str(timeNow))
        if timeNow.hour == spotHour and timeNow.minute == spotMinute:
            self.aTrader.before_trading_start_quantopian(self.aTrader.context, self.aTrader.qData)

    def _check_at_beginning_of_a_day(self, timeNow):
        self.aTrader.log.debug(__name__ + '::_check_at_beginning_of_a_day')
        if not self.marketCalendar.trading_day(timeNow):
            self.runScheduledOrHandleDataToday = False
        else:
            self.aTrader.runScheduledFunctionsToday = \
                self.check_date_rules(timeNow.date(), self.aTrader.scheduledFunctionList)
            self.runScheduledOrHandleDataToday = \
                self.aTrader.runScheduledFunctionsToday or self.aTrader.runHandleDataFlag
            if self.runScheduledOrHandleDataToday:
                self.todayMarketOpenTime, self.todayMarketCloseTime = \
                    self.marketCalendar.get_market_open_close_time(timeNow)

    def _display_message(self, message):
        if message != self.lastDisplayMessage:
            print('MarketManager::' + message)
            self.lastDisplayMessage = message

    # When connection to IB Gateway is lost, errorCode 502, 504, 509, etc will come in
    # the code should not exit if run_auto_connection is True
    # So, autoConnectedToGateway should be an attr of Trader, instead of marketManager.
    # TODO implement autoconnection
    # TODO marketManager can run multi trader at anytime to parallel
    def run_auto_connection(self, tryTimes=3):
        self.aTrader.wantToEnd = False
        while self.numberOfConnection <= tryTimes:
            self.run()
            if self.aTrader.wantToEnd:
                break
            else:
                self.aTrader.log.error(__name__ + '::run_auto_connection:wait 30 seconds to reconnect')
                time.sleep(30)
                if self.numberOfConnection > tryTimes:
                    break
        if not self.aTrader.wantToEnd:
            print (__name__ + '::run_auto_connection: END. tried 3 times but cannot connect to Gateway.')
        else:
            print (__name__ + '::run_auto_connection: END')

    # it is not very useful because IB Gateway will automatically get reconnected to IB server during nightly shutdown
    # However, it might be useful when user want to detect any abnormal connection and send out warning signals.
    def check_connectivity(self):
        if not self.aTrader.connectionGatewayToServer:
            return True

        setTimer = dt.datetime.now()
        # print (setTimer-self.lastCheckConnectivityTime).total_seconds()
        if (setTimer - self.lastCheckConnectivityTime).total_seconds() < 30:
            return True
        self.aTrader.log.debug(__name__ + '::check_connectivity')
        self.aTrader.nextId = None
        self.aTrader.reqIds(0)
        checkTimer = dt.datetime.now()
        while (checkTimer - setTimer).total_seconds() < 0.5:
            self.aTrader.processMessages()
            if self.aTrader.nextId is not None:
                self.lastCheckConnectivityTime = checkTimer
                self.aTrader.log.debug(__name__ + '::check_connectivity:GOOD')
                return True
            self.aTrader.log.debug(__name__ + '::check_connectivity:checking ...')
            time.sleep(0.05)
            checkTimer = dt.datetime.now()
        self.aTrader.log.debug(__name__ + '::check_connectivity:BAD')
        return False

    def check_date_rules(self, aDay, scheduledFunctionList):
        """
        Input:
        aDay: dt.date only for faster

        Algo:
        if schedule_funtion is [], then run everyday
        else, strictly follow schedule_function defines !!! IMPORTANT

        Output:
        set self.runToday to True(run repeat_func today) or False
        """
        self.aTrader.log.debug(__name__ + '::check_date_rules: aDay=%s' % (str(aDay),))
        # if type(aDay) == dt.datetime:
        #    aDay = aDay.date()
        self.aTrader.monthDay = self.marketCalendar.nth_trading_day_of_month(aDay)
        self.aTrader.weekDay = self.marketCalendar.nth_trading_day_of_week(aDay)
        # print (monthDay, weekDay)
        if self.aTrader.monthDay is None or self.aTrader.weekDay is None:
            self.aTrader.log.debug(__name__ + '::check_date_rules: %s = not trading date' % (str(aDay),))
            return False
        else:
            if scheduledFunctionList is list:
                return True
            for ct in scheduledFunctionList:
                # print (ct.onNthMonthDay, ct.onNthWeekDay)
                if special_match(ct.onNthMonthDay, self.aTrader.monthDay, 'monthWeek') \
                        and special_match(ct.onNthWeekDay, self.aTrader.weekDay, 'monthWeek'):
                    return True
            self.aTrader.log.debug(__name__ + '::check_date_rules: %s = nothing scheduled today' % (str(aDay),))
            return False


if __name__ == '__main__':
    pass
