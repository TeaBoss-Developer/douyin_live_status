# douyin_live_status
Get the information and status of the Douyin live room through the Douyin web page

通过抖音网页版获取抖音直播间状态
抖音直播推送

首先引入Douyin库(目录下)
import Douyin
在Douyin库下有几个有用的函数
def query_live_status

def clear

def heartbeat

query_live_status使用方法:
Douyin.query_live_status("主播抖音号"[str],是否为Python对象[bool])
例:
Douyin.query_live_status("J1an9u9u",True)#返回Python对象

('[J1an9u9u]缄啾啾', '少萝', 2, '338在线观众\n最大人数记录:1万+观众\n点赞数:18588', '{竞技游戏}[第五人格]', 'https://p6-webcast-sign.douyinpic.com/image-cut-tos-priv/d918975991c0445276308bb2dd43a7bf~tplv-qz53dukwul-common-resize:0:0.image?biz_tag=10&classify=10&from=webcast.room.pack&scene_tag=enter_room&x-expires=1698639788&x-signature=8meIPjzJk0ZQxC3%2F8tKznBOYiCo%3D', 'https://live.douyin.com/J1an9u9u\n(qr_url:https://p3-pc.douyinpic.com/img/aweme-qrcode/wBMLzF7284447748588341004~c5_720x720.webp?from=746027608)\n最佳视频推送流:http://pull-flv-l11.douyincdn.com/third/stream-7284447477145635584_hd5.flv?expire=1696652588&sign=92e97a376cf01ced0f62a19a71c9abb3')

Douyin.query_live_status("J1an9u9u",False)#返回json对象

{'name': '[J1an9u9u]缄啾啾', 'room_title': '少萝', 'status': 2, 'room_view_stats': '337在线观众', 'position': '{竞技游戏}[第五人格]', 'logo_url': 'https://p6-webcast-sign.douyinpic.com/image-cut-tos-priv/d918975991c0445276308bb2dd43a7bf~tplv-qz53dukwul-common-resize:0:0.image?biz_tag=10&classify=10&from=webcast.room.pack&scene_tag=enter_room&x-expires=1698639789&x-signature=oJtE73PT5DisLExhvmdj4SjSsfU%3D', 'url': 'https://live.douyin.com/J1an9u9u', 'view_total': '1万+观众', 'like_count': 18588, 'qr_url': 'https://p3-pc.douyinpic.com/img/aweme-qrcode/wBMLzF7284447748588341004~c5_720x720.webp?from=746027608', 'live_steam_url': 'http://pull-flv-l11.douyincdn.com/third/stream-7284447477145635584_hd5.flv?expire=1696652589&sign=01616d258885ac3f8a16c654dff11982'}

clear使用方法:
ps:这个是用来在Windows以及Linux清屏的指令

例:clear()

heartbeat介绍及使用方法:
这个本来是我用来机器人推送直播的函数
他继承了@async_fun
所以直接单独线程进行检测和推送
10s一次心跳
http://127.0.0.1:451/send_msg    #发送群消息
http://127.0.0.1:451/change_groupname     #更改群名称
这俩API是我自写的,可以改成onebot标准的那种的API.
基本上没有误报和漏报

PS:Douyin.py的第五十一行
self.__pace_f.push([1,\"a:[\\\"$\\\",\\\"$L11\\\",null,
这个$L11可能会变,后期检测变了会更新.

使用须知:本程序仅用于学习和交流,一切有关douyin的商业用途,与开发者无关.
