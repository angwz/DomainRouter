import time
import requests
import re
import os
import ipaddress
from datetime import datetime, timedelta, timezone
import logging

# 设置日志记录，确保日志文件使用 utf-8 编码
log_file = 'py_log.txt'
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

logging.info("开始运行脚本...")

# 请求URL内容
url = 'https://raw.githubusercontent.com/angwz/DomainRouter/main/my.wei'
try:
    logging.info(f"正在请求URL内容: {url}")
    response = requests.get(url)
    response.raise_for_status()
    content = response.text
    logging.info("成功获取URL内容")
except requests.exceptions.RequestException as e:
    logging.error(f"获取URL内容时出错: {e}")
    content = ""

# 初始化字典
data_dict = {}

# 使用正则表达式解析内容
pattern = re.compile(r'\[([^\]]+)\]([^\[]*)')
matches = pattern.findall(content)
logging.info(f"找到 {len(matches)} 个匹配项")

skip_rules = False

for match in matches:
    key = match[0].strip()
    if "rules" in key.lower():
        skip_rules = True
        logging.info(f"跳过包含'rules'的部分: {key}")
        continue  # 跳过包含"rules"的部分
    if skip_rules:
        skip_rules = False
        continue

    value = match[1].strip().split('\n')
    value = [v.strip() for v in value if v.strip()]  # 清理空白行
    final_value = []

    for item in value:
        if item.startswith('http'):
            while True:
                try:
                    logging.info(f"请求子内容: {item}")
                    sub_response = requests.get(item)
                    time.sleep(0.5)
                    sub_response.raise_for_status()
                    sub_content = sub_response.text
                    sub_lines = sub_content.split('\n')
                    final_value.extend([line.strip() for line in sub_lines if line.strip()])  # 清理空白行
                    logging.info(f"成功获取子内容: {item}")
                    break
                except requests.exceptions.RequestException as e:
                    logging.warning(f"重试 {item} 由于错误: {e}")
                    time.sleep(5)
        else:
            final_value.append(item)

    data_dict[key] = {
        "values": final_value,
        "errors": []
    }
    logging.info(f"处理完键: {key}")

# 定义过滤和修剪函数
def filter_and_trim_values(values):
    filtered_values = []
    domain_pattern = re.compile(
        r'^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z]{2,6})+$'
    )

    for item in values:
        # 去掉字符串两边和中间的所有空格
        item = ''.join(item.split())

        # 过滤掉以#或payload开头的行
        if item.startswith('#') or item.startswith('payload'):
            logging.info(f"跳过行: {item}")
            continue

        # 使用正则表达式判断是否为域名
        if domain_pattern.match(item):
            filtered_values.append(f"+.{item}")
            logging.info(f"添加域名: +.{item}")
            continue  # 如果是有效的域名，直接跳到下一个 item

        # 修剪内容，去掉两端所有非字母中文数字:+*.
        item_trimmed = re.sub(r'^[^\w\u4e00-\u9fa5:+*.]+|[^\w\u4e00-\u9fa5:+*.]+$', '', item)

        # 判断字符串所有字符中包含的非字母中文数字()$正斜杠反斜杠^,:+*.-字符的数量是否大于3个
        special_characters_count = len(re.findall(r'[^a-zA-Z0-9\u4e00-\u9fa5()$/\\^,:+*.-]', item_trimmed))
        if special_characters_count > 3:
            logging.info(f"剔除非法内容: {item_trimmed}")
            continue  # 剔除非法内容

        filtered_values.append(item_trimmed)
        logging.info(f"添加修剪后的内容: {item_trimmed}")
    return filtered_values

# 处理字典中的每一组数据
filtered_dict = {}
for key, content in data_dict.items():
    logging.info(f"过滤和修剪值: {key}")
    filtered_values = filter_and_trim_values(content["values"])
    filtered_dict[key] = {
        "values": filtered_values,
        "errors": content["errors"]
    }

