# -*- coding: utf-8 -*-
"""请求封装：统一处理 base_url 拼接、超时、鉴权注入、请求响应日志与异常兜底。"""

import logging

import requests

logger = logging.getLogger("api")


class RequestClient:
    def __init__(self, base_url, timeout=10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.token = None

    def set_token(self, token):
        """登录后注入 token，后续请求自动带上。"""
        self.token = token
        self.session.headers.update({"Authorization": token})

    def clear_token(self):
        self.token = None
        self.session.headers.pop("Authorization", None)

    def request(self, method, path, **kwargs):
        url = path if path.startswith("http") else self.base_url + path
        logger.info("→ %s %s | params=%s json=%s", method, url,
                    kwargs.get("params"), kwargs.get("json"))
        try:
            resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.RequestException as e:
            logger.error("请求异常: %s", e)
            raise
        logger.info("← %s %s | %s | %s", method, url, resp.status_code, resp.text[:500])
        return resp

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def put(self, path, **kwargs):
        return self.request("PUT", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)
