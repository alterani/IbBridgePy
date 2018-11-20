# -*- coding: utf-8 -*-
"""
There is a risk of loss when trading stocks, futures, forex, options and other
financial instruments. Please trade with capital you can afford to
lose. Past performance is not necessarily indicative of future results.
Nothing in this computer program/code is intended to be a recommendation, explicitly or implicitly, and/or
solicitation to buy or sell any stocks or futures or options or any securities/financial instruments.
All information and computer programs provided here is for education and
entertainment purpose only; accuracy and thoroughness cannot be guaranteed.
Readers/users are solely responsible for how to use these information and
are solely responsible any consequences of using these information.

If you have any questions, please send email to IBridgePy@gmail.com
All rights reserved.
"""

from IBridgePy.quantopian import PositionClass, MarketOrder, IbridgePyOrder, ReqData, \
    LimitOrder, StopOrder, from_contract_to_security
import datetime as dt
import time
from IBridgePy.SuperTrader import SuperTrader
from IBridgePy.IbridgepyTools import transform_action, print_contract
from sys import exit
import pandas as pd
import numpy as np
import math
from IBridgePy.constants import OrderStatus, FollowUpRequest


class SingleTrader(SuperTrader):
    # IB callback functions
    def updateAccountValue(self, key, value, currency, accountCode):
        """
        IB callback function
        update account values such as cash, PNL, etc
        """
        self.log.notset(__name__ + '::updateAccountValue: key=' + key
                       + ' value=' + str(value)
                       + ' currency=' + currency
                       + ' accountCode=' + accountCode)
        if not self.validateAccountCode(accountCode):
            return

        if key == 'TotalCashValue':
            self.PORTFOLIO.cash = float(value)
            # print (__name__+'::updateAccountValue: cash=',self.PORTFOLIO.cash)
        elif key == 'UnrealizedPnL':
            self.PORTFOLIO.pnl = float(value)
        elif key == 'NetLiquidation':
            self.PORTFOLIO.portfolio_value = float(value)
            # print (__name__+'::updateAccountValue: portfolio=',self.PORTFOLIO.portfolio_value)
        elif key == 'GrossPositionValue':
            self.PORTFOLIO.positions_value = float(value)
            # print (__name__+'::updateAccountValue: positions=',self.PORTFOLIO.positions_value)
        else:
            pass

    def accountDownloadEnd(self, accountCode):
        """
        IB callback function
        """
        self.log.debug(__name__ + '::accountDownloadEnd: ' + str(accountCode))
        reqId = self.end_check_list[self.end_check_list['reqType'] == 'reqAccountUpdates']['reqId']
        self.end_check_list.loc[reqId, 'status'] = 'Done'

    def accountSummary(self, reqId, accountCode, tag, value, currency):
        self.log.notset(__name__ + '::accountSummary:' + str(reqId) + str(accountCode) + str(tag) +
                        str(value) + str(currency))
        if not self.validateAccountCode(accountCode):
            return

        if tag == 'TotalCashValue':
            self.PORTFOLIO.cash = float(value)
            self.log.debug(__name__ + '::accountSummary: cash change =%s' % (str(self.PORTFOLIO.cash),))
        elif tag == 'GrossPositionValue':
            self.PORTFOLIO.positions_value = float(value)
        elif tag == 'NetLiquidation':
            self.PORTFOLIO.portfolio_value = float(value)

    def accountSummaryEnd(self, reqId):
        self.log.debug(__name__ + '::accountSummaryEnd: ' + str(reqId))
        reqId = self.end_check_list[self.end_check_list['reqType'] == 'reqAccountSummary']['reqId']
        self.end_check_list.loc[reqId, 'status'] = 'Done'

    def position(self, accountCode, contract, amount, price):
        """
        call back function of IB C++ API which updates the position of a contract
        of a account
        """
        self.log.debug(
            __name__ + '::position: %s %s %s %s' % (accountCode, print_contract(contract), str(amount), str(price)))
        if not self.validateAccountCode(accountCode):
            return

        security = self._search_and_add_contract_to_qData(contract)

        # if security is not in positions,  add it in it
        if (not self.PORTFOLIO.positions) or (security not in self.PORTFOLIO.positions):
            self.PORTFOLIO.positions[security] = PositionClass()

        # update position info. Remove it from positions if amount = 0
        if amount:
            self.PORTFOLIO.positions[security].amount = amount
            self.PORTFOLIO.positions[security].cost_basis = price
            self.PORTFOLIO.positions[security].accountCode = accountCode
        else:
            del self.PORTFOLIO.positions[security]

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId,
                    whyHeld):
        """
        call back function of IB C++ API which update status or certain order
        indicated by orderId
        Same orderId may be called back multiple times with status of 'Filled'
        orderStatus is always called back after openOrder
        """
        self.log.debug(__name__ + '::orderStatus: ' + str(orderId) + ", " + str(status) + ", " + str(filled)
                       + ", " + str(remaining) + ", " + str(avgFillPrice))
        if status == OrderStatus.CANCELLED:
            reqId = self.end_check_list[self.end_check_list['reqType'] == 'cancelOrder']['reqId']
            self.end_check_list.loc[reqId, 'status'] = 'Done'
        elif status in [OrderStatus.PRESUBMITTED, OrderStatus.SUBMITTED]:
            reqId = self.end_check_list[self.end_check_list['reqType'] == 'placeOrder']['reqId']
            self.end_check_list.loc[reqId, 'status'] = 'Done'

        accountCode = self.orderId_to_accountCode(orderId)
        if self.validateAccountCode(accountCode):
            self.PORTFOLIO.orderStatusBook[orderId].filled = filled
            self.PORTFOLIO.orderStatusBook[orderId].remaining = remaining
            self.PORTFOLIO.orderStatusBook[orderId].status = status
            self.PORTFOLIO.orderStatusBook[orderId].avgFillPrice = avgFillPrice
            if (self.PORTFOLIO.orderStatusBook[orderId].parentOrderId
                    is not None and status == 'Filled'):
                if self.PORTFOLIO.orderStatusBook[orderId].stop is not None:
                    self.PORTFOLIO.orderStatusBook[
                        self.PORTFOLIO.orderStatusBook[orderId].parentOrderId].stop_reached = True
                    self.log.info(__name__ + "::orderStatus " + "stop executed: " +
                                  self.PORTFOLIO.orderStatusBook[orderId].contract.symbol)
                if self.PORTFOLIO.orderStatusBook[orderId].limit is not None:
                    self.PORTFOLIO.orderStatusBook[
                        self.PORTFOLIO.orderStatusBook[orderId].parentOrderId].limit_reached = True
                    self.log.info(__name__ + "::orderStatus " + "limit executed: " +
                                  self.PORTFOLIO.orderStatusBook[orderId].contract.symbol)

    def openOrder(self, orderId, contract, order, orderState):
        """
        call back function of IB C++ API which updates the open orders indicated
        by orderId
        """
        self.log.debug(__name__ + '::openOrder: orderId = %i contract = %s order.action = %s order.totalQuantity = %s'
                       % (orderId, print_contract(contract), str(order.action), str(order.totalQuantity)))

        if not self.validateAccountCode(order.account):
            return

        if orderId in self.PORTFOLIO.orderStatusBook:
            self.PORTFOLIO.orderStatusBook[orderId].orderstate = orderState
            self.PORTFOLIO.orderStatusBook[orderId].status = orderState.status
        else:
            self.log.debug(__name__ + '::openOrder: Add %s to orderStatusBook' % (orderId,))
            self._search_and_add_contract_to_qData(contract)
            self.PORTFOLIO.orderStatusBook[orderId] = \
                IbridgePyOrder(orderId=orderId,
                               created=self.get_datetime(),
                               stop=(lambda x: x if x < 100000 else None)(order.auxPrice),
                               limit=(lambda x: x if x < 100000 else None)(order.lmtPrice),
                               amount=order.totalQuantity,
                               commission=(lambda x: x if x < 100000 else None)(orderState.commission),
                               status=orderState.status,
                               contract=contract,
                               order=order,
                               orderstate=orderState)

    def execDetails(self, reqId, contract, execution):
        self.log.debug(__name__ + '::execDetails: reqId= %i' % (int(reqId),) + print_contract(contract))
        self.log.debug(__name__ + '::execDetails: %s %s %s %s %s %s'
                       % (str(execution.side), str(execution.shares), str(execution.price),
                          str(execution.orderRef), str(execution.orderId), str(execution.clientId)))

        if not self.validateAccountCode(execution.acctNumber):
            return

        cashChange = execution.shares * float(execution.price)
        if execution.side == 'BOT':
            self.PORTFOLIO.cash -= cashChange
        elif execution.side == 'SLD':
            self.PORTFOLIO.cash += cashChange
        else:
            self.log.error(__name__ + '::execDetails: EXIT, cannot handle execution.side=' + execution.side)
            exit()
        self.log.debug(__name__ + '::execDetails: cash= %f' % (float(self.PORTFOLIO.cash),))
        if execution.orderRef not in self.PORTFOLIO.performanceTracking:
            self.PORTFOLIO.performanceTracking[execution.orderRef] = \
                pd.DataFrame({'security': 'NA',
                              'action': 'NA',
                              'quantity': 0,
                              'avgFillPrice': 0,
                              'virtualStrategyBalance': 0},
                             index=[self.get_datetime()])

        # Do not add the security to self.qData.data{} because STK,,SMART,SPY,USD may be executed at any exchange
        # need more understanding gof tracking_performance
        # TODO:
        security = from_contract_to_security(contract)
        action = str(execution.side)
        quantity = float(execution.shares)
        avgFillPrice = float(execution.price)
        virtualStrategyBalance = self._track_performance(execution.orderRef,
                                                         security,
                                                         action,
                                                         quantity,
                                                         avgFillPrice,
                                                         execution.acctNumber)
        # print self.PORTFOLIO.virtualHoldings
        # prev=self.PORTFOLIO.performanceTracking[execution.orderRef].ix[-1, 'virtualStrategyBalance']
        # print prev,virtualStrategyBalance
        if virtualStrategyBalance is None:
            virtualStrategyBalance = np.nan
        newRow = pd.DataFrame({'security': str(security),
                               'action': action,
                               'quantity': quantity,
                               'avgFillPrice': avgFillPrice,
                               'virtualStrategyBalance': virtualStrategyBalance},
                              index=[self.get_datetime()])
        self.PORTFOLIO.performanceTracking[execution.orderRef] = \
            self.PORTFOLIO.performanceTracking[execution.orderRef].append(newRow)
        # print self.PORTFOLIO.performanceTracking[execution.orderRef]

    ########## IBridgePy action functions
    def order(self, security, amount, style=MarketOrder(), orderRef='',
              accountCode='default', outsideRth=False, hidden=False, tradeAtExchange=None):
        self.log.debug(__name__ + '::order:' + str(security) + ' ' + str(amount))
        if amount > 0:
            action = 'BUY'
        elif amount < 0:
            action = 'SELL'
            amount = -amount
        else:
            self.log.debug(__name__ + '::order: No order has been placed')
            return 0
        tmp = self.create_order(action, amount, security, style, orderRef=orderRef, outsideRth=outsideRth,
                                hidden=hidden, tradeAtExchange=tradeAtExchange)
        if tmp is not None:
            return self.IBridgePyPlaceOrder(tmp, accountCode=accountCode)
        else:
            self.log.error(__name__ + '::order: EXIT wrong security instance ' + str(security))
            exit()

    def order_target(self, security, amount, style=MarketOrder(), orderRef='',
                     accountCode='default'):
        self.log.notset(__name__ + '::order_target')
        hold = self.count_positions(security, accountCode=accountCode)
        if amount != hold:
            # amount - hold is correct, confirmed
            return self.order(security, amount=int(amount - hold), style=style,
                              orderRef=orderRef, accountCode=accountCode)
        else:
            self.log.debug(__name__ + '::order_target: %s No action is needed' % (str(security),))
            return 0

    def order_value(self, security, value, style=MarketOrder(), orderRef='',
                    accountCode='default'):
        self.log.notset(__name__ + '::order_value')
        targetShare = int(value / self.show_real_time_price(security, 'ask_price'))
        return self.order(security, amount=targetShare, style=style,
                          orderRef=orderRef, accountCode=accountCode)

    def order_percent(self, security, percent, style=MarketOrder(), orderRef='',
                      accountCode='default'):
        self.log.notset(__name__ + '::order_percent')
        if percent > 1.0 or percent < -1.0:
            self.log.error(__name__ + '::order_percent: EXIT, percent=%s [-1.0, 1.0]' % (str(percent),))
            exit()
        targetShare = int(self.PORTFOLIO.portfolio_value / self.show_real_time_price(security, 'ask_price'))
        return self.order(security, amount=int(targetShare * percent), style=style,
                          orderRef=orderRef, accountCode=accountCode)

    def order_target_percent(self, security, percent, style=MarketOrder(),
                             orderRef='', accountCode='default'):
        self.log.notset(__name__ + '::order_percent')
        if percent > 1.0 or percent < -1.0:
            self.log.error(__name__ + '::order_target_percent: EXIT, percent=%s [-1.0, 1.0]' % (str(percent),))
            exit()
        a = self.PORTFOLIO.portfolio_value
        b = self.show_real_time_price(security, 'ask_price')
        if math.isnan(b):
            self.log.error(__name__ + '::order_target_percent: EXIT, real_time_price is NaN')
            exit()
        if b <= 0.0:
            self.log.error(__name__ + '::order_target_percent: EXIT, real_time_price <= 0.0')
            exit()
        targetShare = int(a * percent / b)
        return self.order_target(security, amount=targetShare, style=style,
                                 orderRef=orderRef, accountCode=accountCode)

    def order_target_value(self, security, value, style=MarketOrder(),
                           orderRef='', accountCode='default'):
        self.log.notset(__name__ + '::order_target_value')
        targetShare = int(value / self.show_real_time_price(security, 'ask_price'))
        return self.order_target(security, amount=targetShare, style=style,
                                 orderRef=orderRef, accountCode=accountCode)

    def order_target_II(self, security, amount, style=MarketOrder(), accountCode='default'):
        self.log.notset(__name__ + '::order_target_II')
        hold = self.count_positions(security, accountCode=accountCode)
        if (hold >= 0 and amount > 0) or (hold <= 0 and amount < 0):
            orderID = self.order(security, amount=amount - hold, style=style, accountCode=accountCode)
            if self.order_status_monitor(orderID, 'Filled'):
                return orderID
        if (hold > 0 > amount) or (hold < 0 < amount):
            orderID = self.order_target(security, 0, accountCode=accountCode)
            if self.order_status_monitor(orderID, 'Filled'):
                orderID = self.order(security, amount, accountCode=accountCode)
                if self.order_status_monitor(orderID, 'Filled'):
                    return orderID
                else:
                    self.log.debug(
                        __name__ + '::order_target_II:orderID=%s was not processed as expected. EXIT!!!' % (orderID,))
                    return 0
            else:
                self.log.debug(
                    __name__ + '::order_target_II:orderID=%s was not processed as expected. EXIT!!!' % (orderID,))
                return 0
        if hold == amount:
            self.log.debug(__name__ + '::order_target_II: %s No action is needed' % (str(security),))
            return 0
        else:
            self.log.debug(__name__ + '::order_target_II: hold=' + str(hold))
            self.log.debug(__name__ + '::order_target_II: amount=' + str(amount))
            self.log.debug(__name__ + '::order_target_II: Need debug EXIT')
            exit()

    def modify_order(self, orderId, newQuantity=None, newLimitPrice=None, newStopPrice=None, newTif=None,
                     newOrderRef=None):
        self.log.debug(__name__ + '::modify_order: orderId = %s' % (orderId,))
        if self.PORTFOLIO.orderStatusBook[orderId].status in [OrderStatus.PRESUBMITTED, OrderStatus.SUBMITTED]:
            an_order = self.PORTFOLIO.orderStatusBook[orderId]
            an_order.status = OrderStatus.PRESUBMITTED
            if newQuantity is not None:
                # amount is the same number as order.totalQuantity. Keep it because Quantopian has it.
                an_order.amount = newQuantity
                an_order.order.totalQuantity = newQuantity
            if newLimitPrice is not None:
                an_order.limit = newLimitPrice
                an_order.order.lmtPrice = newLimitPrice
            if newStopPrice is not None:
                an_order.stop = newStopPrice
                an_order.order.auxPrice = newStopPrice
            if newTif is not None:
                an_order.order.tif = newTif
            if newOrderRef is not None:
                an_order.order.orderRef = newOrderRef
            self.request_data(ReqData.placeOrder(orderId, an_order.contract, an_order.order, FollowUpRequest.DO_NOT_FOLLOW_UP))
        else:
            self.log.error(__name__ + '::modify_order: Cannot modify order. orderId = %s' % (orderId,))
            exit()

    def cancel_all_orders(self, accountCode='default'):
        self.log.info(__name__ + '::cancel_all_orders')
        if not self.validateAccountCode(accountCode):
            return

        for orderId in self.PORTFOLIO.orderStatusBook:
            if self.PORTFOLIO.orderStatusBook[orderId].status not in ['Filled', 'Cancelled', 'Inactive']:
                self.cancel_order(orderId)

    def display_positions(self, accountCode='default'):
        self.log.notset(__name__ + '::display_positions')
        if not self.displayFlag:
            return

        if not self.validateAccountCode(accountCode):
            return

        if self.hold_any_position(accountCode):
            self.log.info('##    POSITIONS %s   ##' % (self.adjust_accountCode(accountCode),))
            self.log.info('Symbol Amount Cost_basis Latest_profit')

            for ct in self.PORTFOLIO.positions:
                if self.PORTFOLIO.positions[ct].amount != 0:
                    a = self.qData.data[self._search_and_add_security_to_Qdata(ct)].last_traded
                    b = self.PORTFOLIO.positions[ct].cost_basis
                    c = self.PORTFOLIO.positions[ct].amount
                    # self.show_real_time_price(ct, 'price') if market is not open,
                    # the code will terminate and the user will complain
                    if a is not None and a != -1:
                        self.log.info(str(ct) + ' ' + str(c) + ' ' + str(b) + ' ' + str((a - b) * c))
                    else:
                        self.log.info(str(ct) + ' ' + str(c) + ' ' + str(b) + ' NA')

            self.log.info('##    END    ##')
        else:
            self.log.info('##    NO ANY POSITION    ##')

    def display_orderStatusBook(self, accountCode='default'):
        self.log.notset(__name__ + '::display_orderStatusBook')
        if not self.displayFlag:
            return

        # show orderStatusBook
        if not self.validateAccountCode(accountCode):
            return

        if len(self.PORTFOLIO.orderStatusBook) >= 1:
            self.log.info('##    Order Status %s   ##' % (self.adjust_accountCode(accountCode),))
            for orderId in self.PORTFOLIO.orderStatusBook:
                self.log.info(str(self.PORTFOLIO.orderStatusBook[orderId]))
            self.log.info('##    END    ##')
        else:
            self.log.info('##    NO any order    ##')

    def display_account_info(self, accountCode='default'):
        """
        display account info such as position values in format ways
        """
        self.log.notset(__name__ + '::display_account_info')
        if not self.displayFlag:
            return

        if not self.validateAccountCode(accountCode):
            return

        self.log.info('##    ACCOUNT Balance  %s  ##' % (self.adjust_accountCode(accountCode),))
        self.log.info('CASH=' + str(self.PORTFOLIO.cash))
        # self.log.info('pnl=' + str(self.PORTFOLIO.pnl))
        self.log.info('portfolio_value=' + str(self.PORTFOLIO.portfolio_value))
        self.log.info('positions_value=' + str(self.PORTFOLIO.positions_value))
        # self.log.info('returns=' + str(self.PORTFOLIO.returns))
        # self.log.info('starting_cash=' + str(self.PORTFOLIO.starting_cash))
        # self.log.info('start_date=' + str(self.PORTFOLIO.start_date))
        if self.PORTFOLIO.cash + self.PORTFOLIO.portfolio_value + self.PORTFOLIO.positions_value <= 0.0:
            self.log.error(__name__ + '::display_account_info: EXIT, Wrong input accountCode = %s'
                           % (self.accountCode,))
            self.accountCodeCallBackSet.discard(self.accountCode)
            self.accountCodeCallBackSet.discard('default')
            if len(self.accountCodeCallBackSet):
                self.log.error(__name__ + '::display_account_info: Possible accountCode = %s'
                               % (' '.join(self.accountCodeCallBackSet)))
            exit()

    def display_all(self, accountCode='default'):
        if not self.displayFlag:
            return

        if not self.validateAccountCode(accountCode):
            self.log.error(__name__ + '::display_all: Unexpected accountCode = %s' % (accountCode,))
            return

        accountCode = self.adjust_accountCode(accountCode)
        self.display_account_info(accountCode)
        self.display_positions(accountCode)
        self.display_orderStatusBook(accountCode)

    def get_order_status(self, orderId):
        """
        orderId is unique for any orders in any session
        """
        accountCode = self.orderId_to_accountCode(orderId)
        if not self.validateAccountCode(accountCode):
            return

        if orderId in self.PORTFOLIO.orderStatusBook:
            return self.PORTFOLIO.orderStatusBook[orderId].status
        else:
            return None

    def order_status_monitor(self, orderId, target_status, waitingTimeInSeconds=30):
        self.log.notset(__name__ + '::order_status_monitor: orderId = %s' % (orderId,))

        accountCode = self.orderId_to_accountCode(orderId)
        if orderId == -1:
            self.log.error(__name__ + '::order_status_monitor: EXIT, orderId=-1')
            exit()
        elif orderId == 0:
            return True
        else:
            timer = dt.datetime.now()
            exit_flag = True
            while exit_flag:
                time.sleep(0.1)
                self.processMessages()

                # self.validateAccountCode MUST stay here because self.processMessage may change self.PORTFOLIO
                if not self.validateAccountCode(accountCode):
                    self.log.error(__name__ + '::order_status_monitor: EXIT, untracked orderId = %s' % (orderId,))
                    exit()

                if (dt.datetime.now() - timer).total_seconds() <= waitingTimeInSeconds:

                    tmp_status = self.PORTFOLIO.orderStatusBook[orderId].status
                    if type(target_status) == str:
                        if tmp_status == target_status:
                            self.log.debug(__name__ + '::order_status_monitor: %s, %s ' % (
                                target_status, str(self.PORTFOLIO.orderStatusBook[orderId])))
                            return True
                    else:
                        if tmp_status in target_status:
                            self.log.debug(__name__ + '::order_status_monitor: %s, %s ' % (
                                tmp_status, str(self.PORTFOLIO.orderStatusBook[orderId])))
                            return True

                else:
                    self.log.error(__name__ + '::order_status_monitor: EXIT, waiting time is too long, >%i' % (
                        waitingTimeInSeconds,))
                    status = self.PORTFOLIO.orderStatusBook[orderId].status
                    security = self._search_and_add_contract_to_qData(self.PORTFOLIO.orderStatusBook[orderId].contract)
                    self.log.error(__name__ + '::order_status_monitor: EXIT, orderId=%i, status=%s, %s'
                                   % (orderId, status, str(security)))
                    exit()

    def close_all_positions(self, orderStatusMonitor=True, accountCode='default'):
        self.log.debug(__name__ + '::close_all_positions:')
        if not self.validateAccountCode(accountCode):
            return

        orderIdList = []
        for security in self.PORTFOLIO.positions.keys():
            orderId = self.order_target(security, 0, accountCode=accountCode)
            orderIdList.append(orderId)
        if orderStatusMonitor:
            for orderId in orderIdList:
                self.order_status_monitor(orderId, 'Filled')

    def close_all_positions_except(self, a_security, accountCode='default'):
        self.log.debug(__name__ + '::close_all_positions_except:' + str(a_security))
        if not self.validateAccountCode(accountCode):
            return

        orderIdList = []
        for security in self.PORTFOLIO.positions.keys():
            if self._same_security(a_security, security):
                pass
            else:
                orderId = self.order_target(security, 0, accountCode=accountCode)
                orderIdList.append(orderId)
        for orderId in orderIdList:
            self.order_status_monitor(orderId, 'Filled')

    def show_account_info(self, infoName, accountCode='default'):
        if not self.validateAccountCode(accountCode):
            return

        if hasattr(self.PORTFOLIO, infoName):
            return getattr(self.PORTFOLIO, infoName)
        else:
            self.log.error(
                __name__ + '::show_account_info: ERROR, context.portfolio of accountCode=%s does not have attr=%s' % (
                    self.accountCode, infoName))
            exit()

    def count_open_orders(self, security='All', accountCode='default'):
        self.log.debug(__name__ + '::count_open_orders')
        if not self.validateAccountCode(accountCode):
            return

        count = 0
        for orderId in self.PORTFOLIO.orderStatusBook:
            if self.PORTFOLIO.orderStatusBook[orderId].status not in ['Filled', 'Cancelled', 'Inactive']:
                if security == 'All':
                    count += self.PORTFOLIO.orderStatusBook[orderId].amount
                else:
                    tp = self.PORTFOLIO.orderStatusBook[orderId].contract
                    tp = self._search_and_add_contract_to_qData(tp)
                    if self._same_security(tp, security):
                        count += self.PORTFOLIO.orderStatusBook[orderId].amount
        return count

    def count_positions(self, security, accountCode='default'):
        self.log.debug(__name__ + '::count_positions')
        if not self.validateAccountCode(accountCode):
            return

        for sec in self.PORTFOLIO.positions:
            if self._same_security(sec, security):
                return self.PORTFOLIO.positions[sec].amount
        return 0

    def hold_any_position(self, accountCode='default'):
        self.log.debug(__name__ + '::hold_any_position')
        if not self.validateAccountCode(accountCode):
            return False

        for ct in self.PORTFOLIO.positions:
            if self.PORTFOLIO.positions[ct].amount != 0:
                self.log.debug(__name__ + '::hold_any_position: %s' % (ct,))
                return True
        return False

    def calculate_profit(self, a_security, accountCode='default'):
        self.log.notset(__name__ + '::calculate_profit:' + str(a_security))
        if not self.validateAccountCode(accountCode):
            return

        tp = self._search_and_add_security_to_Qdata(a_security)
        a = self.show_real_time_price(tp, 'ask_price')
        b = self.PORTFOLIO.positions[tp].cost_basis
        c = self.PORTFOLIO.positions[tp].amount
        if a is not None and a != -1:
            return (a - b) * c
        else:
            return None

    def get_order(self, orderId, accountCode='default'):
        self.log.debug(__name__ + '::get_order: orderId = %s' % (orderId,))
        if not self.validateAccountCode(accountCode):
            return

        if isinstance(orderId, int):
            if orderId in self.PORTFOLIO.orderStatusBook:
                return self.PORTFOLIO.orderStatusBook[orderId]
            else:
                self.log.error(__name__ + '::get_order: EXIT, Not found in orderStatusBook orderId=%s' % (str(orderId),))
        else:
            self.log.error(__name__ + '::get_order: EXIT, invalid orderId=%s type = %s' % (str(orderId),str(type(orderId))))
            exit()

    def get_open_orders(self, security=None, accountCode='default'):
        self.log.debug(__name__ + '::get_open_orders')
        if not self.validateAccountCode(accountCode):
            return

        if security is None:
            ans = {}
            for orderId in self.PORTFOLIO.orderStatusBook:
                if self.PORTFOLIO.orderStatusBook[orderId].status in ['PreSubmitted', 'Submitted']:
                    tp = self.PORTFOLIO.orderStatusBook[orderId].contract
                    security = self._search_and_add_contract_to_qData(tp)
                    if security not in ans:
                        ans[security] = [self.PORTFOLIO.orderStatusBook[orderId]]
                    else:
                        ans[security].append(self.PORTFOLIO.orderStatusBook[orderId])
            return ans
        else:
            ans = []
            for orderId in self.PORTFOLIO.orderStatusBook:
                if self.PORTFOLIO.orderStatusBook[orderId].status in ['PreSubmitted', 'Submitted']:
                    tp = self.PORTFOLIO.orderStatusBook[orderId].contract
                    adj_security = self._search_and_add_contract_to_qData(tp)
                    if self._same_security(security, adj_security):
                        ans.append(self.PORTFOLIO.orderStatusBook[orderId])
            return ans

    # IBridgePy supportive functions
    def place_order_with_stoploss(self, security, amount, stopLossPrice, style=MarketOrder()):
        """
        return orderId of the parentOrder only
        """
        action, oppositeAction, amount = transform_action(amount)
        parentOrder = self.create_order(action, amount, security, style, ocaGroup=str(self.nextId))
        slOrder = self.create_order(oppositeAction, amount, security, StopOrder(stopLossPrice),
                                    ocaGroup=str(self.nextId))
        # IB recommends this way to place takeProfitOrder and stopLossOrder
        # with main order.
        parentOrder.order.transmit = False
        slOrder.order.parentId = self.nextId
        slOrder.order.transmit = True  # only transmit slOrder to avoid inadvertent actions
        orderId = self.IBridgePyPlaceOrder(parentOrder, followUpWaiver=FollowUpRequest.DO_NOT_FOLLOW_UP)
        slOrderId = self.IBridgePyPlaceOrder(slOrder)
        return orderId, slOrderId

    def place_order_with_takeprofit(self, security, amount, takeProfitPrice, style=MarketOrder()):
        """
        return orderId of the parentOrder only
        """
        action, oppositeAction, amount = transform_action(amount)
        parentOrder = self.create_order(action, amount, security, style, ocaGroup=str(self.nextId))
        tpOrder = self.create_order(oppositeAction, amount, security, LimitOrder(takeProfitPrice),
                                    ocaGroup=str(self.nextId))
        # IB recommends this way to place takeProfitOrder and stopLossOrder
        # with main order.
        parentOrder.order.transmit = False
        tpOrder.order.parentId = self.nextId
        tpOrder.order.transmit = True
        orderId = self.IBridgePyPlaceOrder(parentOrder, followUpWaiver=FollowUpRequest.DO_NOT_FOLLOW_UP)
        tpOrderId = self.IBridgePyPlaceOrder(tpOrder)
        return orderId, tpOrderId

    def place_order_with_stoploss_takeprofit(self, security, amount, stopLossPrice, takeProfitPrice,
                                             style=MarketOrder()):
        """
        return orderId of the parentOrder only
        """
        action, oppositeAction, amount = transform_action(amount)
        parentOrder = self.create_order(action, amount, security, style, ocaGroup=str(self.nextId))
        tpOrder = self.create_order(oppositeAction, amount, security, LimitOrder(takeProfitPrice),
                                    ocaGroup=str(self.nextId))
        slOrder = self.create_order(oppositeAction, amount, security, StopOrder(stopLossPrice),
                                    ocaGroup=str(self.nextId))
        # IB recommends this way to place takeProfitOrder and stopLossOrder
        # with main order.
        parentOrder.order.transmit = False
        tpOrder.order.parentId = self.nextId
        slOrder.order.parentId = self.nextId
        tpOrder.order.transmit = False
        slOrder.order.transmit = True  # only transmit slOrder to avoid inadvertent actions
        orderId = self.IBridgePyPlaceOrder(parentOrder, followUpWaiver=FollowUpRequest.DO_NOT_FOLLOW_UP)
        tpOrderId = self.IBridgePyPlaceOrder(tpOrder, followUpWaiver=FollowUpRequest.DO_NOT_FOLLOW_UP)
        slOrderId = self.IBridgePyPlaceOrder(slOrder)
        return orderId, slOrderId, tpOrderId

    def build_security_in_positions(self, a_security, accountCode='default'):
        self.log.notset(__name__ + '::build_security_in_positions')
        if not self.validateAccountCode(accountCode):
            return

        if a_security not in self.PORTFOLIO.positions:
            self.PORTFOLIO.positions[a_security] = PositionClass()
            self.log.notset(__name__ + '::_build_security_in_positions: Empty,\
            add a new position ' + str(a_security))

    def check_if_any_unfilled_orders(self, verbose=False, accountCode='default'):
        self.log.notset(__name__ + '::check_if_any_unfilled_orders')
        if not self.validateAccountCode(accountCode):
            return

        flag = False
        for orderId in self.PORTFOLIO.orderStatusBook:
            if self.PORTFOLIO.orderStatusBook[orderId].status != 'Filled':
                flag = True
        if flag:
            if verbose:
                self.log.info(__name__ + '::check_if_any_unfilled_orders: unfilled orderst are:')
                self.display_orderStatusBook(accountCode)
        return flag

    def IBridgePyPlaceOrder(self, an_order, accountCode='default', followUpWaiver=False):
        self.log.debug(__name__ + '::IBridgePyPlaceOrder')
        if not self.validateAccountCode(accountCode):
            return

        an_order.order.account = self.adjust_accountCode(accountCode)
        an_order.orderId = self.nextId
        an_order.created = self.get_datetime()
        an_order.stop = an_order.order.auxPrice
        an_order.limit = an_order.order.lmtPrice
        an_order.amount = an_order.order.totalQuantity
        an_order.status = 'PreSubmitted'

        # in the test_run mode, self.nextId may change after self.placeOrder, so, record it at first place
        orderId = self.nextId
        self.nextId = self.nextId + 1
        self.PORTFOLIO.orderStatusBook[orderId] = an_order
        self.request_data(ReqData.placeOrder(orderId, an_order.contract, an_order.order, followUpWaiver))
        return orderId

    def get_performance(self, orderRef, accountCode='default'):
        self.log.debug(__name__ + '::get_performance: %s %s' % (orderRef, accountCode))
        if not self.validateAccountCode(accountCode):
            return

        if orderRef in self.PORTFOLIO.performanceTracking:
            a = self.PORTFOLIO.performanceTracking[orderRef]
            c = a[a['virtualStrategyBalance'] <= 0x7FFFFFFF]
            return c['virtualStrategyBalance']
        else:
            return []

    def _track_performance(self, orderRef, security, action, quantity, avgFillPrice, accountCode='default'):
        security = str(security)
        self.log.debug(__name__ + '::_track_performance: %s %s' % (orderRef, accountCode))

        if not self.validateAccountCode(accountCode):
            return

        if orderRef not in self.PORTFOLIO.virtualHoldings:
            self.PORTFOLIO.virtualHoldings[orderRef] = {}
        if security not in self.PORTFOLIO.virtualHoldings[orderRef]:
            self.PORTFOLIO.virtualHoldings[orderRef][security] = {'action': action,
                                                                  'quantity': quantity,
                                                                  'avgFillPrice': avgFillPrice}
            return None

        q = self.PORTFOLIO.virtualHoldings[orderRef][security]['quantity']
        p = self.PORTFOLIO.virtualHoldings[orderRef][security]['avgFillPrice']
        if action == self.PORTFOLIO.virtualHoldings[orderRef][security]['action']:
            self.PORTFOLIO.virtualHoldings[orderRef][security]['avgFilePrice'] = \
                (q * p + quantity * avgFillPrice) / (q + quantity)
            self.PORTFOLIO.virtualHoldings[orderRef][security]['quantity'] += quantity
            return None
        else:
            if q > quantity:
                self.PORTFOLIO.virtualHoldings[orderRef][security]['quantity'] -= quantity
                if action == 'SLD':
                    return (avgFillPrice - p) * quantity
                else:
                    return -(avgFillPrice - p) * quantity
            elif q < quantity:
                self.PORTFOLIO.virtualHoldings[orderRef][security]['action'] = action
                self.PORTFOLIO.virtualHoldings[orderRef][security]['quantity'] = quantity - q
                self.PORTFOLIO.virtualHoldings[orderRef][security]['avgFillPrice'] = avgFillPrice
                if action == 'SLD':
                    return (avgFillPrice - p) * q
                else:
                    return -(avgFillPrice - p) * q
            else:
                if action == 'SLD':
                    tmp = (avgFillPrice - p) * q
                else:
                    tmp = -(avgFillPrice - p) * q
                del self.PORTFOLIO.virtualHoldings[orderRef][security]
                return tmp

    # special function
    def validateAccountCode(self, accountCode):
        self.log.notset(__name__ + '::validateAccountCode: %s' % (accountCode,))
        if accountCode != 'default' and 'DUC' not in accountCode:
            self.accountCodeCallBackSet.add(accountCode)
        if accountCode == 'default':
            accountCode = self.accountCode
        if accountCode == self.accountCode:
            self.PORTFOLIO = self.context.portfolio
            return True
        else:
            # self.log.error(__name__ + '::validateAccountCode: unexpected accountCode = %s' % (accountCode,))
            # self.log.error(__name__ + '::validateAccountCode: Input accountCode ' + str(self.accountCode))
            # self.log.error('Please contact with IBridgePy@gmail.com about IBridgePy for Multi Account')
            return False

    def orderId_to_accountCode(self, orderId):
        self.log.notset(__name__ + '::orderId_to_accountCode: orderId = %s' % (orderId,))
        return self.accountCode

    def update_last_price_in_positions(self, last_price, security):
        self.log.notset(__name__+'::update_last_price_in_positions: last_price = %s security = %s'
                        % (str(last_price), security.full_print()))
        self.validateAccountCode(self.accountCode)
        if self.PORTFOLIO.positions and security in self.PORTFOLIO.positions:
            self.PORTFOLIO.positions[security].last_sale_price = last_price

    def adjust_accountCode(self, accountCode):
        self.log.notset(__name__+'::adjust_accountCode: %s' % (accountCode,))
        if accountCode == 'default':
            return self.accountCode
        else:
            return accountCode
