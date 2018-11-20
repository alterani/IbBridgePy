# -*- coding: utf-8 -*-
"""
Created on Wed Aug 22 23:50:16 2018

@author: IBridgePy@gmail.com
"""
import os
from IBridgePy.constants import DataProviderName


def get_data_provider(name):
    if name == DataProviderName.IB:
        from .interactiveBrokers import InteractiveBrokers
        return InteractiveBrokers


class Plan:
    """
    Each plan contains the loading setup of each security
    """
    def __init__(self, security, barSize, fileName):
        self.str_security = str(security)
        self.barSize = barSize
        self.fullFilePath = fileName

    def __str__(self):
        return self.str_security + ' ' + self.barSize + ' ' + self.fullFilePath


class LoadingPlan:
    """
    finalPlan is a Set() to contain all specific plans
    """
    def __init__(self):
        self.finalPlan = set()

    def add(self, plan):
        self.finalPlan.add(plan)

    def getFinalPlan(self):
        return self.finalPlan

    def adjust_root_folder_name(self, rootFolderName):
        for plan in self.finalPlan:
            plan.fullFilePath = os.path.join(rootFolderName, plan.fullFilePath)
        return self
