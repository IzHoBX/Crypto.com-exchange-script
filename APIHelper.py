import urllib.parse
import requests
import hashlib
import time
import hmac


def get_timestamp():
    return int(time.time() * 1000)


class CryptoAPI:
    def __init__(self, key, sec):
        self.timeout = 1000
        self.apiurl = "https://api.crypto.com/v2/"
        self.apikey = key
        self.apisec = sec
        return

    def http_get(self, url, params):
        headers = {
            'Content-Type': "application/x-www-form-urlencoded"
        }
        data = urllib.parse.urlencode(params or {})
        try:
            response = requests.get(url, data, headers=headers, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                return {"code": -1, "msg": "response status:%s" % response.status_code}
        except Exception as e:
            print("httpGet failed, detail is:%s" % e)
            return {"code": -1, "msg": e}

    def http_post(self, url, params):
        headers = {
            "Content-type": "application/json",
        }
        try:
            response = requests.post(url, json=params, headers=headers, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                return {"code": -1, "msg": f"response code:{response.status_code}, msg: {response.text}" }
        except Exception as e:
            print("httpPost failed, detail is:%s" % e)
            return {"code": -1, "msg": e}

    def api_key_post(self, path, params):
        if not params:
            params = {}
        req = {}
        req["id"] = 1
        req["method"] = path
        req["api_key"] = self.apikey
        req["nonce"] = get_timestamp()
        req["params"] = params
        req["sig"] = self.create_sign(req)
        print(req)
        return self.http_post(self.apiurl + path, req)

    def create_sign(self, params):
        sorted_params = sorted(params["params"].items(), key=lambda d: d[0], reverse=False)
        s = params["method"] + str(params["id"]) + self.apikey + "".join(map(lambda x: str(x[0]) + str(x[1] or ""), sorted_params)) + str(params["nonce"])
        print(s)
        return hmac.new(
            bytes(self.apisec, 'utf-8'),
            msg=bytes(s, 'utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()

    # get order book for market indicated by sym
    def depth(self, sym, n=10):
        url = self.apiurl + "public/get-book"
        print(url)
        params = {"instrument_name": sym, "depth": 10}
        return self.http_get(url, params)

    # list all account balances
    def balance(self):
        path = "private/get-account-summary"
        return self.api_key_post(path, {})

    # list all orders in a given market
    def get_all_orders(self, sym):
        url = self.apiurl + "/v1/allOrders"
        params = {}
        params['symbol'] = sym
        return self.api_key_post(url, params)

    # get ortder detail
    def get_order(self, sym, oid):
        url = self.apiurl + "/v1/showOrder"
        params = {}
        params['order_id'] = oid
        params['symbol'] = sym
        return self.api_key_post(url, params)

    # formatted order detail
    def get_ordst(self, sym, oid):
        url = self.apiurl + "/v1/showOrder"
        params = {}
        params['order_id'] = oid
        params['symbol'] = sym
        res = self.api_key_post(url, params)
        if ('code' in res) and (res['code']=='0') and ('order_info' in res['data']):
            return res['data']['order_info']['status']
        return -1

    # get all pending orders
    def get_open_orders(self, sym):
        url = self.apiurl + "/v1/openOrders"
        params = {}
        params['pageSize'] = '200'
        params['symbol'] = sym
        return self.api_key_post(url, params)

    # get all executed orders
    def get_trades(self, sym):
        url = self.apiurl + "/v1/myTrades"
        params = {}
        params['symbol'] = sym
        return self.api_key_post(url, params)

    def cancel_order(self, sym, oid):
        url = self.apiurl + "/v1/orders/cancel"
        params = {}
        params['order_id'] = oid
        params['symbol'] = sym
        return self.api_key_post(url, params)

    def cancel_order_all(self, sym):
        url = self.apiurl + "/v1/cancelAllOrders"
        params = {}
        params['symbol'] = sym
        return self.api_key_post(url, params)

    # side: BUY, SELL
    # prx: unit proce
    # note: type can be changed - 1: order book, 2 market order
    def create_order(self, sym, side, prx, qty):
        """
            s:return:
        """
        url = self.apiurl + "/v1/order"
        params = {}
        params['price'] = prx
        params['side'] = side
        params['symbol'] = sym
        params['type'] = 1
        params['volume'] = qty
        return self.api_key_post(url, params)

    def getAllMarketSym(self):
        return self.http_get(self.apiurl+"public/get-instruments", None)

    def getCandleSticksData(self, sym, windowSize):
        params = {}
        params['timeframe'] = windowSize
        params['instrument_name'] = sym
        return self.http_get(self.apiurl+"public/get-candlestick", params)
