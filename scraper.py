import asyncio
import aiohttp
import os
import logging
import time
from typing import List, Tuple

# 配置日志
logging.basicConfig(level=logging.INFO)

# 直播源列表
live_sources = [
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

# 创建目录
def create_directory(path: str):
    if not os.path.exists(path):
        os.makedirs(path)

# 下载直播源内容
async def download_live_source(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    content = await response.text()
                    return content
        except Exception as e:
            logging.error(f"无法下载 {url}: {e}")
    return ""

# 检测直播源响应时间
async def test_speed(url: str) -> bool:
    start_time = time.time()
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    elapsed_time = time.time() - start_time
                    return elapsed_time <= 5  # 如果响应时间小于等于5秒，视为有效源
        except Exception as e:
            logging.error(f"无法访问 {url}: {e}")
    return False

# 按分类下载和验证直播源
async def fetch_and_categorize_sources() -> List[Tuple[str, str]]:
    valid_sources = []

    for url in live_sources:
        logging.info(f"正在处理 {url}...")
        content = await download_live_source(url)
        if content:
            # 假设内容中包含直播源链接，处理内容
            sources = content.splitlines()
            for source in sources:
                if await test_speed(source):
                    valid_sources.append((url, source))

    return valid_sources

# 写入白名单/黑名单文件
def write_to_file(file_path: str, category_name: str, sources: List[Tuple[int, str]]):
    create_directory(os.path.dirname(file_path))
    with open(file_path, 'w') as f:
        f.write(f"{category_name},#genre#\n")
        for idx, (url, source) in enumerate(sources, start=1):
            f.write(f"{idx}{source}\n")
    logging.info(f"写入文件 {file_path} 完成.")

# 主流程
async def main():
    valid_sources = await fetch_and_categorize_sources()
    white_list = []
    black_list = []

    # 按照5秒响应时间判断，分配到白名单或黑名单
    for url, source in valid_sources:
        if await test_speed(source):
            white_list.append((url, source))
        else:
            black_list.append((url, source))

    # 白名单和黑名单的输出路径
    white_list_path = "white_list.txt"
    black_list_path = "black_list.txt"

    # 写入文件
    write_to_file(white_list_path, "日韩线路", white_list)
    write_to_file(black_list_path, "日韩线路", black_list)

# 运行主程序
if __name__ == "__main__":
    asyncio.run(main())
