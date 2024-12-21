import aiohttp
import asyncio
import os
import logging
from bs4 import BeautifulSoup
import subprocess
import sys

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 目标URL
URL = "https://epg.pw/test_channel_page.html"
TIMEOUT = 5  # 设置请求超时时间（秒）
VALID_THRESHOLD = 2  # 响应时间阈值，2秒以内视为有效

# 自动生成 requirements.txt 文件
def ensure_requirements_file():
    dependencies = [
        "aiohttp",
        "beautifulsoup4"
    ]
    
    if not os.path.exists("requirements.txt"):
        logging.info("requirements.txt 文件不存在，正在创建...")
        try:
            with open("requirements.txt", "w") as f:
                for dep in dependencies:
                    f.write(f"{dep}\n")
            logging.info("requirements.txt 文件已成功创建。")
        except Exception as e:
            logging.error(f"创建 requirements.txt 文件时出错：{e}")
            sys.exit(1)
    else:
        logging.info("requirements.txt 文件已存在，无需创建。")

# 自动安装依赖
def install_requirements():
    ensure_requirements_file()  # 确保 requirements.txt 文件存在
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        logging.info("依赖安装成功。")
    except subprocess.CalledProcessError as e:
        logging.error(f"安装依赖失败：{e}")
        sys.exit(1)

# 发送GET请求获取网页内容
async def fetch_page_content():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(URL) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logging.error(f"Error fetching page content from {URL}: Status code {response.status}")
                    return None
    except Exception as e:
        logging.error(f"Error fetching page content: {e}")
        return None

# 基于节目名称自动分类
def classify_channel(name):
    name = name.lower()
    if '新闻' in name:
        return '新闻频道'
    elif '体育' in name:
        return '体育频道'
    elif '地方' in name:
        return '地方频道'
    elif '娱乐' in name:
        return '娱乐频道'
    else:
        return '其他频道'

# 测试单个直播源的响应时间
async def test_speed(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=TIMEOUT) as response:
                return response.status, response.url, response.elapsed.total_seconds()
    except Exception as e:
        logging.error(f"Error testing URL {url}: {e}")
        return None, url, None

# 解析网页内容，提取直播源数据
def parse_live_sources(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 假设每个节目都在一个 <div class="channel"> 标签中
    channels = soup.find_all('div', class_='channel')
    
    live_sources = []
    for channel in channels:
        try:
            # 提取每个频道的节目名称和链接
            name = channel.find('h2').text if channel.find('h2') else 'Unknown Name'
            link = channel.find('a')['href'] if channel.find('a') else None
            
            if link:
                category = classify_channel(name)
                live_sources.append((name, link))
        except Exception as e:
            logging.error(f"Error processing channel: {e}")
    
    return live_sources

# 根据响应时间排序并分类
async def test_and_categorize(live_sources):
    white_list = []
    black_list = []
    
    tasks = []
    
    for name, url in live_sources:
        tasks.append(test_speed(url))
    
    results = await asyncio.gather(*tasks)
    
    for status, url, elapsed in results:
        if status == 200 and elapsed is not None:
            if elapsed <= VALID_THRESHOLD:
                white_list.append(f"{url}, {elapsed}s")
                logging.info(f"Valid: {url} responded in {elapsed}s")
            else:
                black_list.append(f"{url}, {elapsed}s")
                logging.warning(f"Invalid (slow): {url} responded in {elapsed}s")
        else:
            black_list.append(f"{url}, Unreachable")
            logging.warning(f"Invalid (unreachable): {url}")
    
    return white_list, black_list

# 自动创建文件夹和保存白名单、黑名单
def save_to_files(white_list, black_list, base_path="live_streams"):
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    
    # 创建白名单和黑名单文件
    white_file = os.path.join(base_path, "white_list.txt")
    black_file = os.path.join(base_path, "black_list.txt")
    
    with open(white_file, 'w', encoding='utf-8') as f:
        for line in white_list:
            f.write(line + "\n")
    
    with open(black_file, 'w', encoding='utf-8') as f:
        for line in black_list:
            f.write(line + "\n")
    
    logging.info(f"White list saved to {white_file}")
    logging.info(f"Black list saved to {black_file}")

# 主程序
async def main():
    # 确保依赖文件和安装
    ensure_requirements_file()
    install_requirements()

    html_content = await fetch_page_content()

    if html_content:
        live_sources = parse_live_sources(html_content)
        
        if live_sources:
            white_list, black_list = await test_and_categorize(live_sources)
            save_to_files(white_list, black_list)
        else:
            logging.warning("No live sources found.")
    else:
        logging.error("Failed to retrieve the webpage content.")

# 启动爬虫程序
if __name__ == "__main__":
    asyncio.run(main())
