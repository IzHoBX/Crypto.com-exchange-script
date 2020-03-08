import APIHelper
import sys
import time

MARKET_SYM = "linkcro"
EXECUTION_INTERVAL = 1
ORDER_DONE_STATUS_CODE = 2
DEFAULT_AMOUNT_TO_BUY_IN_TARGET = 1

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

def getPriceToBuyAt():
    sell = getLowestSellingPrice(MARKET_SYM)
    buy = getHighestBuyingPrice(MARKET_SYM)
    return round(min(buy+0.1, buy+sell/2), 2)

def updateBuyingOids(buyingOids):
    currentBuyingPrice = getHighestBuyingPrice(MARKET_SYM)
    for i in range(0, len(buyingOids)):
        info = apiHelper.get_order(MARKET_SYM, buyingOids[i])
        if info['data']['order_info']['price'] < currentBuyingPrice:
            apiHelper.cancel_order(MARKET_SYM, buyingOids[i])
            apiHelper.create_order(MARKET_SYM, "SELL", round(info['data']['order_info']['price']*1.003, 2), info['data']['order_info']['deal_volume'])
            buyingOids = buyingOids[:i] + buyingOids[i+1:]
        elif info['data']['order_info']['price'] == currentBuyingPrice:
            if apiHelper.get_ordst(MARKET_SYM, lastBuyingOrder[0]) == ORDER_DONE_STATUS_CODE:
                apiHelper.create_order(MARKET_SYM, "SELL", round(info['data']['order_info']['price']*1.003, 2), info['data']['order_info']['deal_volume'])
                buyingOids = buyingOids[:i] + buyingOids[i+1:]
        else:#if my buying price is higher than current  highest buying price, that means order completed
            apiHelper.create_order(MARKET_SYM, "SELL", round(info['data']['order_info']['price']*1.003, 2), info['data']['order_info']['deal_volume'])
            buyingOids = buyingOids[:i] + buyingOids[i+1:]

    return buyingOids

apiHelper = APIHelper.CryptoAPI(sys.argv[1], sys.argv[2])

buyingOids = []
lastBuyingPrice = -1

while True:
    buyingOids = updateBuyingOids(buyingOids)
    priceToBuyAt = getPriceToBuyAt()
    if lastBuyingPrice == priceToBuyAt:
        continue
    elif float(getBalance("cro")) > priceToBuyAt * DEFAULT_AMOUNT_TO_BUY_IN_TARGET:
        buyingOids.append(apiHelper.create_order(MARKET_SYM, "BUY", priceToBuyAt, DEFAULT_AMOUNT_TO_BUY_IN_TARGET)['data']['order_id'])
        lastBuyingPrice = priceToBuyAt
    time.sleep(EXECUTION_INTERVAL)
