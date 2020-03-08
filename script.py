import APIHelper
import sys
import time
import datetime

MARKET_SYM = "linkcro"
EXECUTION_INTERVAL = 300
ORDER_DONE_STATUS_CODE = 2
DEFAULT_AMOUNT_TO_BUY_IN_TARGET = 1
DEFAULT_PROFIT_MARGIN = 1.005
DEFAULT_OUTBID_MARGIN = 0.10

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
    return round(min(buy+DEFAULT_OUTBID_MARGIN, buy+sell/2), 2)

def updateBuyingOids(buyingOids):
    global totalTargetTraded
    print("-----------------------------------------------------------------")
    print("updating buying orders at time: " + str(datetime.datetime.now()))
    currentBuyingPrice = getHighestBuyingPrice(MARKET_SYM)
    for i in range(0, len(buyingOids)):
        info = apiHelper.get_order(MARKET_SYM, buyingOids[i])
        orderPrice = float(info['data']['order_info']['price'])
        toSellPrice = getToSellPrice(orderPrice)
        completedVolume = float(info['data']['order_info']['deal_volume'])
        if orderPrice < currentBuyingPrice:
            print("market buying price has rose above our bid at: " + str(currentBuyingPrice) + " cancelling order at: " + str(orderPrice))
            apiHelper.cancel_order(MARKET_SYM, buyingOids[i])
            totalTargetTraded += completedVolume
            if completedVolume > 0:
                apiHelper.create_order(MARKET_SYM, "SELL", toSellPrice, completedVolume)
                print("created order selling order with price: " + str(toSellPrice))
            else:
                print("Nothing was bought, no need to sell")
            buyingOids = buyingOids[:i] + buyingOids[i+1:]
        elif orderPrice == currentBuyingPrice:
            print("market price equal to our bid at: " + str(orderPrice))
            if apiHelper.get_ordst(MARKET_SYM, buyingOids[i]) == ORDER_DONE_STATUS_CODE:
                totalTargetTraded+=completedVolume
                apiHelper.create_order(MARKET_SYM, "SELL", toSellPrice, completedVolume)
                print("Our order complated. Created order selling order with price: " + str(toSellPrice))
                buyingOids = buyingOids[:i] + buyingOids[i+1:]
        else:#if my buying price is higher than current  highest buying price, that means order completed
            print("market buying price is: " + str(currentBuyingPrice) + "which is lower than our bid. Creating sell order at: " + str(toSellPrice))
            apiHelper.create_order(MARKET_SYM, "SELL", toSellPrice, completedVolume)
            buyingOids = buyingOids[:i] + buyingOids[i+1:]
            totalTargetTraded+=completedVolume

    return buyingOids

def printCurrentBuyingOrders(buyingOids):
    for id in buyingOids:
        print(str(id) + " " + apiHelper.get_order(MARKET_SYM, id)['data']['order_info']['price'])

def getToSellPrice(buyingPrice):
    return round(buyingPrice*DEFAULT_PROFIT_MARGIN, 2)

apiHelper = APIHelper.CryptoAPI(sys.argv[1], sys.argv[2])

buyingOids = []
lastBuyingPrice = -1

while True:
    buyingOids = updateBuyingOids(buyingOids)
    priceToBuyAt = getPriceToBuyAt()
    if lastBuyingPrice == priceToBuyAt:
        print("same as last buying price: " + lastBuyingOrder + " no action taken")
        continue
    elif float(getBalance("cro")) > priceToBuyAt * DEFAULT_AMOUNT_TO_BUY_IN_TARGET:
        print("creating new buying order because price changed")
        buyingOids.append(apiHelper.create_order(MARKET_SYM, "BUY", priceToBuyAt, DEFAULT_AMOUNT_TO_BUY_IN_TARGET)['data']['order_id'])
        printCurrentBuyingOrders(buyingOids)
        lastBuyingPrice = priceToBuyAt
    else:
        print("Insufficient balance. No buying order created despite price changed. ")
    time.sleep(EXECUTION_INTERVAL)
