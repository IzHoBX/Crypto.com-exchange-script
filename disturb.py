import APIHelper
import sys
import time
import datetime
import math

MARKET_SYM = "linkcro"
TARGET_SYM = "link"
EXECUTION_INTERVAL = 10
ORDER_DONE_STATUS_CODE = 2

DEFAULT_AMOUNT_TO_BUY_IN_TARGET = 1
DEFAULT_PROFIT_MARGIN = 1.005
DEFAULT_OUTBID_MARGIN = 0.10

HEAVY_CAPITAL_THRESHOLD = 100

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

def getPriceToBuyAt(buy, sell):
    return round(min(buy+DEFAULT_OUTBID_MARGIN, buy+sell/2, sell-0.01), 2)

def easyToSell(priceToSellAt):
    cummulativeStock = 0
    for order in apiHelper.depth(MARKET_SYM)['data']['tick']['asks']:
        if order[0] <= priceToSellAt:
            cummulativeStock += order[1]
        else:
            break
    if cummulativeStock > HEAVY_CAPITAL_THRESHOLD:
        return False
    else:
        return True

def createBuyingOrder(priceToBuyAt):
    if easyToSell(getToSellPrice(priceToBuyAt)):
        print("creating new buying order")
        if float(getBalance("cro")) > priceToBuyAt * DEFAULT_AMOUNT_TO_BUY_IN_TARGET:
            return apiHelper.create_order(MARKET_SYM, "BUY", priceToBuyAt, DEFAULT_AMOUNT_TO_BUY_IN_TARGET)['data']['order_id']
        else:
            print("Insufficient balance. No buying order created despite price changed. ")
            return -1
    else:
        print("Difficult to sell, not buying")
        return -1

def updatebuyingOrder(buyingOid):
    global totalTargetTraded
    print("-----------------------------------------------------------------")
    print("updating buying orders at time: " + str(datetime.datetime.now()))
    currentBuyingPrice = getHighestBuyingPrice(MARKET_SYM)
    currentSellingPrice = getLowestSellingPrice(MARKET_SYM)
    priceToBuyAt = getPriceToBuyAt(currentBuyingPrice, currentSellingPrice)
    if buyingOid == -1:
        return createBuyingOrder(priceToBuyAt)
    info = apiHelper.get_order(MARKET_SYM, buyingOid)
    orderPrice = float(info['data']['order_info']['price'])
    toSellPrice = getToSellPrice(orderPrice)
    completedVolume = float(info['data']['order_info']['deal_volume'])
    if orderPrice < currentBuyingPrice:
        print("market buying price has rose above our bid at: " + str(currentBuyingPrice) + " cancelling order at: " + str(orderPrice))
        apiHelper.cancel_order(MARKET_SYM, buyingOid)
        totalTargetTraded += completedVolume
        if completedVolume > 0:
            apiHelper.create_order(MARKET_SYM, "SELL", toSellPrice, math.floor(float(getBalance(TARGET_SYM)) * 100)/100.0)
            print("created order selling order with price: " + str(toSellPrice))
        else:
            print("Nothing was bought, no need to sell")
        return createBuyingOrder(priceToBuyAt)
    elif orderPrice == currentBuyingPrice:
        print("market price equal to our bid at: " + str(orderPrice))
        if apiHelper.get_ordst(MARKET_SYM, buyingOid) == ORDER_DONE_STATUS_CODE:
            totalTargetTraded+=completedVolume
            apiHelper.create_order(MARKET_SYM, "SELL", toSellPrice, math.floor(float(getBalance(TARGET_SYM)) * 100)/100.0)
            print("Our order complated. Created order selling order with price: " + str(toSellPrice))
            return createBuyingOrder(priceToBuyAt)
        else:
            if easyToSell(toSellPrice):
                print("Our order still in progress, no order created")
            else:
                print("It has became difficult to sell, cancelling order")
                apiHelper.create_order(MARKET_SYM, "SELL", toSellPrice, math.floor(float(getBalance(TARGET_SYM)) * 100)/100.0)
                apiHelper.cancel_order(MARKET_SYM, buyingOid)
                buyingOid = -1
            return buyingOid
    else:#if my buying price is higher than current  highest buying price, that means order completed
        print("market buying price is: " + str(currentBuyingPrice) + "which is lower than our bid. Creating sell order at: " + str(toSellPrice))
        apiHelper.create_order(MARKET_SYM, "SELL", toSellPrice, math.floor(float(getBalance(TARGET_SYM)) * 100)/100.0)
        totalTargetTraded+=completedVolume
        return createBuyingOrder(priceToBuyAt)

def printCurrentBuyingOrder(buyingOid):
    if buyingOid == -1:
        print("no buying order in queue")
    else:
        print(str(buyingOid) + " " + apiHelper.get_order(MARKET_SYM, buyingOid)['data']['order_info']['price'])

def getToSellPrice(buyingPrice):
    return round(buyingPrice*DEFAULT_PROFIT_MARGIN, 2)

apiHelper = APIHelper.CryptoAPI(sys.argv[1], sys.argv[2])

lastid= -1

while True:
    if getLowestSellingPrice(MARKET_SYM) != getHighestBuyingPrice(MARKET_SYM) + 0.01:
        if lastid != -1:
            info = apiHelper.get_order(MARKET_SYM, lastid)
            apiHelper.cancel_order(MARKET_SYM, lastid)
            print(1.002*float(info['data']['order_info']['price']))
            print(apiHelper.create_order(MARKET_SYM, "SELL", round(1.002*float(info['data']['order_info']['price']), 2), math.floor(float(getBalance(TARGET_SYM)) * 100)/100.0))
        res = apiHelper.create_order(MARKET_SYM, "BUY", getLowestSellingPrice(MARKET_SYM)-0.01, 1)
        try:
            lastid = res['data']['order_id']
        except KeyError:
            lastid = -1
    time.sleep(1)
