import asyncio
import aiohttp
import os
import logging
import time

# 配置日志
logging.basicConfig(level=logging.INFO)

# 下载 .m3u 文件并转换为 .txt 文件
async def download_m3u_file(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    content = await response.text()
                    return content
        except Exception as e:
            logging.error(f"无法下载 {url}: {e}")
    return ""

# 解析 .m3u 文件内容并提取直播源链接
def parse_m3u_content(content: str) -> list:
    lines = content.splitlines()
    live_sources = []
    for line in lines:
        # M3U 格式中的有效链接一般以 'http' 或 'https' 开头
        if line.startswith("http"):
            live_sources.append(line.strip())
    return live_sources

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

# 创建目录
def create_directory(path: str):
    if not os.path.exists(path):
        os.makedirs(path)

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
    m3u_url = "https://fm1077.serv00.net/SmartTV.m3u"
    live_source_file_path = "live_sources.txt"  # 存储转换后的 .txt 文件
    white_list_path = "white_list.txt"  # 白名单文件
    black_list_path = "black_list.txt"  # 黑名单文件

    # 下载 .m3u 文件并转换为 .txt 文件
    m3u_content = await download_m3u_file(m3u_url)
    if m3u_content:
        # 解析 .m3u 内容，提取直播源链接
        live_sources = parse_m3u_content(m3u_content)
        # 将直播源写入 .txt 文件
        with open(live_source_file_path, 'w') as f:
            for source in live_sources:
                f.write(f"{source}\n")
        logging.info(f"转换完成：{live_source_file_path}")

        # 根据响应时间判断有效源，生成白名单和黑名单
        white_list = []
        black_list = []

        for source in live_sources:
            if await test_speed(source):
                white_list.append(source)
            else:
                black_list.append(source)

        # 写入白名单和黑名单文件
        write_to_file(white_list_path, "有效直播源", white_list)
        write_to_file(black_list_path, "无效直播源", black_list)

# 运行主程序
if __name__ == "__main__":
    asyncio.run(main())
