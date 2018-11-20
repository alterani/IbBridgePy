import time
import pytz
import pandas as pd
import BasicPyLib.simpleLogger as simpleLogger
from IBridgePy.quantopian import ContextClass, QDataClass, ReqData
from IBridgePy.Trader_single_account import SingleTrader
from IBridgePy.IbridgepyTools import read_in_hash_config, special_match
import os

SHORT_PERIOD = {2, 3, 4, 5, 6, 10, 15, 20, 30}
LONG_PERIOD = {120, 180, 300, 900, 1800}


class Trader(SingleTrader):
    """
    TickTraders are IBAccountManager too, so TickTraders inherits from IBAccountManager.
    """

    fileName = ''
    versionNumber = ''

    # This set is used to track what accountCodes have been called back from IB server.
    accountCodeCallBackSet = set()

    # For Single Account version, the input accountCode is saved here
    accountCode = ''

    # For Multi Account version, the set of input accountCode will be saved here, and used later
    accountCodeSet = set()

    # Default is single account = False, multiAccount = True
    multiAccountFlag = False

    # same as context and data in quantopian
    context = None
    qData = None  # wrapper of data, because of data.current and data.history

    # Quantopian's basic functions will be saved here
    before_trading_start_quantopian = None
    initialize_quantopian = None
    handle_data_quantopian = None

    # handle_data is not required anymore. This flag will only be used in backtest mode to decide if backtester
    # should run handle_data or not during the backtesting
    runHandleDataFlag = False

    # In run_like_quantopian mode, at the beginning of a day, run code to check if
    # scheduled_functions should run on that day. This is the flag. It will be saved for the whole day.
    runScheduledFunctionsToday = False

    # simulated IB server time,
    # in the test_run, it will be returned as results of get_datetime()
    simulatedServerTime = None

    # a flag, quantopian style = False
    runScheduledFunctionBeforeHandleData = False

    # The list of securities
    # The critial information is exchange and primaryExchange
    # The keys to search is secType, symbol and currency
    # the function to search is in IbrigepyTools.py
    stockList = None

    # When change a contract to a security, it needs to check if exchange
    # info and primaryExchange info are available.
    # False: To check
    # True: Not check. It means self._search_security_in_qData will return
    # NA for exchange and primaryExchange if not found.
    securityCheckWaiver = False

    # Whenever there is a new request/requests, request_data() will create
    # a new dataFrame filled by information. Then the newly created dataFrame
    # is passed to self.end_check_list in req_info_from_server() to submit
    # them to IB. The callback information will check self.end_check_list first
    # then, save results as instruction.
    # IBAccountManager._from_arg_to_pandas_endEheckList defines the
    # the columns of self.end_check_list
    # columns:
    #      str reqId
    #      str status
    #      bool waiver
    #      ReqData reqData
    #      str reqType
    # pandas dataframe is used here because it is easier to filter
    # self.end_check_list and self.end_check_list_result will be
    # initialized whenever IBAccountManager.req_info_from_server is called.
    # After prepare_reqId(), the self.end_check_list is keyed by real reqId
    end_check_list = pd.DataFrame()

    # self.end_check_list_result is to save callback information
    end_check_list_result = {}

    # a flag to show if the connection between IB Gateway/TWS and IB server
    # is good or not
    # The most important usage is to ignore the connection check between
    # IBridgePy and IB Gateway/TWS
    # Must stay here because errorCode will change it
    connectionGatewayToServer = False

    # a Flag to tell if hist data has come in or request_hist has some error
    # set it to False when submit request
    # set it to True after received 1st hist line
    # it will be turned on after connection is established.
    # it will be turned off after errorId=1100
    receivedHistFlag = False

    # these two param are used in quantopian mode
    # For schedule function
    # They will be put in a value at the beginning of everyday
    # check_date_rules in MarketManagerBase.py
    monthDay = None
    weekDay = None

    # MarketMangerBase will monitor it to stop
    # False is want to run
    wantToEnd = False

    scheduledFunctionList = []  # record all of user scheduled function conditions

    # record all realTimeRequests to avoid repeat calls
    realTimePriceRequestedList = {}

    # a flag to decide if display_all() should work
    # in test_run mode, tester will request historical data first
    # in this case, there is no need to display account info.
    displayFlag = True

    # in the run_like_quantopian mode
    # the system should use Easter timezone as the system time
    # self.sysTimeZone will be used for this purpose
    sysTimeZone = pytz.timezone('US/Eastern')

    # record server UTC time and the local time
    # when the first server time comes in
    # when the current server time is needed, used dt.datetime.now()
    # to calculate
    recordedServerUTCtime = None  # float, utc number
    recordedLocalTime = None  # a datetime, without tzinfo

    # passed in broker, so that backtester can use broker's funcitons
    brokerService = None

    # Save the current folder path so that it can be used to load any files
    # for example, security_info.csv, and dataProvider
    rootFolderName = ''

    loading_plan = None  # should be a function, to define how to load hist data into back tester

    log = None
    userLog = None
    logLevel = None
    showTimeZone = None
    maxSaveTime = None
    repBarFreq = 0
    waitForFeedbackInSeconds = 0
    repeat = 0

    def setup_trader(self,
                     fileName='defaultFileName',
                     accountCode='All',
                     logLevel='INFO',
                     showTimeZone='US/Eastern',
                     maxSaveTime=1800,
                     waitForFeedbackInSeconds=30,
                     repeat=3,
                     repBarFreq=1,
                     securityCheckWaiver=False,
                     runScheduledFunctionBeforeHandleData=False,
                     handle_data_quantopian=None,  # a function name is passed in.
                     initialize_quantopian=None,  # a function name is passed in.
                     before_trading_start_quantopian=None):  # optical function

        """
        initialize the IBAccountManager. We don't do __init__ here because we don't
        want to overwrite parent class IBCpp.IBClient's __init__ function
        stime: IB server time when it is first received. localTime is the local
        computer time when first IB server time is received. The following IB
        server time is simulated by stime,localTime and dt.datetime.now()
        maxSaveTime: max timeframe to be saved in price_size_last_matrix for TickTrader

        """
        self.fileName = fileName
        self.versionNumber = '3.2.2'
        if isinstance(accountCode, list) or isinstance(accountCode, set) or isinstance(accountCode, tuple):
            self.accountCodeSet = set(accountCode)
            self.multiAccountFlag = True
            self.context = ContextClass(self.accountCodeSet)
        else:
            self.accountCode = accountCode
            self.multiAccountFlag = False
            self.context = ContextClass(self.accountCode)
        self.qData = None
        self.logLevel = logLevel
        self.showTimeZone = pytz.timezone(showTimeZone)
        self.maxSaveTime = maxSaveTime
        self.repBarFreq = repBarFreq
        self.waitForFeedbackInSeconds = waitForFeedbackInSeconds
        self.repeat = repeat

        # Prepare log
        todayDateStr = time.strftime("%Y-%m-%d")
        self.log = simpleLogger.SimpleLoggerClass(filename='TraderLog_' + todayDateStr + '.txt', logLevel=self.logLevel)

        # userLog is for the function of record (). User will use it for any reason.
        dateTimeStr = time.strftime("%Y_%m_%d_%H_%M_%S")
        self.userLog = simpleLogger.SimpleLoggerClass(filename='userLog_' + dateTimeStr + '.txt', logLevel='NOTSET',
                                                      addTime=False)

        self.initialize_quantopian = initialize_quantopian
        if not handle_data_quantopian:  # if user does not define handle_data, just ignore it
            self.handle_data_quantopian = (lambda x, y: None)
            self.runHandleDataFlag = False  # it is used in MarketManagerBase.py to decide if run handle_data
        else:
            self.handle_data_quantopian = handle_data_quantopian
            self.runHandleDataFlag = True

        if before_trading_start_quantopian is None:
            self.before_trading_start_quantopian = (lambda x, y: None)
        else:
            self.before_trading_start_quantopian = before_trading_start_quantopian

        # Set up IBridgePy hash configuration
        self.setHashConfig(read_in_hash_config('hash.conf'))
        if self.multiAccountFlag:
            self.setAuthedAcctCode('All')
        else:
            self.setAuthedAcctCode(self.accountCode)

        self.securityCheckWaiver = securityCheckWaiver

        self.rootFolderName = os.getcwd()

        # self.stockList = pd.read_csv(str(os.path.dirname(os.path.realpath(__file__)))+'/security_info.csv')
        self.stockList = pd.read_csv(os.path.join(self.rootFolderName, 'IBridgePy', 'security_info.csv'))

        self.runScheduledFunctionBeforeHandleData = runScheduledFunctionBeforeHandleData
        self.log.notset(__name__ + '::setup_trader')

    def initialize_Function(self):
        self.log.notset(__name__ + '::initialize_Function')
        self.log.info('IBridgePy version %s' % (self.versionNumber,))
        self.log.info('fileName = %s' % (self.fileName,))
        self.qData = QDataClass(self)
        self.request_data(ReqData.reqIds())
        self.request_data(ReqData.reqCurrentTime())
        if self.multiAccountFlag:
            self.request_data(ReqData.reqAccountSummary(),
                              ReqData.reqAllOpenOrders(),
                              ReqData.reqPositions())
        else:
            self.request_data(ReqData.reqAccountUpdates(True, self.accountCode),
                              ReqData.reqAllOpenOrders(),
                              ReqData.reqPositions())

        self.log.debug(__name__+'::initialize_Function::start to run customers init function')
        self.initialize_quantopian(self.context)  # function name was passed in.

        self.log.info('####    Starting to initialize trader    ####')
        if self.multiAccountFlag:
            for acctCode in self.accountCode:
                self.display_all(acctCode)
        else:
            self.display_all()
        self.log.info('####    Initialize trader COMPLETED    ####')

    def repeat_Function(self):
        self.log.debug(__name__ + '::repeat_Function: repBarFreq=' + str(self.repBarFreq))
        if self.runScheduledFunctionsToday:
            if self.runScheduledFunctionBeforeHandleData:
                self.check_schedules()

        self.handle_data_quantopian(self.context, self.qData)

        if self.runScheduledFunctionsToday:
            if not self.runScheduledFunctionBeforeHandleData:
                self.check_schedules()

    # supportive functions
    def check_schedules(self):
        self.log.debug(__name__ + '::check_schedules')
        timeNow = self.get_datetime(timezone=self.sysTimeZone)

        # ct is an instance of class TimeBasedRules in quantopian.py
        for ct in self.scheduledFunctionList:
            if special_match(ct.onHour, timeNow.hour, 'hourMinute') and \
                    special_match(ct.onMinute, timeNow.minute, 'hourMinute') and \
                    special_match(ct.onNthMonthDay, self.monthDay, 'monthWeek') and \
                    special_match(ct.onNthWeekDay, self.weekDay, 'monthWeek'):
                ct.func(self.context, self.qData)

    def getWantToEnd(self):
        """
        The function is used in Repeater in MarketManagerBase.py to know if repeat should stop
        :return: bool
        """
        return self.wantToEnd

    def setLocalMachineTime(self, datetime):
        """
        In live mode, it is real local time, dt.datetime.now()
        In backtest mode, it is the simulated time, passed in by repeater
        :param datetime: a passed in datetime
        :return: void
        """
        self.log.debug(__name__ + '::setLocalMachineTime: localMachineTime = %s' % (datetime,))
        self.localMachineTime = datetime

    def get_account_code(self):
        if self.multiAccountFlag:
            return self.accountCodeSet
        else:
            return self.accountCode

    def process_messages(self, dummyTime1, dummyTime2):
        """
        this function is created to fit the new RepeaterEngine because any functions to be scheduled must have two input
        times. It is easier to input two times to repeated function(?)
        :param dummyTime1:
        :return:
        """
        self.log.debug(__name__ + '::process_messages')
        self.processMessages()
