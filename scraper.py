import aiohttp
import asyncio
import os
import logging
from datetime import datetime
import re
import subprocess
import sys

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 直播源接口列表
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

# 自动生成 requirements.txt 文件并写入依赖
def ensure_requirements_file():
    dependencies = [
        "aiohttp"
    ]
    
    if not os.path.exists("requirements.txt"):
        try:
            with open("requirements.txt", "w") as f:
                for dep in dependencies:
                    f.write(f"{dep}\n")
            logging.info("requirements.txt 文件已创建并写入依赖。")
        except Exception as e:
            logging.error(f"创建 requirements.txt 文件时出错：{e}")
            sys.exit(1)
    else:
        logging.info("requirements.txt 文件已存在，跳过创建。")

# 自动安装依赖
def install_requirements():
    ensure_requirements_file()  # 确保 requirements.txt 文件存在
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        logging.info("依赖已成功安装。")
    except subprocess.CalledProcessError as e:
        logging.error(f"安装依赖失败：{e}")
        sys.exit(1)

# 测试直播源响应时间
async def test_speed(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=TIMEOUT) as response:
                return response.status, response.url, response.elapsed.total_seconds()
    except Exception as e:
        logging.error(f"测试直播源 {url} 时出错：{e}")
        return None, url, None

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

# 解析网页内容并提取直播源
async def parse_live_sources(url):
    live_sources = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    # 假设直播源是直接在文本文件中的
                    lines = html.splitlines()
                    for line in lines:
                        line = line.strip()
                        if match_live_source(line):
                            live_sources.append(('未知频道', line))  # 没有频道名称时默认使用 '未知频道'
                    if not live_sources:
                        logging.warning(f"未找到任何符合条件的直播源，来自 {url}。")
                else:
                    logging.error(f"无法获取网页内容，来自 {url}，状态码：{response.status}")
    except Exception as e:
        logging.error(f"获取网页内容时出错，来自 {url}：{e}")
    
    return live_sources

# 根据响应时间分类
async def test_and_categorize(live_sources):
    white_list = []
    black_list = []
    
    # 调整任务列表，仅传递 URL 给 test_speed
    tasks = [test_speed(url) for _, url in live_sources]  # 只取 `url`
    results = await asyncio.gather(*tasks)
    
    for (name, url), (status, _, elapsed) in zip(live_sources, results):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 筛选出响应时间小于阈值的直播源（响应时间小于等于 2 秒的为有效）
        if status == 200 and elapsed is not None:
            if elapsed <= VALID_THRESHOLD:
                white_list.append(f"{name}, #{url}# , {elapsed}s, {timestamp}")
                logging.info(f"有效：{name} ({url}) 响应时间：{elapsed}s")
            else:
                black_list.append(f"{name}, #{url}# , {elapsed}s, {timestamp}")
                logging.warning(f"无效（响应过慢）：{name} ({url}) 响应时间：{elapsed}s")
        else:
            black_list.append(f"{name}, #{url}# , 无法访问, {timestamp}")
            logging.warning(f"无效（无法访问）：{name} ({url})")
    
    return white_list, black_list

# 保存白名单和黑名单到文件
def save_to_files(white_list, black_list, base_path="live_streams"):
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    
    white_file = os.path.join(base_path, "white_list.txt")
    black_file = os.path.join(base_path, "black_list.txt")
    
    with open(white_file, 'w', encoding='utf-8') as f:
        for line in white_list:
            f.write(line + "\n")
    
    with open(black_file, 'w', encoding='utf-8') as f:
        for line in black_list:
            f.write(line + "\n")
    
    logging.info(f"白名单保存至 {white_file}")
    logging.info(f"黑名单保存至 {black_file}")

# 主程序
async def main():
    install_requirements()  # 确保安装依赖

    live_sources = []
    
    # 获取每个 URL 的内容并提取直播源
    for url in URLS:
        logging.info(f"正在处理：{url}")
        sources = await parse_live_sources(url)
        live_sources.extend(sources)

    # 分类和筛选直播源
    white_list, black_list = await test_and_categorize(live_sources)

    # 保存白名单和黑名单
    save_to_files(white_list, black_list)

if __name__ == "__main__":
    asyncio.run(main())  # 执行主程序
