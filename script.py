import APIHelper
import sys

def getBalance(balanceResponse, sym):
    balanceDataList = balanceResponse["data"]["coin_list"]
    return balanceDataList

apiHelper = APIHelper.CryptoAPI(sys.argv[1], sys.argv[2])
#print(apiHelper.create_order("xrpcro", "BUY", 4.00, 1))
print(getBalance(apiHelper.balance(), "cro"))
