import APIHelper
import sys
MARKET_SYM = "linkcro"
EXECUTION_INTERVAL = 1

# by default only returns normal (available for use balance)
def getBalance(sym):
    balanceDataList = apiHelper.balance()["data"]["coin_list"]
    for balanceData in balanceDataList:
        if balanceData['coin'] == sym:
            return balanceData['normal']
    #to prevent overspending when there is data error
    return 0

def getLowestSellingPrice(sym):
    return apiHelper.depth(sym)['data']['tick']['asks'][0][0]

def getHighestBuyingPrice(sym):
    return apiHelper.depth(sym)['data']['tick']['bids'][0][0]

apiHelper = APIHelper.CryptoAPI(sys.argv[1], sys.argv[2])
#print(apiHelper.create_order("xrpcro", "BUY", 4.00, 1))
#print(getBalance(apiHelper.balance(), "cro"))
print(getHighestBuyingPrice("linkcro"))
while True:
    sell = getLowestSellingPrice(MARKET_SYM)
    buy = getHighestBuyingPrice(MARKET_SYM)