# 分类函数
def classify_values(values):
    domain_list = []
    ipcidr_list = []
    classical_list = []
    for item in values:
        # 尝试直接判断是否为单个IP地址或IP段
        try:
            ip_addr = ipaddress.ip_address(item.strip())
            if ip_addr.version == 4:
                ipcidr_list.append(f"{item.strip()}/32")
            else:
                ipcidr_list.append(f"{item.strip()}/128")
            continue
        except ValueError:
            pass

        try:
            ip_net = ipaddress.ip_network(item.strip(), strict=False)
            ipcidr_list.append(item.strip())
            continue
        except ValueError:
            pass

        # 检查是否为域名规则
        if re.match(r'(\+\..*|\*.*|DOMAIN-SUFFIX,.*|DOMAIN,.*|^[a-zA-Z0-9\-.]+$)', item, re.IGNORECASE):
            domain_list.append(item)
        else:
            parts = item.split(',')
            if len(parts) > 1:
                try:
                    ip_net = ipaddress.ip_network(parts[1].strip(), strict=False)
                    ipcidr_list.append(parts[1].strip())
                except ValueError:
                    classical_list.append(item)
            else:
                classical_list.append(item)

    return domain_list, ipcidr_list, classical_list

# 排序函数 for IPCIDR
def sort_ipcidr_items(items):
    ipv4_items = []
    ipv6_items = []

    for item in items:
        try:
            ip_net = ipaddress.ip_network(item, strict=False)
            if ip_net.version == 4:
                ipv4_items.append(item)
            else:
                ipv6_items.append(item)
        except ValueError:
            pass

    ipv4_items.sort(key=lambda x: ipaddress.ip_network(x).with_prefixlen)
    ipv6_items.sort(key=lambda x: ipaddress.ip_network(x).with_prefixlen)

    return ipv4_items + ipv6_items

# 排序函数 for Classic
def sort_classic_items(items):
    order = {
        "DOMAIN-KEYWORD": 0,
        "DOMAIN-REGEX": 1,
        "GEOSITE": 2,
        "IP-SUFFIX": 3,
        "IP-ASN": 4,
        "GEOIP": 5,
        "SRC-GEOIP": 6,
        "SCR-IP-ASN": 7,
        "SRC-IP-CIDR": 8,
        "SRC-IP-SUFFIX": 9,
        "DST-PORT": 10,
        "SRC-PORT": 11,
        "IN-PORT": 12,
        "IN-TYPE": 13,
        "IN-USER": 14,
        "IN-NAME": 15,
        "PROCESS-PATH": 16,
        "PROCESS-PATH-REGEX": 17,
        "PROCESS-NAME": 18,
        "PROCESS-NAME-REGEX": 19,
        "UID": 20,
        "NETWORK": 21,
        "DSCP": 22,
        "RULE-SET": 23,
        "AND": 24,
        "OR": 25,
        "NOT": 26,
        "SUB-RULE": 27
    }

    item_counts = {key: 0 for key in order.keys()}

    def get_order(item):
        parts = item.split(',')
        if parts[0].upper() in order:
            item_counts[parts[0].upper()] += 1
            return order[parts[0].upper()]
        return len(order)

    sorted_items = sorted(items, key=get_order)

    # 只保留有数据的项
    item_counts = {k: v for k, v in item_counts.items() if v > 0}

    return sorted_items, item_counts

# 创建domain, classic, 和 ipcidr 文件夹
os.makedirs('domain', exist_ok=True)
os.makedirs('classic', exist_ok=True)
os.makedirs('ipcidr', exist_ok=True)

# 清空domain, classic 和 ipcidr 文件夹中的所有文件
for folder in ['domain', 'classic', 'ipcidr']:
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                os.rmdir(file_path)
        except Exception as e:
            logging.error(f'Failed to delete {file_path}. Reason: {e}')

