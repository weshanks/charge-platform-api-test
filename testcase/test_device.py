# -*- coding: utf-8 -*-
"""设备管理用例：增删改查 + 分页 + 参数校验 + 数据库落库校验。"""

import uuid

import allure
import pytest

from api.device_api import DeviceApi
from common.assert_util import (assert_api_ok, assert_code, assert_db_count,
                                assert_db_field, assert_equal, assert_status)
from common.yaml_util import load_case

data = load_case("test_device.yaml")
PREFIX = "AUTO"


def _new_code():
    return f"{PREFIX}{uuid.uuid4().hex[:8].upper()}"


@allure.feature("设备管理")
class TestDevice:

    @allure.story("新增设备")
    @allure.title("新增设备成功并正确落库")
    @pytest.mark.smoke
    def test_add_device_success(self, client, db, ctx):
        code = _new_code()
        resp = DeviceApi.add(client, code, data["add_ok"]["station_name"],
                             data["add_ok"]["power"])
        assert_api_ok(resp)
        assert_equal(resp.json()["data"]["device_code"], code, "返回设备编码")
        assert_db_field(db, "SELECT * FROM t_device WHERE device_code=%s", (code,),
                        "status", "idle", "新增设备")
        ctx["device_code"] = code

    @allure.story("新增设备")
    @allure.title("设备编码重复时新增失败")
    def test_add_device_duplicate(self, client, ctx):
        code = ctx["device_code"]
        resp = DeviceApi.add(client, code, data["add_ok"]["station_name"])
        assert_status(resp, 200)
        assert_code(resp, 2003)

    @allure.story("新增设备")
    @allure.title("缺少必填参数时新增失败")
    def test_add_device_missing_param(self, client):
        resp = client.post(DeviceApi.path, json={"device_code": _new_code()})
        assert_status(resp, 200)
        assert_code(resp, 3001)

    @allure.story("查询设备")
    @allure.title("设备列表分页返回条数与 size 一致")
    def test_device_list_paging(self, client, db):
        for _ in range(3):
            DeviceApi.add(client, _new_code(), data["add_ok"]["station_name"])
        resp = DeviceApi.list(client, data["paging"]["page"], data["paging"]["size"])
        assert_api_ok(resp)
        assert_equal(len(resp.json()["data"]["list"]), data["paging"]["size"], "本页条数")
        assert resp.json()["data"]["total"] >= 3, "总条数应不少于 3"

    @allure.story("修改设备")
    @allure.title("修改设备状态成功并落库")
    def test_update_device_status(self, client, db, ctx):
        code = ctx["device_code"]
        resp = DeviceApi.update_status(client, code, data["update_status"])
        assert_api_ok(resp)
        assert_db_field(db, "SELECT * FROM t_device WHERE device_code=%s", (code,),
                        "status", data["update_status"], "修改设备状态")

    @allure.story("修改设备")
    @allure.title("状态取值非法时修改失败")
    def test_update_device_invalid_status(self, client, ctx):
        resp = DeviceApi.update_status(client, ctx["device_code"], data["invalid_status"])
        assert_status(resp, 200)
        assert_code(resp, 3001)

    @allure.story("删除设备")
    @allure.title("删除设备成功且数据库中不再存在")
    def test_delete_device(self, client, db):
        code = _new_code()
        DeviceApi.add(client, code, data["add_ok"]["station_name"])
        resp = DeviceApi.delete(client, code)
        assert_api_ok(resp)
        assert_db_count(db, "SELECT * FROM t_device WHERE device_code=%s", (code,),
                        0, "删除设备")
