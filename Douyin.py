# -*- coding: utf-8 -*-
"""
Douyin.py - 抖音直播间信息获取（配置化 + 健壮解析版）

核心改进（对比旧版）：
1. 不再硬编码 self.__pace_f 的 chunk 前缀（旧版写死 "$L10"，抖音改版即失效）
2. 遍历页面所有 RSC flight chunk，递归定位 roomInfo，chunk 编号变化也能工作
3. 配置化：主播列表、推送 API、心跳间隔全部由 config.json 控制
4. 更健壮的错误处理：解析失败返回 None + 错误原因，不抛裸异常
5. 字段解析全部走 .get() 容错，缺字段不崩溃

依赖：requests, beautifulsoup4（可通过 pip install requests beautifulsoup4 安装）

用法：
    import Douyin
    Douyin.query_live_status("主播抖音号", is_target=True)  # 返回 Python 对象
    Douyin.query_live_status("主播抖音号", is_target=False) # 返回 dict

    Douyin.heartbeat(config)  # 开播推送（独立线程），config 为 dict
"""
import json
import logging
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional, Union

import requests
from bs4 import BeautifulSoup

import util

# ---------- 日志 ----------
logger = logging.getLogger("Douyin")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)

# ---------- 常量 ----------
LIVE_URL_TEMPLATE = "https://live.douyin.com/{account}?my_ts={ts}"
STATUS_LIVE = 2          # 直播中
STATUS_NOT_LIVE = 4      # 未开播
STATUS_UNKNOWN = 0       # 未知/解析失败


def get_headers_for_live() -> Dict[str, str]:
    """浏览器请求头，降低被风控概率"""
    return {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
        'accept-encoding': 'gzip, deflate',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-site',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
    }