# 格式化函数
def format_item(item, item_type):
    if item_type == "domain":
        if item.lower().startswith('domain,'):
            item = item[len('domain,'):]
            return f"  - '{item}'"
        elif item.lower().startswith('domain-suffix,'):
            item = item[len('domain-suffix,'):]
            return f"  - '+.{item}'"
        else:
            return f"  - '{item}'"
    elif item_type == "ipcidr":
        return f"  - '{item}'"
    else:
        parts = item.split(',')
        valid_prefixes = [
            "DOMAIN-KEYWORD", "DOMAIN-REGEX", "GEOSITE", "IP-SUFFIX", "IP-ASN", "GEOIP", "SRC-GEOIP", "SCR-IP-ASN",
            "SRC-IP-CIDR", "SRC-IP-SUFFIX", "DST-PORT", "SRC-PORT", "IN-PORT", "IN-TYPE", "IN-USER", "IN-NAME",
            "PROCESS-PATH", "PROCESS-PATH-REGEX", "PROCESS-NAME", "PROCESS-NAME-REGEX", "UID", "NETWORK", "DSCP",
            "RULE-SET", "AND", "OR", "NOT", "SUB-RULE"
        ]
        if parts[0].upper() not in valid_prefixes:
            return None  # 剔除不符合的内容

        if 'ip' in parts[0].lower():
            if not item.endswith(',no-resolve'):
                item += ',no-resolve'
        return f"  - {item}"

# 去重函数
def deduplicate(items):
    seen = set()
    deduped_items = []
    for item in items:
        if item and item not in seen:
            deduped_items.append(item)
            seen.add(item)
    return deduped_items

# 预处理函数 for sorting domain items after formatting
def preprocess_for_sorting(item):
    if item.startswith("  - '") and item.endswith("'"):
        item = item[5:-1]
    return item

# 排序函数 for Domain after formatting
def sort_formatted_domain_items(items):
    plus_items = []
    star_items = []
    dot_items = []
    plain_items = []

    for item in items:
        preprocessed_item = preprocess_for_sorting(item)
        if preprocessed_item.startswith('+.'):
            plus_items.append(preprocessed_item)
        elif preprocessed_item.startswith('*.'):
            star_items.append(preprocessed_item)
        elif preprocessed_item.startswith('.'):
            dot_items.append(preprocessed_item)
        else:
            plain_items.append(preprocessed_item)

    def sort_by_parts(items):
        return sorted(items, key=lambda x: (x.count('.'), x))

    plus_items = sort_by_parts(plus_items)
    star_items = sort_by_parts(star_items)
    dot_items = sort_by_parts(dot_items)
    plain_items = sort_by_parts(plain_items)

    return plus_items + star_items + dot_items + plain_items

# 统计deduped_classical_list中每种类型的数量
def count_classic_items(items):
    counts = {}
    for item in items:
        # 移除前缀和空白
        item = item.lstrip("  - ").strip()
        parts = item.split(',')
        type_key = parts[0].strip()
        if type_key in counts:
            counts[type_key] += 1
        else:
            counts[type_key] = 1
    return counts

# 统计deduped_ipcidr_list中每种类型的数量
def count_ipcidr_items(items):
    ipv4_count = 0
    ipv6_count = 0
    for item in items:
        # 去除前缀和单引号
        item_cleaned = item[5:-1]
        ip_net = ipaddress.ip_network(item_cleaned, strict=False)
        if ip_net.version == 4:
            ipv4_count += 1
        else:
            ipv6_count += 1
    return ipv4_count, ipv6_count

