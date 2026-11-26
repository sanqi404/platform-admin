"""审计辅助：客户端 IP / UA 解析 / 敏感参数脱敏 / 操作语义推断。

不引入第三方 UA 库，用最小规则集覆盖运维场景常见客户端
（浏览器、curl、python-requests、Postman、运维脚本），保证离线可用。
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

# --------------------------------------------------------------------------- #
# IP
# --------------------------------------------------------------------------- #
_PRIVATE_PREFIX = ("10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.2",
                   "172.30.", "172.31.", "192.168.", "100.64.", "fd00:", "fe80:")
_LOOPBACK = {"127.0.0.1", "::1", "localhost", "0.0.0.0"}


def client_ip(request) -> str:
    """取真实客户端 IP：代理优先 X-Forwarded-For 首个地址，其次 X-Real-IP。"""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    return request.client.host if request.client else "unknown"


def ip_region(ip: str) -> str:
    """网段归属判定（不做外部 geo 查询，内网环境也准确）。"""
    if not ip:
        return "未知"
    if ip in _LOOPBACK:
        return "本机"
    if ip.startswith(_PRIVATE_PREFIX):
        return "内网"
    if ip.startswith("169.254."):
        return "链路本地"
    return "公网"


# --------------------------------------------------------------------------- #
# UA 解析
# --------------------------------------------------------------------------- #
_OS_RULES: list[tuple[str, str]] = [
    (r"Windows NT 10\.0", "Windows 10/11"),
    (r"Windows NT 6\.3", "Windows 8.1"),
    (r"Windows NT 6\.1", "Windows 7"),
    (r"Windows", "Windows"),
    (r"iPhone|iPad|iPod", "iOS"),
    (r"Android[ /]?([\d.]+)", "Android"),
    (r"Mac OS X", "macOS"),
    (r"CrOS", "ChromeOS"),
    (r"Ubuntu", "Ubuntu"),
    (r"Kylin|kylin", "Kylin"),
    (r"openEuler|openeuler", "openEuler"),
    (r"Linux", "Linux"),
]

_BROWSER_RULES: list[tuple[str, str]] = [
    (r"Edg(?:e|A|iOS)?/([\d.]+)", "Edge"),
    (r"OPR/([\d.]+)", "Opera"),
    (r"Firefox/([\d.]+)", "Firefox"),
    (r"Chrome/([\d.]+)", "Chrome"),
    (r"Version/([\d.]+).*Safari", "Safari"),
    (r"Safari/([\d.]+)", "Safari"),
    (r"curl/([\d.]+)", "curl"),
    (r"python-requests/([\d.]+)", "python-requests"),
    (r"python-httpx/([\d.]+)", "httpx"),
    (r"Go-http-client/([\d.]+)", "Go-http-client"),
    (r"PostmanRuntime/([\d.]+)", "Postman"),
    (r"okhttp/([\d.]+)", "OkHttp"),
]


def parse_ua(ua: Optional[str]) -> tuple[str, str, str]:
    """返回 (操作系统, 浏览器/客户端, 设备类型)。"""
    if not ua:
        return "未知", "未知", "未知"

    os_name = "未知"
    for pattern, name in _OS_RULES:
        if re.search(pattern, ua, re.I):
            os_name = name
            break

    browser = "未知"
    for pattern, name in _BROWSER_RULES:
        m = re.search(pattern, ua, re.I)
        if m:
            ver = m.group(1) if m.groups() else ""
            browser = f"{name} {ver}".strip() if ver else name
            break
    if browser == "未知" and ua:
        token = ua.split("/")[0].strip()
        browser = token[:32] if token else "未知"

    lowered = ua.lower()
    if any(k in lowered for k in ("curl", "python-requests", "python-httpx",
                                  "go-http-client", "postmanruntime", "okhttp", "java/")):
        device = "程序调用"
    elif any(k in lowered for k in ("iphone", "android", "ipad", "mobile")):
        device = "移动端"
    elif any(k in lowered for k in ("ipad", "tablet")):
        device = "平板"
    else:
        device = "PC"

    return os_name, browser, device


# --------------------------------------------------------------------------- #
# 参数脱敏
# --------------------------------------------------------------------------- #
_SENSITIVE_KEYS = {
    "password", "old_password", "new_password", "password_hash", "pwd", "passwd",
    "secret", "token", "access_token", "refresh_token", "api_key", "apikey",
    "private_key", "credential", "authorization",
}
_MASK = "******"
_MAX_PARAM_LEN = 4000


def _mask_obj(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in _SENSITIVE_KEYS:
                out[k] = _MASK
            else:
                out[k] = _mask_obj(v)
        return out
    if isinstance(obj, list):
        return [_mask_obj(x) for x in obj]
    return obj


def mask_params(raw: bytes | str | None) -> Optional[str]:
    """请求体脱敏后序列化；超长截断，保证日志可读且不落敏感值。"""
    if not raw:
        return None
    if isinstance(raw, bytes):
        try:
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            return "<二进制内容>"
    else:
        text = raw
    text = text.strip()
    if not text:
        return None

    try:
        data = json.loads(text)
    except Exception:
        if len(text) > _MAX_PARAM_LEN:
            return text[:_MAX_PARAM_LEN] + "...(已截断)"
        return text

    masked = _mask_obj(data)
    try:
        dumped = json.dumps(masked, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        dumped = str(masked)
    if len(dumped) > _MAX_PARAM_LEN:
        dumped = dumped[:_MAX_PARAM_LEN] + "...(已截断)"
    return dumped


# --------------------------------------------------------------------------- #
# 操作语义推断
# --------------------------------------------------------------------------- #
# 路径首段 → 业务模块中文名
MODULE_MAP: dict[str, str] = {
    "auth": "认证",
    "users": "用户管理",
    "roles": "角色权限",
    "menus": "菜单管理",
    "permissions": "权限点",
    "tenants": "租户管理",
    "logs": "日志审计",
    "depts": "部门管理",
}

# 路径首段 → 用于拼接动作的资源简称（新增用户 / 删除角色）
RESOURCE_MAP: dict[str, str] = {
    "users": "用户", "roles": "角色", "menus": "菜单", "tenants": "租户",
    "depts": "部门", "logs": "日志", "permissions": "权限", "auth": "账号",
}

MODULE_TO_RESOURCE: dict[str, str] = {v: RESOURCE_MAP.get(k, v) for k, v in MODULE_MAP.items()}

# (method, 路径关键字) → (动作码, 动作中文)
_ACTION_RULES: list[tuple[str, Optional[str], str, str]] = [
    ("POST", "login", "login", "登录"),
    ("POST", "logout", "logout", "退出登录"),
    ("POST", "refresh", "refresh", "刷新令牌"),
    ("PUT", "/password", "reset_password", "重置密码"),
    ("POST", "/password", "reset_password", "重置密码"),
    ("PUT", "/grants", "grant", "分配权限"),
    ("PUT", "/roles", "assign_role", "分配角色"),
    ("GET", "export", "export", "导出数据"),
    ("POST", "export", "export", "导出数据"),
    ("POST", "", "create", "新增"),
    ("PUT", "", "update", "更新"),
    ("PATCH", "", "update", "更新"),
    ("DELETE", "", "delete", "删除"),
]

_ACTION_EN: dict[str, str] = {
    "新增": "create", "更新": "update", "删除": "delete",
    "分配权限": "grant", "分配角色": "assign_role", "重置密码": "reset_password",
    "导出数据": "export", "登录": "login", "退出登录": "logout", "刷新令牌": "refresh",
}


def resolve_action(method: str, path: str) -> tuple[str, str]:
    """返回 (动作码, 中文动作)。中文动作后续会拼上模块名，如「新增用户」。"""
    method = method.upper()
    lower = path.lower()
    for m, kw, code, label in _ACTION_RULES:
        if m != method:
            continue
        if kw is None or kw in lower:
            return code, label
    return "other", "访问"


def resolve_module(path: str) -> str:
    """从 /api/v1/users/3 这类路径取业务模块名。"""
    parts = [p for p in path.split("/") if p and p not in ("api", "v1")]
    if not parts:
        return "系统"
    return MODULE_MAP.get(parts[0], parts[0])


def resolve_target(path: str) -> str:
    """提取路径中的资源标识，形如 users/3/password → 用户管理 #3。"""
    parts = [p for p in path.split("/") if p and p not in ("api", "v1")]
    if not parts:
        return ""
    resource = parts[0]
    nums = [p for p in parts[1:] if p.isdigit()]
    sub = [p for p in parts[1:] if not p.isdigit()]
    target = RESOURCE_MAP.get(resource, resource)
    if nums:
        target = f"{target} #{nums[0]}"
    if sub:
        tail = sub[-1]
        if tail not in ("password", "grants", "tree", "refresh", "logout"):
            target = f"{target}/{tail}"
        else:
            target = f"{target}.{tail}"
    return target[:255]


def compose_action_label(module: str, action_label: str) -> str:
    """拼出人可读动作描述：新增 + 用户管理 → 新增用户；分配权限 + 角色权限 → 分配权限给角色。"""
    noun = MODULE_TO_RESOURCE.get(module, module)
    if action_label in ("登录", "退出登录", "刷新令牌", "访问"):
        return action_label if action_label != "访问" else f"访问{module}"
    if action_label == "分配权限":
        return f"分配权限给{noun}"
    if action_label == "分配角色":
        return f"分配角色给{noun}"
    if action_label == "重置密码":
        return f"重置{noun}密码"
    if action_label == "导出数据":
        return f"导出{noun}数据"
    return f"{action_label}{noun}"
