# douyin_live_status

通过抖音网页版获取抖音直播间状态 + 开播推送（配置化 + 健壮解析版）

> 原版发布于 2023-09，硬编码 `self.__pace_f.push` 的 `$L10` chunk 前缀。
> 抖音页面改版后该写法已失效（`list index out of range`）。
> 本版改为遍历全部 RSC flight chunk 递归定位 `roomInfo`，chunk 编号变化也能工作。

## 安装依赖

```bash
pip install requests beautifulsoup4
```

## 快速使用

```bash
python Main.py                 # 默认查询 J1an9u9u
python Main.py 主播抖音号      # 查询指定主播
```

或作为库引入：

```python
import Douyin

# 返回 dict
Douyin.query_live_status("J1an9u9u", is_target=False)

# 返回 Python 对象（元组，兼容旧版心跳）
Douyin.query_live_status("J1an9u9u", is_target=True)
```

返回 dict 字段：

| 字段 | 说明 |
| --- | --- |
| name | 主播昵称 |
| room_title | 直播间标题 |
| status | 2=直播中，4=未开播，0=未知 |
| room_view_stats | 在线人数显示文本 |
| position | 分区，如 `{竞技游戏}[第五人格]` |
| logo_url | 主播头像 / 封面 |
| url | 直播间链接 |
| view_total | 总观看人数文本 |
| like_count | 点赞数 |
| qr_url | 直播间二维码 |
| live_steam_url | FLV 拉流地址（直播中才有） |

## 配置文件 config.json

```json
{
  "accounts": ["J1an9u9u"],
  "heartbeat_interval": 10,
  "push_api": {
    "send_msg": "http://127.0.0.1:451/send_msg",
    "change_groupname": "http://127.0.0.1:451/change_groupname",
    "group_id": "000000000"
  }
}
```

- `accounts`：要监听的主播抖音号列表
- `heartbeat_interval`：心跳间隔（秒）
- `push_api`：开播推送接口（原为自写 QQ 机器人 API，可改成 onebot 标准接口）

## 开播推送

```python
import Douyin
Douyin.heartbeat()              # 读取 config.json，独立线程运行
Douyin.heartbeat("config.json") # 指定配置文件
Douyin.heartbeat(config_dict)   # 直接传 dict
```

监听逻辑：
- 每 `heartbeat_interval` 秒查询一次
- `status=2`（直播中）且未推送过 → 发送开播通知 + 改群名"推送姬-主播正在播呢"
- `status=4`（未开播）→ 复位推送标记，改群名"推送姬-主播已下播"

## 健壮性说明

- 解析不再依赖具体 chunk 编号（`$L10`/`$L11`/`$L12`），遍历全部 `self.__pace_f.push` 数据
- 字段全部 `.get()` 容错，缺字段不崩溃
- 请求失败 / 解析失败返回 `None` 并记日志，不抛裸异常
- 拉流地址不再硬编码 `HD1`，按 `HD1 → FULL_HD1 → SD1 → SD2 → 任意` 顺序取

## 免责声明

本程序仅用于学习和交流，一切有关抖音的商业用途与开发者无关。

## 系列说明

本仓库是「抖音解析系列」的成员之一，三件套共用同一套异步 API + 配置化 + 健壮解析模式：

| 仓库 | 用途 |
| --- | --- |
| [douyin_live_status](https://github.com/TeaBoss-Developer/douyin_live_status) | 直播间状态查询 + 开播推送（本仓库） |
| [douyin_vedio_info](https://github.com/TeaBoss-Developer/douyin_vedio_info) | 视频无水印直链解析 |
| [douyin_image_info](https://github.com/TeaBoss-Developer/douyin_image_info) | 图集（图文帖）无水印原图解析 |

各仓库均需配置 `config.json` 中的有效 Cookie（抖音风控会拦截未登录请求），Cookie 已被 .gitignore 排除，不会提交到仓库。
