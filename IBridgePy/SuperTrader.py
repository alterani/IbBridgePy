# -*- coding: utf-8 -*-
"""
There is a risk of loss in stocks, futures, forex and options trading. Please
trade with capital you can afford to lose. Past performance is not necessarily
indicative of future results. Nothing in this computer program/code is intended
to be a recommendation to buy or sell any stocks or futures or options or any
tradable securities.
All information and computer programs provided is for education and
entertainment purpose only; accuracy and thoroughness cannot be guaranteed.
Readers/users are solely responsible for how they use the information and for
their results.

If you have any questions, please send email to IBridgePy@gmail.com
"""

from IBridgePy.IBAccountManager import IBAccountManager
from IBridgePy.quantopian import ReqData, ServerResponse
from IBridgePy.IbridgepyTools import print_contract
from IBridgePy import IBCpp
import pandas as pd
import datetime as dt


class SuperTrader(IBAccountManager):
    """
    Do NOT __init__, which will damage IBCpp's __init__
    """

    def tickOptionComputation(self, reqId, tickType, impliedVol, delta,
                              optPrice, pvDividend, gamma, vega, theta,
                              undPrice):
        self.log.debug(__name__ + '::tickOptionComputation:' + str(reqId))
        self.log.debug(__name__ + '::tickOptionComputation:\
        %s %s %s %s %s %s %s %s %s' % (
            tickType, impliedVol, delta, optPrice, pvDividend, gamma, vega, theta,
            undPrice))
        # security found is guaranteed to be in self.qData.data
        # no need to search it anymore.
        security = self._reqId_to_security(reqId)
        self.qData.data[security].impliedVol = impliedVol
        self.qData.data[security].delta = delta
        self.qData.data[security].gamma = gamma
        self.qData.data[security].vega = vega
        self.qData.data[security].theta = theta
        self.qData.data[security].undPrice = undPrice

    def tickGeneric(self, reqId, field, value):
        self.log.notset(__name__ + '::tickGeneric: reqId=%i field=%s value=%d' % (reqId, field, value))
        # exit()

    def contractDetails(self, reqId, contractDetails):
        """
        IB callback function to receive contract info
        """
        self.log.debug(__name__ + '::contractDetails:' + str(reqId))
        security = self._search_and_add_contract_to_qData(contractDetails.summary)

        # newRow=pd.DataFrame({'contractDetails':contractDetails},index=[0])
        newRow = pd.DataFrame({'right': contractDetails.summary.right,
                               'strike': float(contractDetails.summary.strike),
                               # 'expiry':dt.datetime.strptime(contractDetails.summary.expiry, '%Y%m%d'),
                               'expiry': contractDetails.summary.expiry,
                               # 'contractName':self._print_contract(contractDetails.summary),
                               'contractName': str(security),
                               'security': security,
                               'contract': contractDetails.summary,
                               'multiplier': contractDetails.summary.multiplier,
                               'contractDetails': contractDetails
                               }, index=[len(self.end_check_list_result[reqId])])

        self.end_check_list_result[reqId] = self.end_check_list_result[reqId].append(newRow)

    def bondContractDetails(self, reqId, contractDetails):
        """
        IB callback function to receive contract info
        """
        self.log.info(__name__ + '::bondContractDetails:' + str(reqId))
        # newRow=pd.DataFrame({'contractDetails':contractDetails},index=[0])
        newRow = pd.DataFrame({'right': contractDetails.summary.right,
                               'strike': float(contractDetails.summary.strike),
                               # 'expiry':dt.datetime.strptime(contractDetails.summary.expiry, '%Y%m%d'),
                               'expiry': contractDetails.summary.expiry,
                               'contractName': print_contract(contractDetails.summary),
                               'contract': contractDetails.summary,
                               'multiplier': contractDetails.summary.multiplier,
                               'contractDetails': contractDetails
                               }, index=[len(self.end_check_list_result[reqId])])
        self.end_check_list_result[reqId] = self.end_check_list_result[reqId].append(newRow)

    def contractDetailsEnd(self, reqId):
        """
        IB callback function to receive the ending flag of contract info
        """
        self.log.debug(__name__ + '::contractDetailsEnd:' + str(reqId))
        self.end_check_list.loc[reqId, 'status'] = 'Done'

    def tickSnapshotEnd(self, reqId):
        self.log.notset(__name__ + '::tickSnapshotEnd: ' + str(reqId))

    def updateAccountTime(self, tm):
        self.log.notset(__name__ + '::updateAccountTime:' + str(tm))

    def accountSummaryEnd(self, reqId):
        self.log.error(__name__ + '::accountSummaryEnd:CANNOT handle' + str(reqId))
        self.end()

    def updatePortfolio(self, contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL,
                        accountCode):
        self.log.notset(__name__ + '::updatePortfolio')

    def execDetails(self, reqId, contract, execution):
        self.log.notset(__name__ + '::execDetails: DO NOTHING reqId' + str(reqId))

    def commissionReport(self, commissionReport):
        self.log.notset(__name__ + '::commissionReport: DO NOTHING' + str(commissionReport))

    def realtimeBar(self, reqId, time, price_open, price_high, price_low, price_close, volume, wap, count):
        """
        call back function from IB C++ API
        return realTimebars for requested security every 5 seconds
        """
        self.log.debug(__name__ + '::realtimeBar: reqId=' + str(reqId) + ',' + str(dt.datetime.fromtimestamp(time)))
        if reqId in self.end_check_list.index:
            self.end_check_list.loc[reqId, 'status'] = 'Done'
        security = self._reqId_to_security(reqId)  # same thing in tickPrice
        self.update_DataClass(security, 'realTimeBars',
                              ls_info=[time, price_open, price_high, price_low, price_close, volume, wap, count])
        self.realtimeBarCount += 1
        self.realtimeBarTime = dt.datetime.fromtimestamp(time)

    def scannerData(self, reqId, rank, contractDetails, distance, benchmark, projection, legsStr):
        self.log.debug(__name__ + '::scannerData: reqId = %i, rank = %i, contractDetails.summary = %s, distance = %s,\
                benchmark = %s, project = %s, legsStr = %s'
                       % (reqId, rank, print_contract(contractDetails.summary), distance, benchmark,
                          projection, legsStr))
        security = self._search_and_add_contract_to_qData(contractDetails.summary)

        # If a security is unknown, remove it from the results
        if security is None:
            return

        newRow = pd.DataFrame({'rank': rank,
                               'contractDetails': contractDetails,
                               'security': security,
                               'distance': distance,
                               'benchmark': benchmark,
                               'projection': projection,
                               'legsStr': legsStr}, index=[len(self.end_check_list_result[reqId])])
        self.end_check_list_result[reqId] = self.end_check_list_result[reqId].append(newRow)

    def scannerDataEnd(self, reqId):
        self.log.debug(__name__ + '::scannerDataEnd:' + str(reqId))
        self.end_check_list.loc[reqId, 'status'] = 'Done'

    def scannerParameters(self, xml):
        self.log.debug(__name__ + '::scannerParameters:')
        reqId = self.end_check_list[self.end_check_list['reqType'] == 'reqScannerParameters']['reqId']
        self.end_check_list_result[int(reqId)] = xml
        self.end_check_list.loc[reqId, 'status'] = 'Done'

    #   IBridgePy functions  ##############
    def place_combination_orders(self, legList):
        """
        legList is a list of created orders that are created by create_order( )
        """
        finalOrderIdList = []
        for leg in legList:
            orderId = self.IBridgePyPlaceOrder(leg)
            finalOrderIdList.append(orderId)
        return finalOrderIdList

    def get_option_greeks(self, a_security_of_option, itemName=None):
        """
        itemName can be a string 'delta' or a list of string
        """
        ans = {}
        itemList = []
        if itemName is None:
            itemList = ['delta', 'gamma', 'vega', 'theta', 'impliedVol']
        else:
            if type(itemName) == str:
                itemList.append(itemName)
            elif type(itemName) == list:
                itemList = itemName
            else:
                self.log.error(__name__ + '::get_option_greeks: EXIT, cannot handle itemName=%s' % (itemName,))
                exit()
        for ct in itemList:
            if ct not in ['delta', 'gamma', 'vega', 'theta', 'impliedVol']:
                self.log.error(__name__ + '::get_option_greeks: EXIT, cannot handle itemName=%s' % (itemName,))
                exit()
            else:
                ans[ct] = getattr(self.qData.data[a_security_of_option], ct)
        return ans

    def get_contract_details(self, secType, symbol, field, currency='USD', exchange='', primaryExchange='', expiry='',
                             strike=0.0, right='', multiplier='', conId=0, localSymbol=''):
        security = self.superSymbol(secType=secType, symbol=symbol, currency=currency, exchange=exchange,
                                    primaryExchange=primaryExchange, expiry=expiry, strike=strike, right=right,
                                    multiplier=multiplier, conId=conId, localSymbol=localSymbol, addToQdata=False)

        self.request_data(ReqData.reqContractDetails(security))

        # Request contractDetails will not be mixed with other request so that only one result will be returned.
        if len(self.end_check_list_result) == 1:
            for ct in self.end_check_list_result:
                return self._extract_contractDetails(self.end_check_list_result[ct], field)

    def get_scanner_results(self, **kwargs):
        #        numberOfRows=-1, instrument='', locationCode='', scanCode='', abovePrice=0.0,
        #        belowPrice=0.0, aboveVolume=0, marketCapAbove=0.0, marketCapBelow=0.0, moodyRatingAbove='',
        #        moodyRatingBelow='', spRatingAbove='', spRatingBelow='', maturityDateAbove='', maturityDateBelow='',
        #        couponRateAbove=0.0, couponRateBelow=0.0, excludeConvertible=0, averageOptionVolumeAbove=0,
        #        scannerSettingPairs='', stockTypeFilter=''
        tagList = ['numberOfRows', 'instrument', 'locationCode', 'scanCode', 'abovePrice', 'belowPrice', 'aboveVolume',
                   'marketCapAbove',
                   'marketCapBelow', 'moodyRatingAbove', 'moodyRatingBelow', 'spRatingAbove', 'spRatingBelow',
                   'maturityDateAbove',
                   'maturityDateBelow', 'couponRateAbove', 'couponRateBelow', 'excludeConvertible',
                   'averageOptionVolumeAbove',
                   'scannerSettingPairs', 'stockTypeFilter']
        subscription = IBCpp.ScannerSubscription()
        for ct in kwargs:
            if ct in tagList:
                setattr(subscription, ct, kwargs[ct])
        self.request_data(ReqData.reqScannerSubscription(subscription))
        reqId = int(self.end_check_list[self.end_check_list['reqType'] == 'reqScannerSubscription']['reqId'])
        ans = ServerResponse(reqId, self.end_check_list_result[int(reqId)])
        return ans

    def get_scanner_parameters(self):
        self.request_data(ReqData.reqScannerParameters())
        for x in self.end_check_list_result:
            return self.end_check_list_result[x]

    def cancel_scanner_request(self, scannerRequestId):
        self.request_data(ReqData.cancelScannerSubscription(scannerRequestId))

    # supportive functions
    def _extract_contractDetails(self, df, field):
        ans = {}
        if type(field) == str:
            field = [field]
        for item in field:
            if item in ['conId', 'symbol', 'secType', 'LastTradeDateOrContractMonth', 'strike', 'right', 'multiplier',
                        'exchange', 'currency', 'localSymbol', 'primaryExchange', 'tradingClass', 'includeExpired',
                        'secIdType', 'secId', 'comboLegs', 'underComp', 'comboLegsDescrip']:

                if hasattr(df.iloc[0]['contractDetails'].summary, item):
                    ans[item] = getattr(df.iloc[0]['contractDetails'].summary, item)
                else:
                    ans[item] = 'not found'
            elif item in ['marketName', 'minTick', 'priceMagnifier', 'orderTypes', 'validExchanges', 'underConId',
                          'longName', 'contractMonth', 'industry', 'category', 'subcategory', 'timeZoneId',
                          'tradingHours', 'liquidHours', 'evRule', 'evMultiplier', 'mdSizeMultiplier', 'aggGroup',
                          'secIdList', 'underSymbol', 'underSecType', 'marketRuleIds', 'realExpirationDate', 'cusip',
                          'ratings', 'descAppend', 'bondType', 'couponType', 'callable', 'putable', 'coupon',
                          'convertible', 'maturity', 'issueDate', 'nextOptionDate', 'nextOptionType',
                          'nextOptionPartial',
                          'notes']:
                if hasattr(df.iloc[0]['contractDetails'], item):
                    ans[item] = getattr(df.iloc[0]['contractDetails'], item)
                else:
                    ans[item] = 'not found'
            elif item == 'summary':
                return df.loc[:, ['contractName', 'expiry', 'strike', 'right', 'multiplier', 'contract', 'security']]
            else:
                self.log.error(__name__ + '::_extract_contractDetails: Invalid item = %s' % (item,))
                exit()
        return ans
