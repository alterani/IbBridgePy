# -*- coding: utf-8 -*-
"""
Created on Fri Jul 20 00:24:07 2018

@author: uvali
"""

if __name__ == '__main__':
    from FakeMarketCalendar import FakeMarketCalendar
    from MarketCalendar import MarketCalendar
else:
    from BasicPyLib.FakeMarketCalendar import FakeMarketCalendar
    from BasicPyLib.MarketCalendar import MarketCalendar


class MarketCalendarWrapper:
    def __init__(self, marketName='NYSE'):
        if marketName == 'Fake':
            self.marketCalendar = FakeMarketCalendar()
        else:
            self.marketCalendar = MarketCalendar(marketName)

    def getMarketCalendar(self):
        return self.marketCalendar


if __name__ == '__main__':
    import datetime as dt

    name = 'NYSE'
    c = MarketCalendarWrapper(name)
    ans = c.getMarketCalendar()
    #print(ans.get_market_open_close_time(dt.datetime.now()))
    print(ans.trading_day(dt.date(2017,8,1)))
    print(ans.nth_trading_day_of_month(dt.date(2017,8,1)))
