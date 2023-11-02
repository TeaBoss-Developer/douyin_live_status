# @Time    : 2023.09.04 22:39
# @Author  : TeaBoss
# @File    : Douyin.py
# @Software: 抖音直播间信息获取
import util  
from bs4 import BeautifulSoup
import json
import time
import threading
import requests
import os
flag_live = False
gb_fq=""
gb_zfq=""
name_flag = False
def get_headers_for_live():
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
def clear():
    os.system('cls' if os.name == 'nt' else 'clear')
def query_live_status(user_account=None,is_target=False):
    global gb_fq
    global gb_zfq
    if user_account is None:
        return
    query_url = 'https://live.douyin.com/{}?my_ts={}'.format(user_account, int(time.time()))
    headers = get_headers_for_live()
    response = util.requests_get(query_url, '查询直播间状态', headers=headers, use_proxy=True)
    result={}
    where = []
    if util.check_response_is_ok(response):
        html_text = response.text
        try:
            soup = BeautifulSoup(html_text, "html.parser")
            scripts = soup.findAll('script')
            result = None
            a=0
            for i in scripts:
                a+=1
                if(user_account in str(i.string)):
                    where.append(a-1)
            result = json.loads(str(str(str(scripts[where[len(where)-1]].string).split("]\\n\"])")[0]).split("self.__pace_f.push([1,\"a:[\\\"$\\\",\\\"$L10\\\",null,")[1]).replace("\\\"","\"").replace("\\\\","\\"))
        except Exception as e:
            print("错误1触发",str(e))
            return(None,None,0,None,None,None,None)
        try:
            room_info = result["state"]["roomStore"]["roomInfo"]
            room = room_info.get('room')
            name = room_info['anchor']['nickname']
            room_title = room['title']
            like_count=room['like_count']
            status = room.get("status")
            if(status == 2):
                room_view_stats = room['room_view_stats']['display_long']
                view_total=room.get("stats")['total_user_str']+"观众"
                头像URL = room_info.get("room")["cover"]['url_list'][0]
                qr = room_info['qrcode_url']
                liu=room_info["web_stream_url"]['flv_pull_url'].get("HD1")
            elif(status == 4):
                room_view_stats = "未开播,无记录."
                view_total="未开播,无记录."
                头像URL = "https://p11.douyinpic.com/aweme/100x100/aweme-avatar/tos-cn-i-0813_dc845b3fb60a424f8955c2a22111f407.jpeg?from=3067671334"
                qr="暂无"
                liu="暂无"
            partition_road_map = room_info["partition_road_map"]
            if(str(partition_road_map) == "{}"):
                big = "?{}?".format(gb_fq)
                small = "?{}?".format(gb_zfq)
            else:
                big = partition_road_map.get("partition").get("title")
                small = partition_road_map.get("sub_partition").get("partition").get("title")
                gb_fq=big
                gb_zfq=small
            
            if(not is_target):
                return({"name":"["+user_account+"]"+name,"room_title":room_title,"status":status,"room_view_stats":room_view_stats,"position":"{"+big+"}"+"["+small+"]","logo_url":头像URL,"url":"https://live.douyin.com/"+user_account,"view_total":str(view_total),"like_count":like_count,"qr_url":str(qr),"live_steam_url":liu})
            else:
                return("["+user_account+"]"+name,room_title,status,room_view_stats+"\n最大人数记录:"+str(view_total)+"\n点赞数:"+str(like_count),"{"+big+"}"+"["+small+"]",头像URL,"https://live.douyin.com/"+user_account+"\n(qr_url:"+str(qr)+")"+"\n最佳视频推送流:"+liu)
        except:
            print("错误2触发")
            file = open("waring.log","w",encoding='utf-8')
            file.write(str(result))
            file.close()
            return(None,None,None,None,None,None,None)
def async_fun(f):
    def wrapper(*args, **kwargs):
        thrd = threading.Thread(target=f, args=args, kwargs=kwargs)
        thrd.start()
        return(thrd.ident)
    return wrapper
@async_fun
def heart_beat():#推送,可以根据自己的需求更改.
    global flag_live
    name_flag=False
    while(True):
        time.sleep(10)
        clear()
        try:
            name,title,status,persons,position,logo_url,live_url = query_live_status("J1an9u9u",True)
            if("?" in position):
                continue
        except:
            continue
        print("心跳了一下"+"\n[推送预览-状态:"+str(status)+"]\n(url:"+str(logo_url)+")\n"+str(name)+"在播吗?\n"+"今日标题:"+str(title)+"\n分区为:"+str(position)+"\n人数:"+str(persons)+"\n直播间链接:"+str(live_url))
        file = open("heartbeat.log","w",encoding='utf-8')
        if(status==2):
            file.write("[推送预览-抖音推送状态:"+str(status)+"]\n(url:"+str(logo_url)+")\n"+str(name)+"正在播呢! :>\n"+"今日标题:"+str(title)+"\n分区为:"+str(position)+"\n人数:"+str(persons)+"\n直播间链接:"+str(live_url))
        if(status==4):
            file.write("[推送预览-抖音推送状态:"+str(status)+"]\n(url:"+str(logo_url)+")\n"+str(name)+"还没开播呢:(\n"+"今日标题:"+str(title)+"\n分区为:"+str(position)+"\n人数:"+str(persons)+"\n直播间链接:"+str(live_url))
        file.close()
        if(status == 2):
            if(flag_live == False):
                url = "http://127.0.0.1:451/send_msg"
                data = {
                    "group_id": "000000000",
                    "content": "[@all]\n(url:"+str(logo_url)+")\n"+str(name)+"开播啦~\n"+"今日标题:"+str(title)+"\n分区为:"+str(position)+"\n人数:"+str(persons)+"\n直播间链接:"+str(live_url)
                }
                response = requests.post(url, data=data)
                print("推送结果:"+response.text)
                url = "http://127.0.0.1:451/change_groupname"
                data = {
                    "group_id": "000000000",
                    "content": "推送姬-主播正在播呢"
                }
                response = requests.post(url, data=data)
                name_flag=False
                flag_live = True
            else:
                continue
        if(status == 4):
            flag_live = False
            if(not name_flag):
                url = "http://127.0.0.1:451/change_groupname"
                data = {
                    "group_id": "000000000",
                    "content": "推送姬-主播正在播呢"
                }
                response = requests.post(url, data=data)
                name_flag=True
            else:
                continue
            continue
        if(status == 0):
            continue
        continue
#heart_beat()

