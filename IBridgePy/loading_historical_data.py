from data_provider_factory.data_provider_utils import LoadingPlan, Plan
from IBridgePy.IbridgepyTools import symbol, superSymbol


def create_a_loading_plan(rootFolderName):
    loadingPlan = LoadingPlan(barSize='1 min', goBack='1 day', rootFolderName=rootFolderName)
    loadingPlan.add(Plan(security=symbol('CASH,EUR,USD'), fileName='testData.csv'))
    loadingPlan.add(Plan(security=symbol('CASH,USD,JPY'), fileName='testData.csv'))
    return loadingPlan


if __name__ == '__main__':
    for plan in create_a_loading_plan().getFinalPlan():
        print(plan)
