# -*- coding: utf-8 -*-
"""接口层：设备管理，只发请求不做断言。"""


class DeviceApi:
    path = "/api/device"

    @staticmethod
    def add(client, device_code, station_name, power=120):
        return client.post(DeviceApi.path, json={
            "device_code": device_code,
            "station_name": station_name,
            "power": power,
        })

    @staticmethod
    def list(client, page=1, size=10):
        return client.get(DeviceApi.path + "/list", params={"page": page, "size": size})

    @staticmethod
    def detail(client, device_code):
        return client.get(f"{DeviceApi.path}/{device_code}")

    @staticmethod
    def update_status(client, device_code, status):
        return client.put(f"{DeviceApi.path}/{device_code}", json={"status": status})

    @staticmethod
    def delete(client, device_code):
        return client.delete(f"{DeviceApi.path}/{device_code}")