def clear() -> None:
    """Windows / Linux 清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')


# ---------- 健壮解析核心 ----------

def _extract_flight_chunks(html_text: str) -> List[Any]:
    """
    从页面 HTML 中提取所有 RSC flight chunk 并解析为 Python 对象。

    抖音网页版通过 `self.__pace_f.push([1,"...JSON..."])` 注入数据，
    JSON 前缀形如 "d:["$","$L12",null,{...}]"（chunk 编号会变）。
    这里遍历所有 chunk，不依赖具体编号。
    """
    chunks: List[Any] = []
    pattern = re.compile(r'self\.__pace_f\.push\(\[1,"(.*?)"\]\)', re.S)
    for m in pattern.finditer(html_text):
        raw = m.group(1)
        try:
            decoded = json.loads('"' + raw + '"')  # 反转义 \" 和 \\
        except Exception:
            continue
        # 去掉前缀编号，如 "d:" / "2:"
        m2 = re.match(r'^[0-9a-zA-Z]+:(.*)$', decoded, re.S)
        if not m2:
            continue
        body = m2.group(1)
        # 跳过模块引用型 chunk（形如 I{...}）
        if body.startswith('I{'):
            continue
        try:
            data = json.loads(body)
            chunks.append(data)
        except Exception:
            continue
    return chunks


def _deep_find(obj: Any, key: str, max_depth: int = 8, _depth: int = 0) -> List[Any]:
    """递归查找 dict/list 中所有名为 key 的值，返回列表"""
    results: List[Any] = []
    if _depth > max_depth:
        return results
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                results.append(v)
            results.extend(_deep_find(v, key, max_depth, _depth + 1))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(_deep_find(item, key, max_depth, _depth + 1))
    return results


def _extract_room_info(html_text: str) -> Optional[Dict[str, Any]]:
    """
    从页面提取 roomInfo 字典（包含 room / anchor / web_stream_url 等）。
    遍历所有 chunk，找到第一个结构完整的 roomInfo。
    """
    for data in _extract_flight_chunks(html_text):
        for room_info in _deep_find(data, "roomInfo"):
            if not isinstance(room_info, dict):
                continue
            room = room_info.get("room")
            anchor = room_info.get("anchor")
            # 校验：room 和 anchor 都存在且 room 有 id_str 才算有效
            if (isinstance(room, dict) and isinstance(anchor, dict)
                    and room.get("id_str")):
                return room_info
    return None


# ---------- 字段提取 ----------

def _safe_get(d: Optional[dict], *keys: str, default: Any = None) -> Any:
    """安全地逐级取 dict 值"""
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _get_partition(room_info: Dict[str, Any]) -> str:
    """解析分区：{大类}[小类]"""
    prm = room_info.get("partition_road_map") or {}
    big = _safe_get(prm, "partition", "title", default="")
    small = _safe_get(prm, "sub_partition", "partition", "title", default="")
    return "{" + str(big) + "}" + "[" + str(small) + "]"


def _get_logo_url(room_info: Dict[str, Any]) -> str:
    """获取主播头像（优先 room.cover，其次 anchor.avatar_thumb）"""
    cover = _safe_get(room_info, "room", "cover", "url_list", default=None)
    if isinstance(cover, list) and cover:
        return cover[0]
    thumb = _safe_get(room_info, "anchor", "avatar_thumb", "url_list", default=None)
    if isinstance(thumb, list) and thumb:
        return thumb[0]
    return ""


def _get_stream_url(room_info: Dict[str, Any]) -> Optional[str]:
    """
    获取直播拉流地址（flv_pull_url 各清晰度中取第一个可用）。
    旧版硬编码取 HD1，新版兼容多种 key。
    """
    flv = _safe_get(room_info, "web_stream_url", "flv_pull_url", default=None)
    if not isinstance(flv, dict):
        return None
    for prefer in ("HD1", "FULL_HD1", "SD1", "SD2"):
        if flv.get(prefer):
            return flv[prefer]
    for v in flv.values():
        if isinstance(v, str) and v:
            return v
    return None


def query_live_status(user_account: Optional[str] = None,
                      is_target: bool = False) -> Union[Dict[str, Any], tuple, None]:
    """
    查询直播间状态。

    :param user_account: 主播抖音号（如 "J1an9u9u"）
    :param is_target: True 返回 (name, room_title, status, view_stats, position,
                       logo_url, url) 元组（兼容旧版心跳）；False 返回 dict
    :return: dict / tuple / None（解析失败）
    """
    if not user_account:
        return None

    query_url = LIVE_URL_TEMPLATE.format(account=user_account, ts=int(time.time()))
    response = util.requests_get(query_url, '查询直播间状态',
                                 headers=get_headers_for_live(), timeout=15)

    if not util.check_response_is_ok(response):
        logger.warning("请求失败 status=%s url=%s",
                       getattr(response, 'status_code', None), query_url)
        return None

    try:
        room_info = _extract_room_info(response.text)
    except Exception as e:
        logger.error("页面解析异常: %s", e)
        return None

    if room_info is None:
        logger.warning("未能从页面中提取到 roomInfo（页面结构可能又变了）: %s", user_account)
        return None

    room = room_info.get("room") or {}
    anchor = room_info.get("anchor") or {}
    nickname = anchor.get("nickname", user_account)
    room_title = room.get("title", "")
    status = room.get("status", STATUS_UNKNOWN)

    like_count = room.get("like_count", 0)
    user_count = room.get("user_count_str", "0")

    if status == STATUS_LIVE:
        room_view_stats = f"{user_count}在线观众"
        view_total = f"{user_count}观众"
    elif status == STATUS_NOT_LIVE:
        room_view_stats = "未开播,无记录."
        view_total = "未开播,无记录."
    else:
        room_view_stats = "状态未知."
        view_total = "状态未知."

    position = _get_partition(room_info)
    logo_url = _get_logo_url(room_info)
    qr_url = str(room_info.get("qrcode_url") or "")
    stream_url = _get_stream_url(room_info) or ""

    room_url = f"https://live.douyin.com/{user_account}"

    if not is_target:
        return {
            "name": "[" + user_account + "]" + nickname,
            "room_title": room_title,
            "status": status,
            "room_view_stats": room_view_stats,
            "position": position,
            "logo_url": logo_url,
            "url": room_url,
            "view_total": str(view_total),
            "like_count": like_count,
            "qr_url": qr_url,
            "live_steam_url": stream_url,
        }
    else:
        return (
            "[" + user_account + "]" + nickname,
            room_title,
            status,
            room_view_stats + "\n最大人数记录:" + str(view_total) + "\n点赞数:" + str(like_count),
            position,
            logo_url,
            room_url + "\n(qr_url:" + str(qr_url) + ")" + "\n最佳视频推送流:" + stream_url,
        )


# ---------- 心跳推送 ----------

def async_fun(f):
    """把函数丢进独立线程执行，返回线程 id"""
    def wrapper(*args, **kwargs):
        thrd = threading.Thread(target=f, args=args, kwargs=kwargs)
        thrd.start()
        return thrd.ident
    return wrapper


def _load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """加载配置文件，缺失时返回默认配置"""
    defaults = {
        "accounts": ["J1an9u9u"],
        "heartbeat_interval": 10,
        "push_api": {
            "send_msg": "http://127.0.0.1:451/send_msg",
            "change_groupname": "http://127.0.0.1:451/change_groupname",
            "group_id": "000000000",
        },
    }
    if not os.path.exists(config_path):
        logger.warning("配置文件 %s 不存在，使用默认配置", config_path)
        return defaults
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        # 合并默认值，保证字段完整
        for k, v in defaults.items():
            cfg.setdefault(k, v)
        if isinstance(cfg.get("push_api"), dict):
            for k, v in defaults["push_api"].items():
                cfg["push_api"].setdefault(k, v)
        return cfg
    except Exception as e:
        logger.error("读取配置失败: %s，使用默认配置", e)
        return defaults


def _post(url: str, data: Dict[str, Any]) -> Optional[requests.Response]:
    """POST 推送，失败不抛异常"""
    try:
        return requests.post(url, data=data, timeout=5)
    except Exception as e:
        logger.warning("推送失败 %s: %s", url, e)
        return None


@async_fun
def heartbeat(config: Optional[Union[str, Dict[str, Any]]] = None,
              account: Optional[str] = None) -> Optional[int]:
    """
    开播心跳推送：监听主播，开播时向 QQ 机器人 API 推送开播通知。

    :param config: 配置 dict 或配置文件路径；None 时自动加载 ./config.json
    :param account: 指定监听的主播；None 时取配置中第一个
    """
    if isinstance(config, str) or config is None:
        cfg = _load_config(config if isinstance(config, str) else "config.json")
    else:
        cfg = config

    accounts = cfg.get("accounts") or ["J1an9u9u"]
    if account:
        accounts = [account]
    if not accounts:
        logger.error("没有配置任何主播账号")
        return None

    interval = int(cfg.get("heartbeat_interval", 10))
    api = cfg.get("push_api") or {}
    send_url = api.get("send_msg", "http://127.0.0.1:451/send_msg")
    rename_url = api.get("change_groupname", "http://127.0.0.1:451/change_groupname")
    group_id = api.get("group_id", "000000000")

    flag_live = False      # 是否已推送过开播通知（去重）
    name_flag = False      # 群名恢复标记
    live_name = "推送姬-主播正在播呢"
    off_name = "推送姬-主播已下播"

    logger.info("心跳启动: 监听 %s，间隔 %ss，推送 %s", accounts, interval, send_url)

    while True:
        time.sleep(interval)
        try:
            for acct in accounts:
                result = query_live_status(acct, is_target=True)
                if result is None:
                    continue
                name, title, status, persons, position, logo_url, live_url = result
                if "?" in position:
                    continue
                logger.info("[心跳] %s status=%s 标题=%s", name, status, title)

                if status == STATUS_LIVE:
                    if not flag_live:
                        _post(send_url, {
                            "group_id": group_id,
                            "content": "[@all]\n(url:" + str(logo_url) + ")\n"
                                       + str(name) + "开播啦~\n"
                                       + "今日标题:" + str(title) + "\n"
                                       + "分区为:" + str(position) + "\n"
                                       + "人数:" + str(persons) + "\n"
                                       + "直播间链接:" + str(live_url),
                        })
                        _post(rename_url, {"group_id": group_id, "content": live_name})
                        flag_live = True
                        name_flag = False
                elif status == STATUS_NOT_LIVE:
                    flag_live = False
                    if not name_flag:
                        _post(rename_url, {"group_id": group_id, "content": off_name})
                        name_flag = True
                else:
                    continue
        except Exception as e:
            logger.error("心跳循环异常: %s", e)
            continue


# 兼容旧版命名：heart_beat = heartbeat
heart_beat = heartbeat


if __name__ == "__main__":
    # 命令行直接测试：python Douyin.py 主播号
    import sys
    acct = sys.argv[1] if len(sys.argv) > 1 else "J1an9u9u"
    print(json.dumps(query_live_status(acct, is_target=False),
                     ensure_ascii=False, indent=2))
