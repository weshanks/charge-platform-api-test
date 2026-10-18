# -*- coding: utf-8 -*-
"""pytest 公共 fixture。

做了三件事：
1. 会话级登录，token 注入到请求客户端（接口关联的基础）；
2. 被测服务自检——没起就自动拉起 mock_server，保证 clone 即跑；
3. ctx 字典用于跨用例传递运行时变量（如 order_no、device_code）。
"""

import os
import subprocess
import sys
import time

import pytest
import requests

from api.login_api import LoginApi
from common.db_client import DBClient
from common.request_client import RequestClient
from common.yaml_util import BASE_DIR, load_config

MOCK_APP = os.path.join(BASE_DIR, "mock_server", "app.py")


def _server_alive(base_url, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        try:
            r = requests.get(base_url + "/health", timeout=1)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            time.sleep(0.5)
    return False


@pytest.fixture(scope="session")
def cfg():
    return load_config()


@pytest.fixture(scope="session", autouse=True)
def mock_server(cfg):
    """被测服务未启动时自动拉起，会话结束关闭。"""
    if _server_alive(cfg["base_url"], timeout=2):
        yield
        return

    proc = subprocess.Popen([sys.executable, MOCK_APP],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not _server_alive(cfg["base_url"], timeout=20):
        proc.terminate()
        pytest.exit("被测 mock 服务启动失败", returncode=1)
    try:
        yield
    finally:
        proc.terminate()


@pytest.fixture(scope="session")
def client(cfg, mock_server):
    c = RequestClient(cfg["base_url"], timeout=cfg.get("timeout", 10))
    yield c
    c.session.close()


@pytest.fixture(scope="session")
def token(client, cfg):
    resp = LoginApi.login(client, cfg["account"]["username"], cfg["account"]["password"])
    assert resp.status_code == 200 and resp.json()["code"] == 0, f"登录失败：{resp.text}"
    value = resp.json()["data"]["token"]
    client.set_token(value)
    return value


@pytest.fixture(scope="session", autouse=True)
def login(client, token):
    """所有用例执行前先完成登录，token 注入客户端（接口关联的第一步）。"""
    return token


@pytest.fixture(scope="session")
def db(cfg):
    d = DBClient(cfg["db"])
    yield d
    d.close()


@pytest.fixture(scope="session")
def ctx():
    """跨用例传递运行时变量。"""
    return {}
