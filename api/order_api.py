# -*- coding: utf-8 -*-
"""接口层：充电与订单，只发请求不做断言。"""


class OrderApi:
    start_path = "/api/charge/start"
    stop_path = "/api/charge/stop"
    order_path = "/api/order"

    @staticmethod
    def start(client, device_code, user_id):
        return client.post(OrderApi.start_path, json={
            "device_code": device_code, "user_id": user_id})

    @staticmethod
    def stop(client, order_no, kwh, coupon=0):
        return client.post(OrderApi.stop_path, json={
            "order_no": order_no, "kwh": kwh, "coupon": coupon})

    @staticmethod
    def detail(client, order_no):
        return client.get(f"{OrderApi.order_path}/{order_no}")

    @staticmethod
    def list(client, user_id=None, status=None, page=1, size=10):
        params = {"page": page, "size": size}
        if user_id:
            params["user_id"] = user_id
        if status:
            params["status"] = status
        return client.get(OrderApi.order_path + "/list", params=params)
