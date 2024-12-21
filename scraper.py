import aiohttp
import asyncio
import os
import logging
import re  # 用于正则匹配直播源链接
from datetime import datetime

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 目标URL列表 (替换为你的直播源接口)
URLS = [
    "http://175.178.251.183:6689/aktvlive.txt",
    "https://live.fanmingming.com/tv/m3u/ipv6.m3u",
    "https://raw.githubusercontent.com/yuanzl77/IPTV/main/直播/央视频道.txt",
    "http://120.79.4.185/new/mdlive.txt",
    "https://raw.githubusercontent.com/Fairy8o/IPTV/main/PDX-V4.txt",
    "https://raw.githubusercontent.com/Fairy8o/IPTV/main/PDX-V6.txt",
    "https://live.zhoujie218.top/tv/iptv6.txt",
    "https://live.zhoujie218.top/tv/iptv4.txt",
    "https://www.mytvsuper.xyz/m3u/Live.m3u",
    "https://tv.youdu.fan:666/live/",
    "http://ww.weidonglong.com/dsj.txt",
    "http://xhztv.top/zbc.txt",
    "https://raw.githubusercontent.com/qingwen07/awesome-iptv/main/tvbox_live_all.txt",
    "https://raw.githubusercontent.com/Guovin/TV/gd/output/result.txt",
    "http://home.jundie.top:81/Cat/tv/live.txt",
    "https://raw.githubusercontent.com/vbskycn/iptv/master/tv/hd.txt",
    "https://cdn.jsdelivr.net/gh/YueChan/live@main/IPTV.m3u",
    "https://raw.githubusercontent.com/cymz6/AutoIPTV-Hotel/main/lives.txt",
    "https://raw.githubusercontent.com/PizazzGY/TVBox_warehouse/main/live.txt",
    "https://fm1077.serv00.net/SmartTV.m3u",
    "https://raw.githubusercontent.com/ssili126/tv/main/itvlist.txt",
    "https://raw.githubusercontent.com/kimwang1978/collect-tv-txt/main/merged_output.txt"
]

TIMEOUT = 5  # 请求超时时间（秒）
VALID_THRESHOLD = 2  # 响应时间阈值，2秒以内视为有效

# 正则表达式用于匹配直播源格式（http, rtmp, p3p, rtp 等）
def match_live_source(url):
    patterns = [
        r'http://',  # http
        r'rtmp://',  # rtmp
        r'p3p://',   # p3p
        r'rtsp://',  # rtsp
        r'rtp://',   # rtp
        r'p2p://'    # p2p
    ]
    
    for pattern in patterns:
        if re.match(pattern, url):
            return True
    return False

# 获取网页内容并解析直播源
async def fetch_live_sources(url):
    live_sources = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    logging.info(f"爬取到的内容：{html[:1000]}")  # 打印前1000个字符进行调试
                    # 假设直播源是直接在文本文件中的
                    lines = html.splitlines()
                    for line in lines:
                        line = line.strip()
                        if match_live_source(line):
                            live_sources.append(('未知频道', line))  # 没有频道名称时默认使用 '未知频道'
                            logging.info(f"发现直播源：{line} 来自 {url}")
                else:
                    logging.error(f"无法获取网页内容，来自 {url}，状态码：{response.status}")
    except Exception as e:
        logging.error(f"获取网页内容时出错，来自 {url}：{e}")
    
    return live_sources

# 测试直播源响应时间
async def test_speed(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=TIMEOUT) as response:
                return response.status, response.url, response.elapsed.total_seconds()
    except Exception as e:
        logging.error(f"测试直播源 {url} 时出错：{e}")
        return None, url, None

# 根据响应时间分类
async def test_and_categorize(live_sources):
    white_list = []
    black_list = []
    
    tasks = [test_speed(url) for _, url in live_sources]
    results = await asyncio.gather(*tasks)
    
    for (name, url), (status, _, elapsed) in zip(live_sources, results):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if status == 200 and elapsed is not None:
            logging.info(f"直播源 {url} 的响应时间：{elapsed}s")
            if elapsed <= VALID_THRESHOLD:
                white_list.append(f"{name}, #genre# , {url}, {elapsed}s, {timestamp}")
                logging.info(f"有效：{name} ({url}) 响应时间：{elapsed}s")
            else:
                black_list.append(f"{name}, #genre# , {url}, {elapsed}s, {timestamp}")
                logging.warning(f"无效（响应过慢）：{name} ({url}) 响应时间：{elapsed}s")
        else:
            black_list.append(f"{name}, #genre# , {url}, 无法访问, {timestamp}")
            logging.warning(f"无效（无法访问）：{name} ({url})")
    
    return white_list, black_list

# 自动创建文件夹
def create_folders(base_path="live_streams"):
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    
    subfolders = ["white_list", "black_list"]
    for folder in subfolders:
        folder_path = os.path.join(base_path, folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            logging.info(f"创建文件夹：{folder_path}")

# 保存白名单和黑名单到文件
def save_to_files(white_list, black_list, base_path="live_streams"):
    create_folders(base_path)
    
    # 保存白名单
    white_file = os.path.join(base_path, "white_list", "white_list.txt")
    with open(white_file, 'w', encoding='utf-8') as f:
        for line in white_list:
            f.write(line + "\n")
    logging.info(f"白名单保存至 {white_file}")
    
    # 保存黑名单
    black_file = os.path.join(base_path, "black_list", "black_list.txt")
    with open(black_file, 'w', encoding='utf-8') as f:
        for line in black_list:
            f.write(line + "\n")
    logging.info(f"黑名单保存至 {black_file}")

# 主程序
async def main():
    all_live_sources = []
    for url in URLS:
        live_sources = await fetch_live_sources(url)
        all_live_sources.extend(live_sources)

    if not all_live_sources:
        logging.warning("未发现任何有效的直播源。")
        return

    white_list, black_list = await test_and_categorize(all_live_sources)
    save_to_files(white_list, black_list)

# 启动爬虫程序
if __name__ == "__main__":
    asyncio.run(main())
