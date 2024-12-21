import asyncio
import aiohttp
import os
import logging
import time

# 配置日志
logging.basicConfig(level=logging.INFO)

# 单个直播源接口
live_source_url = "https://fm1077.serv00.net/SmartTV.m3u"

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

# 处理直播源并分类
async def fetch_and_categorize_sources() -> list:
    valid_sources = []

    # 获取直播源内容
    content = await download_live_source(live_source_url)
    if content:
        # 假设内容中包含直播源链接，处理内容
        sources = content.splitlines()
        for source in sources:
            if await test_speed(source):
                valid_sources.append(source)

    return valid_sources

# 写入文件
def write_to_file(file_path: str, category_name: str, sources: list):
    create_directory(os.path.dirname(file_path))
    with open(file_path, 'w') as f:
        f.write(f"{category_name},#genre#\n")
        for idx, source in enumerate(sources, start=1):
            f.write(f"{idx} {source}\n")
    logging.info(f"写入文件 {file_path} 完成.")

# 主流程
async def main():
    valid_sources = await fetch_and_categorize_sources()

    # 白名单和黑名单的输出路径
    white_list_path = "white_list.txt"
    black_list_path = "black_list.txt"

    # 根据响应时间判断有效源，生成白名单和黑名单
    white_list = []
    black_list = []

    for source in valid_sources:
        if await test_speed(source):
            white_list.append(source)
        else:
            black_list.append(source)

    # 写入文件
    write_to_file(white_list_path, "有效直播源", white_list)
    write_to_file(black_list_path, "无效直播源", black_list)

# 运行主程序
if __name__ == "__main__":
    asyncio.run(main())
