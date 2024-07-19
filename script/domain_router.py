import time
import requests
import re
import os
import ipaddress
from datetime import datetime, timedelta, timezone
import logging

# 配置日志记录，确保日志文件使用 utf-8 编码
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

def covers(pattern, domain):
    if pattern == domain:
        return True
    elif pattern == '*':
        return '.' not in domain and '+' not in domain and '*' not in domain
    elif pattern.startswith('*.'):
        return domain.endswith(pattern[2:]) and (domain.count('.') == pattern.count('.') or domain == pattern[2:])
    elif pattern.startswith('+.'):
        return domain.endswith(pattern[2:]) or domain == pattern[2:]
    elif pattern.startswith('.'):
        return domain.endswith(pattern) and domain != pattern[1:]
    return False

def covers_cidr(cidr1, cidr2):
    """ 检查 cidr1 是否完全覆盖 cidr2 """
    network1 = ipaddress.ip_network(cidr1, strict=False)
    network2 = ipaddress.ip_network(cidr2, strict=False)
    return network1.supernet_of(network2)

def optimize_domains(domains):
    """ 优化域名列表 """
    domains = list(set(domains))
    
    # 移除非法的 + 和 . 独立字符
    domains = [d for d in domains if d != '+' and d != '.']
    
    # 保持通配符的优先级
    plus_domains = [d for d in domains if d.startswith('+')]
    star_domains = [d for d in domains if d.startswith('*')]
    other_domains = [d for d in domains if not d.startswith('+') and not d.startswith('*')]
    domains = plus_domains + star_domains + other_domains

    n = len(domains)
    i = 0
    while i < n:
        j = 0
        while j < n:
            if i != j and covers(domains[i], domains[j]):
                del domains[j]
                n -= 1
                if j < i:
                    i -= 1
            elif i != j and covers(domains[j], domains[i]):
                del domains[i]
                n -= 1
                i -= 1
                break
            else:
                j += 1
        i += 1

    return domains

def optimize_cidrs(cidrs):
    """ 优化 CIDR 列表 """
    ipv4_cidrs = [cidr for cidr in cidrs if ipaddress.ip_network(cidr).version == 4]
    ipv6_cidrs = [cidr for cidr in cidrs if ipaddress.ip_network(cidr).version == 6]
    
    optimized_ipv4 = optimize_single_cidr_list(ipv4_cidrs)
    optimized_ipv6 = optimize_single_cidr_list(ipv6_cidrs)
    
    return optimized_ipv4 + optimized_ipv6

def optimize_single_cidr_list(cidrs):
    """ 优化单一类型的 CIDR 列表（IPv4 或 IPv6） """
    cidrs = list(set(cidrs))
    n = len(cidrs)
    
    i = 0
    while i < n:
        j = 0
        while j < n:
            if i != j and covers_cidr(cidrs[i], cidrs[j]):
                del cidrs[j]
                n -= 1
                if j < i:
                    i -= 1
            elif i != j and covers_cidr(cidrs[j], cidrs[i]):
                del cidrs[i]
                n -= 1
                i -= 1
                break
            else:
                j += 1
        i += 1

    return cidrs

def optimize_list(input_list):
    """ 优化输入列表，判断是 CIDR 列表还是域名列表 """
    try:
        ipaddress.ip_network(input_list[0], strict=False)
        return optimize_cidrs(input_list)
    except ValueError:
        return optimize_domains(input_list)

def filter_and_trim_values(values):
    """ 过滤和修剪值 """
    filtered_values = []
    domain_pattern = re.compile(
        r'^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z]{2,6})+$'
    )

    for item in values:
        item = ''.join(item.split())

        if item.startswith('#') or item.startswith('payload'):
            logging.info(f"跳过行: {item}")
            continue

        if domain_pattern.match(item):
            filtered_values.append(f"+.{item}")
            logging.info(f"添加域名: +.{item}")
            continue

        item_trimmed = re.sub(r'^[^\w\u4e00-\u9fa5:+*.]+|[^\w\u4e00-\u9fa5:+*.]+$', '', item)
        special_characters_count = len(re.findall(r'[^a-zA-Z0-9\u4e00-\u9fa5()$/\\^,:+*.-]', item_trimmed))
        if special_characters_count > 3:
            logging.info(f"剔除非法内容: {item_trimmed}")
            continue

        filtered_values.append(item_trimmed)
        logging.info(f"添加修剪后的内容: {item_trimmed}")
    return filtered_values

