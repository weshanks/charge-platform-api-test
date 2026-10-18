# -*- coding: utf-8 -*-
"""登录鉴权用例。"""

import allure
import pytest

from api.login_api import LoginApi
from common.assert_util import assert_code, assert_status
from common.yaml_util import load_case

cases = load_case("test_login.yaml")


@allure.feature("登录鉴权")
class TestLogin:

    @allure.story("登录成功")
    @allure.title("正确账号密码登录成功并返回 token")
    @pytest.mark.smoke
    def test_login_success(self, client, cfg, token):
        assert token.startswith("tk_"), f"token 格式异常：{token}"

    @allure.story("登录失败")
    @allure.title("{case}")
    @pytest.mark.parametrize("case", cases["negative"], ids=[c["case"] for c in cases["negative"]])
    def test_login_failed(self, client, case):
        resp = LoginApi.login(client, case["username"], case["password"])
        assert_status(resp, 200)     # HTTP 200
        assert_code(resp, case["expect_code"])