# 处理并生成文件
for key, content in filtered_dict.items():
    values = content["values"]
    domain_list, ipcidr_list, classical_list = classify_values(values)

    # 排序 ipcidr 和 classic 列表
    ipcidr_list = sort_ipcidr_items(ipcidr_list)
    classical_list, _ = sort_classic_items(classical_list)

    # 格式化 domain 列表
    formatted_domain_list = [format_item(item, "domain") for item in domain_list]
    # 排序 格式化后的 domain 列表
    sorted_formatted_domain_list = sort_formatted_domain_items(formatted_domain_list)
    # 再次格式化 排序后的 domain 列表
    deduped_domain_list = deduplicate([format_item(item, "domain") for item in sorted_formatted_domain_list if item])
    deduped_ipcidr_list = deduplicate([format_item(item, "ipcidr") for item in ipcidr_list if item])
    deduped_classical_list = deduplicate([format_item(item, "classic") for item in classical_list if item])

    # 统计数量
    domain_total = len(deduped_domain_list)
    ipcidr_total = len(deduped_ipcidr_list)
    classic_total = len(deduped_classical_list)
    classic_counts = count_classic_items(deduped_classical_list)
    ipv4_count, ipv6_count = count_ipcidr_items(deduped_ipcidr_list)

    logging.info(f"{key} - domain_list count: {domain_total}")
    logging.info(f"{key} - ipcidr_list count: {ipcidr_total}, ipv4_total: {ipv4_count}, ipv6_total: {ipv6_count}")
    logging.info(f"{key} - classical_list count: {classic_total}, classic_counts: {classic_counts}")

    # 生成 domain 文件
    if domain_total > 0:
        with open(f'domain/{key}.yaml', 'w', encoding='utf-8') as file:
            current_time = datetime.now(timezone.utc) + timedelta(hours=8)
            current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
            file.write(f"# NAME: {key}\n")
            file.write("# AUTHOR: angwz\n")
            file.write("# REPO: https://github.com/angwz/DomainRouter\n")
            file.write(f"# UPDATED: {current_time_str} (UTC+8)\n")
            file.write(f"# TYPE: domain\n")
            file.write(f"# TOTAL: {domain_total}\n")
            file.write("payload:\n")
            for item in deduped_domain_list:
                file.write(f"{item}\n")

    # 生成 ipcidr 文件
    if ipcidr_total > 0:
        with open(f'ipcidr/{key}-ipcidr.yaml', 'w', encoding='utf-8') as file:
            current_time = datetime.now(timezone.utc) + timedelta(hours=8)
            current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
            file.write(f"# NAME: {key}\n")
            file.write("# AUTHOR: angwz\n")
            file.write("# REPO: https://github.com/angwz/DomainRouter\n")
            file.write(f"# UPDATED: {current_time_str} (UTC+8)\n")
            file.write(f"# TYPE: ipcidr\n")
            file.write(f"# TOTAL: {ipcidr_total}\n")
            if ipv4_count > 0:
                file.write(f"# IP-CIDR TOTAL: {ipv4_count}\n")
            if ipv6_count > 0:
                file.write(f"# IP-CIDR6 TOTAL: {ipv6_count}\n")
            file.write("payload:\n")
            for item in deduped_ipcidr_list:
                file.write(f"{item}\n")

    # 生成 classic 文件
    if classic_total > 0:
        with open(f'classic/{key}-classic.yaml', 'w', encoding='utf-8') as file:
            current_time = datetime.now(timezone.utc) + timedelta(hours=8)
            current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
            file.write(f"# NAME: {key}\n")
            file.write("# AUTHOR: angwz\n")
            file.write("# REPO: https://github.com/angwz/DomainRouter\n")
            file.write(f"# UPDATED: {current_time_str} (UTC+8)\n")
            file.write(f"# TYPE: classic\n")
            file.write(f"# TOTAL: {classic_total}\n")
            for k, v in classic_counts.items():
                if v > 0:
                    file.write(f"# {k} TOTAL: {v}\n")
            file.write("payload:\n")
            for item in deduped_classical_list:
                file.write(f"{item}\n")


print("处理完成，生成的文件在'domain', 'ipcidr'和'classic'文件夹中。")
logging.info("处理完成，生成的文件在'domain', 'ipcidr'和'classic'文件夹中。")
