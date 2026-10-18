# -*- coding: utf-8 -*-
"""接口层：登录鉴权，只发请求不做断言。"""


class LoginApi:
    path = "/api/login"

    @staticmethod
    def login(client, username, password):
        return client.post(LoginApi.path, json={"username": username, "password": password})
