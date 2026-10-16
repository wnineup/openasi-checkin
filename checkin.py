# -*- coding: utf-8 -*-
"""OpenASI 每日自动签到。

开机自动运行：登录换 token -> 签到 -> 写日志。
账号密码放在同目录的 config.json（不进 git）。
"""
import json
import logging
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent

logging.basicConfig(
    filename=HERE / "checkin.log",
    level=logging.INFO,
    encoding="utf-8",
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("checkin")

LOGIN_URL = "https://api.openasi.bitmiracle.cn/api/auth/sign-in/email"
CHECKIN_URL = "https://api.openasi.bitmiracle.cn/api/checkin"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36 Edg/155.0.0.0")

MAX_TRIES = 10      
RETRY_WAIT = 15     


def load_config():
    """读 config.json；读不到就返回空字典，别让脚本崩。"""
    try:
        return json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log.error("读取 config.json 失败: %s", e)
        return {}


def login(email, password):
    """拿账号密码换 token；拿不到就返回 None。

    故意不记录响应体——登录响应的 body 里带着 token。
    """
    r = requests.post(
        LOGIN_URL,
        json={"email": email, "password": password},
        timeout=(5, 20),
    )
    log.info("登录 HTTP %s", r.status_code)
    return r.headers.get("set-auth-token")


def checkin(token):
    """发签到请求。注意是 s.post，不是 requests.post。"""
    with requests.Session() as s:
        s.headers["User-Agent"] = UA
        s.headers["Authorization"] = "Bearer " + token
        return s.post(CHECKIN_URL, json={"data": {}}, timeout=(5, 20))


def judge(r):
    """看 error 字段判断结果，不看 HTTP 状态码。

    这个接口无论成败都返回 HTTP 200。

    返回 "ok"（签到成功）/ "done"（今天已签）/ "fail"（失败）
    """
    try:
        err = r.json().get("error")
    except ValueError:
        return "fail"
    if err is None:
        return "ok"
    if err.get("code") == "CONFLICT":
        return "done"
    return "fail"


def main():
    cfg = load_config()
    email, password = cfg.get("email"), cfg.get("password")
    if not (email and password):
        log.error("config.json 里缺少 email / password，停止")
        return

    for i in range(1, MAX_TRIES + 1):
        try:
            token = login(email, password)
            if not token:
                log.error("第%d次 没拿到 set-auth-token，停止", i)
                return
            r = checkin(token)
        except requests.RequestException as e:
            log.warning("第%d次 网络异常: %s", i, e)
        else:
            result = judge(r)
            log.info("第%d次 HTTP %s 判定=%s %s",
                     i, r.status_code, result, r.text[:300])
            if result in ("ok", "done"):
                return
        time.sleep(RETRY_WAIT)


if __name__ == "__main__":
    main()