def classify_values(values):
    """ 分类值为域名、IP/CIDR 和经典规则 """
    domain_list = []
    ipcidr_list = []
    classical_list = []
    for item in values:
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

def sort_ipcidr_items(items):
    """ 排序 IP/CIDR 项目 """
    if items:
        items = optimize_list(items)
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

def sort_classic_items(items):
    """ 排序经典规则项目 """
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
    item_counts = {k: v for k, v in item_counts.items() if v > 0}

    return sorted_items, item_counts

def preprocess_for_sorting(item):
    """ 预处理域名项目以便排序 """
    if item.startswith("  - '") and item.endswith("'"):
        item = item[5:-1]
    return item

def sort_formatted_domain_items(items):
    """ 排序格式化后的域名项目 """
    tmp_items = []
    for item in items:
        tmp_items.append(preprocess_for_sorting(item))
    tmp_items = optimize_list(tmp_items)
    
    plus_items = []
    star_items = []
    dot_items = []
    plain_items = []

    for tmp_item in tmp_items:
        if tmp_item.startswith('+.'):
            plus_items.append(tmp_item)
        elif tmp_item.startswith('*.'):
            star_items.append(tmp_item)
        elif tmp_item.startswith('.'):
            dot_items.append(tmp_item)
        else:
            plain_items.append(tmp_item)

    def sort_by_parts(items):
        return sorted(items, key=lambda x: (x.count('.'), x))

    plus_items = sort_by_parts(plus_items)
    star_items = sort_by_parts(star_items)
    dot_items = sort_by_parts(dot_items)
    plain_items = sort_by_parts(plain_items)

    return plus_items + star_items + dot_items + plain_items

def format_item(item, item_type):
    """ 格式化项目 """
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
            return None

        if 'ip' in parts[0].lower():
            if not item.endswith(',no-resolve'):
                item += ',no-resolve'
        return f"  - {item}"

def deduplicate(items):
    """ 去重项目列表 """
    seen = set()
    deduped_items = []
    for item in items:
        if item and item not in seen:
            deduped_items.append(item)
            seen.add(item)
    return deduped_items

def count_classic_items(items):
    """ 统计经典规则项目数量 """
    counts = {}
    for item in items:
        item = item.lstrip("  - ").strip()
        parts = item.split(',')
        type_key = parts[0].strip()
        if type_key in counts:
            counts[type_key] += 1
        else:
            counts[type_key] = 1
    return counts

def count_ipcidr_items(items):
    """ 统计 IP/CIDR 项目数量 """
    ipv4_count = 0
    ipv6_count = 0
    for item in items:
        item_cleaned = item[5:-1]
        ip_net = ipaddress.ip_network(item_cleaned, strict=False)
        if ip_net.version == 4:
            ipv4_count += 1
        else:
            ipv6_count += 1
    return ipv4_count, ipv6_count

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

# 处理字典中的每一组数据
filtered_dict = {}
for key, content in data_dict.items():
    logging.info(f"过滤和修剪值: {key}")
    filtered_values = filter_and_trim_values(content["values"])
    filtered_dict[key] = {
        "values": filtered_values,
        "errors": content["errors"]
    }

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
            for i, item in enumerate(deduped_domain_list):
                if i < domain_total - 1:
                    file.write(f"{item}\n")
                else:
                    file.write(f"{item}")

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
            for i, item in enumerate(deduped_ipcidr_list):
                if i < ipcidr_total - 1:
                    file.write(f"{item}\n")
                else:
                    file.write(f"{item}")

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
            previous_prefix = None
            for i, item in enumerate(deduped_classical_list):
                current_prefix = item.split(',')[0].upper()
                if previous_prefix and previous_prefix != current_prefix:
                    file.write("\n")
                if i < classic_total - 1:
                    file.write(f"{item}\n")
                else:
                    file.write(f"{item}")
                previous_prefix = current_prefix

print("处理完成，生成的文件在'domain', 'ipcidr'和'classic'文件夹中。")
logging.info("处理完成，生成的文件在'domain', 'ipcidr'和'classic'文件夹中。")
