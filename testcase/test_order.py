# -*- coding: utf-8 -*-
"""充电与订单用例：状态机、金额计算、参数校验、接口返回与数据库双重断言。"""

import uuid

import allure
import pytest

from api.device_api import DeviceApi
from api.order_api import OrderApi
from common.assert_util import (assert_amount, assert_api_ok, assert_code,
                                assert_db_amount, assert_db_field, assert_equal,
                                assert_status)
from common.request_client import RequestClient
from common.yaml_util import load_case

data = load_case("test_order.yaml")
USER_ID = "U10001"


def _prepare_charging(client):
    """准备一台空闲设备并启动充电，返回 (device_code, order_no)。"""
    device_code = f"AUTO{uuid.uuid4().hex[:8].upper()}"
    DeviceApi.add(client, device_code, "自动化演练充电站")
    resp = OrderApi.start(client, device_code, USER_ID)
    assert resp.json()["code"] == 0, f"前置启动充电失败：{resp.text}"
    return device_code, resp.json()["data"]["order_no"]


@allure.feature("充电主流程")
class TestCharge:

    @allure.story("启动充电")
    @allure.title("空闲设备启动充电成功，设备与订单状态同步流转")
    @pytest.mark.smoke
    def test_start_charge_success(self, client, db, ctx):
        device_code, order_no = _prepare_charging(client)
        ctx["device_code"] = device_code
        ctx["order_no"] = order_no

        assert_db_field(db, "SELECT * FROM t_order WHERE order_no=%s", (order_no,),
                        "status", "charging", "订单状态")
        assert_db_field(db, "SELECT * FROM t_device WHERE device_code=%s", (device_code,),
                        "status", "charging", "设备状态")

    @allure.story("启动充电")
    @allure.title("设备充电中重复启动失败")
    def test_start_charge_device_busy(self, client, ctx):
        resp = OrderApi.start(client, ctx["device_code"], USER_ID)
        assert_status(resp, 200)
        assert_code(resp, 2002)

    @allure.story("启动充电")
    @allure.title("设备不存在时启动失败")
    def test_start_charge_device_not_exist(self, client):
        resp = OrderApi.start(client, "NOT_EXIST_DEVICE", USER_ID)
        assert_status(resp, 200)
        assert_code(resp, 2001)

    @allure.story("启动充电")
    @allure.title("缺少必填参数时启动失败")
    def test_start_charge_missing_param(self, client):
        resp = client.post(OrderApi.start_path, json={"user_id": USER_ID})
        assert_status(resp, 200)
        assert_code(resp, 3001)

    @allure.story("未鉴权访问")
    @allure.title("未携带 token 访问受保护接口返回 401")
    def test_stop_charge_without_token(self, cfg, ctx):
        anon = RequestClient(cfg["base_url"])
        resp = OrderApi.stop(anon, ctx["order_no"], 1)
        assert_api_ok(resp, expected_code=1002, expected_status=401)
        anon.session.close()


@allure.feature("订单管理")
class TestOrder:

    @allure.story("金额计算")
    @allure.title("{case}")
    @pytest.mark.parametrize("case", data["amount_cases"],
                             ids=[c["case"] for c in data["amount_cases"]])
    def test_stop_charge_amount(self, client, db, case):
        device_code, order_no = _prepare_charging(client)
        resp = OrderApi.stop(client, order_no, case["kwh"], case["coupon"])
        assert_api_ok(resp)

        body = resp.json()["data"]
        assert_amount(body["elec_fee"], case["expected_elec"], "电费")
        assert_amount(body["service_fee"], case["expected_service"], "服务费")
        assert_amount(body["amount"], case["expected_amount"], "应付金额")

        # 双重断言：接口返回 = 数据库落库
        assert_db_amount(db, "SELECT * FROM t_order WHERE order_no=%s", (order_no,),
                         "amount", case["expected_amount"], "订单表金额")
        assert_db_field(db, "SELECT * FROM t_order WHERE order_no=%s", (order_no,),
                        "status", "finished", "订单表状态")
        assert_db_amount(db, "SELECT * FROM t_settle WHERE order_no=%s", (order_no,),
                         "elec_fee", case["expected_elec"], "结算表电费")
        assert_db_amount(db, "SELECT * FROM t_settle WHERE order_no=%s", (order_no,),
                         "pay_amount", case["expected_amount"], "结算表应付金额")

        # 停止充电后设备应回到空闲
        assert_db_field(db, "SELECT * FROM t_device WHERE device_code=%s", (device_code,),
                        "status", "idle", "设备状态")

    @allure.story("停止充电")
    @allure.title("{case}")
    @pytest.mark.parametrize("case", data["invalid_kwh"],
                             ids=[c["case"] for c in data["invalid_kwh"]])
    def test_stop_charge_invalid_kwh(self, client, case):
        _, order_no = _prepare_charging(client)
        resp = OrderApi.stop(client, order_no, case["kwh"])
        assert_status(resp, 200)
        assert_code(resp, case["expect_code"])

    @allure.story("停止充电")
    @allure.title("重复停止同一订单失败")
    def test_stop_charge_twice(self, client):
        _, order_no = _prepare_charging(client)
        assert OrderApi.stop(client, order_no, 1).json()["code"] == 0
        resp = OrderApi.stop(client, order_no, 1)
        assert_status(resp, 200)
        assert_code(resp, 2002)

    @allure.story("查询订单")
    @allure.title("订单详情与订单列表可按用户过滤查询")
    def test_order_query(self, client, ctx):
        detail = OrderApi.detail(client, ctx["order_no"])
        assert_api_ok(detail)
        assert_equal(detail.json()["data"]["order_no"], ctx["order_no"], "订单号")

        lst = OrderApi.list(client, user_id=USER_ID, page=1, size=5)
        assert_api_ok(lst)
        assert lst.json()["data"]["total"] >= 1, "订单列表应至少有一条"
        assert_equal(len(lst.json()["data"]["list"]) <= 5, True, "分页条数上限")
