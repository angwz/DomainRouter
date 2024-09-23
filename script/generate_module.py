import os
import re
import time
import logging
import requests
import ipaddress
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置日志记录
logging.basicConfig(
    filename="py_log.txt",
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)

CONFIG_URL = "https://raw.githubusercontent.com/angwz/DomainRouter/main/config/my.shadowrocket"
MAX_RETRIES = 3
RETRY_WAIT_TIME = 5

def fetch_config(url):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logging.info(f"请求核心配置文件: {url} (第 {attempt} 次尝试)")
            response = requests.get(url)
            response.raise_for_status()
            logging.info("成功获取配置文件")
            return response.text
        except requests.exceptions.RequestException as e:
            logging.error(f"获取配置文件时出错: {e}，将在 {RETRY_WAIT_TIME} 秒后重试 (已重试 {attempt} 次)")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT_TIME)
            else:
                logging.error("多次尝试仍未能获取配置文件，程序将终止")
                return ""

def parse_config(content):
    data_dict = {}
    pattern = re.compile(r"\[([^\]]+)\]([^\[]*)")
    matches = pattern.findall(content)
    logging.info(f"找到 {len(matches)} 个匹配项")

    rules_dict = {}
    for match in matches:
        key = match[0].strip()
        if key == "Rules":
            rules = [rule.strip() for rule in match[1].strip().split("\n") if rule.strip()]
            for rule in rules:
                group, proxy = rule.split(":", 1)
                rules_dict[group.strip()] = proxy.strip()
        else:
            value = [v.strip() for v in match[1].strip().split("\n") if v.strip()]
            urls = [item for item in value if item.startswith("http")]
            data_dict[key] = {"values": value, "urls": urls, "errors": []}

    return data_dict, rules_dict

def fetch_url_content(url):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logging.info(f"请求子内容: {url}")
            response = requests.get(url)
            response.raise_for_status()
            logging.info(f"成功获取子内容: {url}")
            return [line.strip() for line in response.text.split("\n") if line.strip()]
        except requests.exceptions.RequestException as e:
            logging.warning(f"重试 {url} 由于错误: {e} (尝试次数: {attempt})")
            time.sleep(RETRY_WAIT_TIME)
            if attempt == MAX_RETRIES:
                logging.error(f"资源 {url} 不存在，已重试 {MAX_RETRIES} 次")
                return []

def fetch_all_urls(data_dict):
    all_urls = set()
    for key in data_dict:
        all_urls.update(data_dict[key]['urls'])

    fetched_contents = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(fetch_url_content, url): url for url in all_urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            fetched_contents[url] = future.result()

    return fetched_contents

def merge_url_contents(data_dict, fetched_contents):
    for key in data_dict:
        values = data_dict[key]['values']
        urls = data_dict[key]['urls']
        for url in urls:
            values.extend(fetched_contents.get(url, []))
        data_dict[key]['values'] = values
    return data_dict

def filter_and_trim_values(values):
    filtered_values = []
    domain_pattern = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z]{2,6})+$")

    for item in values:
        item = "".join(item.split())

        if item.startswith("#") or item.startswith("payload"):
            logging.info(f"跳过行: {item}")
            continue

        if domain_pattern.match(item):
            filtered_values.append(f"+.{item}")
            logging.info(f"添加域名: +.{item}")
            continue

        item_trimmed = re.sub(r"^[^\w\u4e00-\u9fa5:+*.]+|[^\w\u4e00-\u9fa5:+*.]+$", "", item)
        special_characters_count = len(re.findall(r"[^a-zA-Z0-9\u4e00-\u9fa5()$/\\^,:+*.-]", item_trimmed))
        if special_characters_count > 3:
            logging.info(f"剔除非法内容: {item_trimmed}")
            continue

        filtered_values.append(item_trimmed)
        logging.info(f"添加修剪后的内容: {item_trimmed}")
    return filtered_values

def classify_and_format_values(values, proxy):
    """
    将所有值分类并格式化为 Shadowrocket 兼容的规则。
    """
    classified_rules = []

    for item in values:
        item = item.strip()
        if item.startswith("+."):
            classified_rules.append(f"DOMAIN-SUFFIX,{item[2:]},{proxy}")
        elif item.startswith("DOMAIN,") or item.startswith("DOMAIN-SUFFIX,") or item.startswith("DOMAIN-KEYWORD,"):
            parts = item.split(",")
            if len(parts) == 2:
                classified_rules.append(f"{item},{proxy}")
            else:
                classified_rules.append(item)
        elif re.match(r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$", item):
            classified_rules.append(f"DOMAIN,{item},{proxy}")
        else:
            # 处理其他规则类型
            parts = item.split(",")
            if len(parts) == 2:
                classified_rules.append(f"{item},{proxy}")
            else:
                classified_rules.append(item)

    return classified_rules

def process_data(data_dict, rules_dict):
    """
    处理数据并生成多个 Shadowrocket 模块文件。
    """
    for group, proxy in rules_dict.items():
        if group not in data_dict:
            logging.warning(f"组 {group} 在数据字典中不存在，跳过")
            continue

        content = data_dict[group]
        filtered_values = filter_and_trim_values(content["values"])
        classified_rules = classify_and_format_values(filtered_values, proxy)

        # 获取当前时间
        current_time = datetime.now(timezone.utc) + timedelta(hours=8)
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

        # 生成 .module 文件
        with open(f"{group}.module", "w", encoding="utf-8") as file:
            file.write(f"#!name={group}\n")
            file.write("#!desc=Generated by Shadowrocket Multi-Module Generator\n")
            file.write(f"#!date={current_time_str}\n\n")
            file.write("[Rule]\n")
            for rule in classified_rules:
                file.write(f"{rule}\n")

        logging.info(f"已生成 {group}.module 文件")

def main():
    content = fetch_config(CONFIG_URL)
    if not content:
        return

    data_dict, rules_dict = parse_config(content)
    fetched_contents = fetch_all_urls(data_dict)
    data_dict = merge_url_contents(data_dict, fetched_contents)
    process_data(data_dict, rules_dict)

    print("处理完成，生成的 .module 文件在当前目录中。")
    logging.info("处理完成，生成的 .module 文件在当前目录中。")

if __name__ == "__main__":
    main()