# OpenASI 自动签到

Windows 开机自动登录 [OpenASI](https://app.openasi.bitmiracle.cn/dashboard) 并完成每日签到。

## 原理

1. `POST /api/auth/sign-in/email`，请求体 `{"email": ..., "password": ...}`
   → 从**响应头** `set-auth-token` 取 token（不是从响应体的 `token` 字段）
2. `POST /api/checkin`，请求头 `Authorization: Bearer <token>`，请求体 `{"data": {}}`

> **这个 API 无论成败都返回 HTTP 200。** 真正的结果在响应体的 `error` 字段里：

| 响应体 | 含义 |
| --- | --- |
| `"error": null` | 签到成功 |
| `"error": {"code": "CONFLICT"}` | 今天已经签过了 |
| `"error": {"code": "UNAUTHORIZED"}` | token 无效 |

## 用法

```powershell
pip install requests
```

1. 把 `config.example.json` 复制成 `config.json`，填上自己的账号密码
2. 手动跑一次：`python checkin.py`
3. 打开 `checkin.log` 看结果

`config.json` 里是明文密码，**已加入 `.gitignore`，不要提交**。

## 开机自启（Windows）

`Win+R` 输入 `shell:startup` 打开启动文件夹，在里面新建 `checkin.vbs`：

```vbs
CreateObject("WScript.Shell").Run """<pythonw.exe 的路径>"" ""<checkin.py 的路径>""", 0, False
```

## 设计说明

- **每次运行都重新登录一次**，用一次登录换掉「token 过期怎么处理」的整套状态判断。
  代价是账号密码要留在本机。
- **网络重试**：开机瞬间网络常常还没通，所以最多重试 10 次、每次间隔 15 秒。
- **幂等**：签到接口有状态，重复调用只会返回 `CONFLICT`，脚本把它当成功处理。
