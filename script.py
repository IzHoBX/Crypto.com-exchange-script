import APIHelper
import sys
import time
import datetime
import math

MARKET_SYM = "LINK_CRO"
TARGET_SYM = "link"
EXECUTION_INTERVAL = 10
ORDER_DONE_STATUS_CODE = 2

DEFAULT_AMOUNT_TO_BUY_IN_TARGET = 1
DEFAULT_PROFIT_MARGIN = 1.005
DEFAULT_OUTBID_MARGIN = 0.10

HEAVY_CAPITAL_THRESHOLD = 100
MINIMUM_BALANCE = 3000

depth_cache = []

# by default only returns normal (available for use balance)
def getBalance(sym):
    balanceDataList = apiHelper.balance()["data"]["coin_list"]
    for balanceData in balanceDataList:
        if balanceData['coin'] == sym:
            return balanceData['normal']
    #to prevent overspending when there is data error
    return "0"

def getLowestSellingPrice(sym):
    return apiHelper.depth(sym)['data']['tick']['asks'][0][0]

def getHighestBuyingPrice(sym, fetchNew=True, positionFromTop=0):
    global depth_cache
    if fetchNew:
        depth_cache = apiHelper.depth(sym)['data']['tick']['bids']
    return depth_cache[positionFromTop][0]

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
        if float(getBalance("cro")) - priceToBuyAt * DEFAULT_AMOUNT_TO_BUY_IN_TARGET > MINIMUM_BALANCE:
            return apiHelper.create_order(MARKET_SYM, "BUY", priceToBuyAt, DEFAULT_AMOUNT_TO_BUY_IN_TARGET)['data']['order_id']
        else:
            print("Insufficient balance. No buying order created despite price changed. ")
            return -1
    else:
        print("Difficult to sell, not buying")
        return -1

def createSellingOrder(toSellPrice, volume):
    if volume == 0:
        return
    res = apiHelper.create_order(MARKET_SYM, "SELL", toSellPrice, volume)
    if res['code'] == -1:
        res = apiHelper.create_order(MARKET_SYM, "SELL", toSellPrice, volume-0.01)
        if res['code'] == -1:
            print("attempting to sell " + str(volume-0.01) + "at " + str(toSellPrice) + " but failed")
            print("current account balance: " + getBalance(TARGET_SYM))
            sys.exit()

def updatebuyingOrder(buyingOid):
    global totalTargetTraded
    print("-----------------------------------------------------------------")
    print("updating buying orders at time: " + str(datetime.datetime.now()))
    currentBuyingPrice = getHighestBuyingPrice(MARKET_SYM)
    secondHighestBuyingPrice = getHighestBuyingPrice(MARKET_SYM, fetchNew=False, positionFromTop=1)
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
            createSellingOrder(toSellPrice, completedVolume)
            print("created order selling order with price: " + str(toSellPrice))
        else:
            print("Nothing was bought, no need to sell")
        return createBuyingOrder(priceToBuyAt)
    elif orderPrice == currentBuyingPrice:
        print("market price equal to our bid at: " + str(orderPrice))
        if apiHelper.get_ordst(MARKET_SYM, buyingOid) == ORDER_DONE_STATUS_CODE:
            totalTargetTraded+=completedVolume
            createSellingOrder(toSellPrice, completedVolume)
            print("Our order complated. Created order selling order with price: " + str(toSellPrice))
            return createBuyingOrder(priceToBuyAt)
        else:
            if easyToSell(toSellPrice):
                newBestBuyingPrice = getPriceToBuyAt(secondHighestBuyingPrice, currentSellingPrice)
                if newBestBuyingPrice < orderPrice:
                    print("offer too much than higher. cancelling our order at: " + str(orderPrice))
                    apiHelper.cancel_order(MARKET_SYM, buyingOid)
                    print("creating selling order at: " + str(toSellPrice))
                    createSellingOrder(toSellPrice, completedVolume)
                    print("creating new lowered buying order at: " + str(newBestBuyingPrice))
                    buyingOid = createBuyingOrder(newBestBuyingPrice)
                else:
                    print("Our order still in progress, no order created")
            else:
                print("It has became difficult to sell, cancelling order")
                createSellingOrder(toSellPrice, completedVolume)
                apiHelper.cancel_order(MARKET_SYM, buyingOid)
                buyingOid = -1
            return buyingOid
    else:#if my buying price is higher than current  highest buying price, that means order completed
        print("market buying price is: " + str(currentBuyingPrice) + "which is lower than our bid. Creating sell order at: " + str(toSellPrice))
        createSellingOrder(toSellPrice, completedVolume)
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

lastBuyingOid = -1
totalTargetTraded = 0

while True:
    try:
        lastBuyingOid = updatebuyingOrder(lastBuyingOid)
        print("currently bought LINK amount: " + str(totalTargetTraded))
        printCurrentBuyingOrder(lastBuyingOid)
        time.sleep(EXECUTION_INTERVAL)
    except KeyboardInterrupt:
        if lastBuyingOid != -1:
            info = apiHelper.get_order(MARKET_SYM, lastBuyingOid)
            orderPrice = float(info['data']['order_info']['price'])
            toSellPrice = getToSellPrice(orderPrice)
            completedVolume = math.floor(float(info['data']['order_info']['deal_volume']) * 100)/100
            apiHelper.cancel_order(MARKET_SYM, lastBuyingOid)
            createSellingOrder(toSellPrice, completedVolume)
            totalTargetTraded+=completedVolume
        print("totalTraded:" + str(totalTargetTraded))
        print("exiting")
        sys.exit()
