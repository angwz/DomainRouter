# 导入所需的模块
import os
import re
import time
import logging
import requests
import ipaddress
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置日志记录，设置日志文件名、级别和格式
log_file = "py_log.txt"
logging.basicConfig(
    filename=log_file,
    level=logging.WARNING,  # 只记录 WARNING 及以上级别的日志
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)

# 记录脚本开始运行的信息
logging.info("脚本开始运行...")

# 定义核心配置文件的 URL
CONFIG_URL = "https://raw.githubusercontent.com/angwz/DomainRouter/main/my.wei"

# 设置最大重试次数和每次重试之间的等待时间
MAX_RETRIES = 3  # 最大重试次数
RETRY_WAIT_TIME = 5  # 重试等待时间（秒）

def fetch_config(url):
    """
    获取核心配置文件内容。

    参数：
        url (str): 配置文件的 URL。

    返回：
        str: 配置文件内容，如果获取失败则返回空字符串。
    """
    # 循环尝试获取配置文件，最多重试 MAX_RETRIES 次
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logging.info(f"请求核心配置文件: {url} (第 {attempt} 次尝试)")
            # 发送 GET 请求获取配置文件
            response = requests.get(url)
            response.raise_for_status()  # 检查请求是否成功
            logging.info("成功获取配置文件")
            return response.text  # 返回配置文件内容
        except requests.exceptions.RequestException as e:
            # 如果请求失败，记录错误并等待一段时间后重试
            logging.error(f"获取配置文件时出错: {e}，将在 {RETRY_WAIT_TIME} 秒后重试 (已重试 {attempt} 次)")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT_TIME)  # 等待指定的秒数
            else:
                logging.error("多次尝试仍未能获取配置文件，程序将终止")
                return ""  # 返回空字符串表示获取失败

def parse_config(content):
    """
    解析配置文件内容，提取每个部分的键和值。

    参数：
        content (str): 配置文件内容。

    返回：
        dict: 包含解析后数据的字典。
    """
    data_dict = {}  # 初始化数据字典
    # 使用正则表达式匹配配置文件中的键和值
    pattern = re.compile(r"\[([^\]]+)\]([^\[]*)")
    matches = pattern.findall(content)
    logging.info(f"找到 {len(matches)} 个匹配项")

    skip_rules = False  # 标记是否跳过 [Rules] 后的内容

    # 遍历匹配到的键和值
    for match in matches:
        key = match[0].strip()  # 获取键
        if "rules" in key.lower():
            # 如果遇到 [Rules]，设置跳过标记
            skip_rules = True
            logging.info(f"跳过 'rules' 后面所有内容: {key}")
            continue
        if skip_rules:
            # 跳过 [Rules] 后面的第一行（空行或注释）
            skip_rules = False
            continue

        # 分割值，去除空白行和空格
        value = [v.strip() for v in match[1].strip().split("\n") if v.strip()]
        final_values = []
        urls = []

        # 将值分类为普通值和需要请求的 URL
        for item in value:
            if item.startswith("http"):
                urls.append(item)  # 将 URL 添加到 urls 列表
            else:
                final_values.append(item)  # 将普通值添加到 final_values 列表

        # 将处理后的数据存入字典
        data_dict[key] = {"values": final_values, "urls": urls, "errors": []}
        logging.info(f"处理完键: {key}")

    return data_dict  # 返回解析后的数据字典

def fetch_url_content(url):
    """
    获取给定 URL 的内容，支持重试。

    参数：
        url (str): 要请求的 URL。

    返回：
        list: 请求到的内容列表，如果获取失败则返回空列表。
    """
    # 循环尝试获取 URL 内容，最多重试 MAX_RETRIES 次
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logging.info(f"请求子内容: {url}")
            # 发送 GET 请求获取内容
            response = requests.get(url)
            response.raise_for_status()  # 检查请求是否成功
            logging.info(f"成功获取子内容: {url}")
            # 分割内容为行，并去除空白行
            return [line.strip() for line in response.text.split("\n") if line.strip()]
        except requests.exceptions.RequestException as e:
            # 如果请求失败，记录警告并等待一段时间后重试
            logging.warning(f"重试 {url} 由于错误: {e} (尝试次数: {attempt})")
            time.sleep(RETRY_WAIT_TIME)  # 等待指定的秒数
            if attempt == MAX_RETRIES:
                logging.error(f"资源 {url} 不存在，已重试 {MAX_RETRIES} 次")
                return []  # 返回空列表表示获取失败

def fetch_all_urls(data_dict):
    """
    并行获取所有需要请求的 URL 内容。

    参数：
        data_dict (dict): 数据字典。

    返回：
        dict: 所有 URL 对应的内容，键为 URL，值为内容列表。
    """
    all_urls = set()
    # 收集所有需要请求的 URL
    for key in data_dict:
        all_urls.update(data_dict[key]['urls'])

    fetched_contents = {}  # 初始化存储获取内容的字典
    # 使用线程池并行请求所有 URL
    with ThreadPoolExecutor(max_workers=10) as executor:
        # 提交所有请求任务
        future_to_url = {executor.submit(fetch_url_content, url): url for url in all_urls}
        # 等待所有请求完成
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            fetched_contents[url] = future.result()  # 获取请求结果

    return fetched_contents  # 返回所有获取的内容

def merge_url_contents(data_dict, fetched_contents):
    """
    将获取的 URL 内容合并回数据字典。

    参数：
        data_dict (dict): 数据字典。
        fetched_contents (dict): 所有 URL 对应的内容。

    返回：
        dict: 更新后的数据字典。
    """
    # 遍历数据字典，将获取的内容合并回去
    for key in data_dict:
        values = data_dict[key]['values']
        urls = data_dict[key]['urls']
        for url in urls:
            # 将 URL 对应的内容添加到 values 列表
            values.extend(fetched_contents.get(url, []))
        data_dict[key]['values'] = values  # 更新 values 列表
    return data_dict  # 返回更新后的数据字典

def write_to_delete_file(items):
    """
    将列表中的值写入 delete_data.txt 文件。

    参数：
        items (list): 要写入文件的列表。
    """
    # 以追加模式打开文件，编码为 utf-8
    with open('delete_data.txt', 'a', encoding='utf-8') as file:
        for item in items:
            file.write(f"{item}\n")  # 将每个项写入文件

def filter_invalid_domains(domain_list):
    """
    过滤掉无效的域名。

    参数：
        domain_list (list): 域名列表。

    返回：
        list: 过滤后的有效域名列表。
    """
    filtered_list = []

    # 遍历域名列表，进行各种检查
    for domain in domain_list:
        # 剔除只包含 ".", "*", "+" 的字符串
        if domain in [".", "*", "+"]:
            continue

        # 剔除不带 "." 的字符串
        if "." not in domain:
            continue

        # 剔除以 "+" 或 "*" 开头但第二个字符不是 "." 的字符串
        if (domain.startswith("+") or domain.startswith("*")) and len(domain) > 1 and domain[1] != ".":
            continue

        # 剔除包含连续 "**", "..", "++" 的字符串
        if "**" in domain or ".." in domain or "++" in domain:
            continue

        # 按 "." 分割域名，检查每部分的 "*" 和 "+" 数量
        parts = domain.split(".")
        if any(part == "" for part in parts[1:]):
            continue

        invalid = False
        for part in parts:
            if part.count("*") > 2 or part.count("+") > 2:
                invalid = True
                break
        if invalid:
            continue

        filtered_list.append(domain)  # 将有效域名添加到列表

    return filtered_list  # 返回过滤后的域名列表

def optimize_domains(domain_list):
    """
    优化域名列表，去除冗余的域名。

    参数：
        domain_list (list): 域名列表。

    返回：
        list: 优化后的域名列表。
    """
    if not domain_list:
        return []

    domain_set = set(filter_invalid_domains(domain_list))  # 过滤无效域名并去重
    # 按照后缀长度从长到短排序
    sorted_domains = sorted(domain_set, key=lambda x: (-x.count('.'), x))

    optimized_set = set()
    removed_domains = set()

    # 遍历排序后的域名列表，进行优化
    for domain in sorted_domains:
        if domain in removed_domains:
            continue
        if domain.startswith('+'):
            # 如果域名以 '+' 开头，移除其余相同后缀的域名
            suffix = domain[1:]
            for other_domain in sorted_domains:
                if other_domain != domain and other_domain.endswith(suffix):
                    removed_domains.add(other_domain)
        elif domain.startswith('.'):
            # 如果域名以 '.' 开头，移除其余以该后缀结尾的域名
            suffix = domain
            for other_domain in sorted_domains:
                if other_domain != domain and other_domain.endswith(suffix):
                    removed_domains.add(other_domain)
        elif '*' in domain:
            # 处理包含 '*' 的通配符域名
            pattern = domain.replace('.', r'\.').replace('*', r'.*')
            regex = re.compile(f'^{pattern}$')
            for other_domain in sorted_domains:
                if other_domain != domain and regex.match(other_domain):
                    removed_domains.add(other_domain)

        optimized_set.add(domain)  # 将域名添加到优化集合

    final_domains = optimized_set - removed_domains  # 去除被移除的域名
    return list(final_domains)  # 返回优化后的域名列表

def optimize_cidrs(cidrs):
    """
    优化 CIDR 列表，合并重叠的网络。

    参数：
        cidrs (list): CIDR 列表。

    返回：
        list: 优化后的 CIDR 列表。
    """
    if not cidrs:
        return []

    # 分别处理 IPv4 和 IPv6 的 CIDR
    ipv4_cidrs = [cidr for cidr in cidrs if ipaddress.ip_network(cidr).version == 4]
    ipv6_cidrs = [cidr for cidr in cidrs if ipaddress.ip_network(cidr).version == 6]

    optimized_ipv4 = optimize_single_cidr_list(ipv4_cidrs) if ipv4_cidrs else []
    optimized_ipv6 = optimize_single_cidr_list(ipv6_cidrs) if ipv6_cidrs else []

    return optimized_ipv4 + optimized_ipv6  # 返回优化后的 CIDR 列表

def optimize_single_cidr_list(cidrs):
    """
    优化单一类型的 CIDR 列表（IPv4 或 IPv6）。

    参数：
        cidrs (list): CIDR 列表。

    返回：
        list: 优化后的 CIDR 列表。
    """
    # 将字符串转换为 ip_network 对象并去重
    cidr_networks = {ipaddress.ip_network(cidr, strict=False) for cidr in cidrs}
    # 合并重叠和连续的网络
    optimized_networks = ipaddress.collapse_addresses(cidr_networks)
    # 将 ip_network 对象转换回字符串
    return [str(network) for network in optimized_networks]

def optimize_list(input_list):
    """
    优化输入列表，判断是 CIDR 列表还是域名列表并调用相应的优化函数。

    参数：
        input_list (list): 输入列表。

    返回：
        list: 优化后的列表。
    """
    try:
        # 尝试将第一个元素解析为网络地址，判断是否为 CIDR 列表
        ipaddress.ip_network(input_list[0], strict=False)
        return optimize_cidrs(input_list)  # 调用 CIDR 优化函数
    except ValueError:
        return optimize_domains(input_list)  # 调用域名优化函数

def filter_and_trim_values(values):
    """
    过滤和修剪值，剔除无效或非法的内容。

    参数：
        values (list): 原始值列表。

    返回：
        list: 过滤和修剪后的值列表。
    """
    filtered_values = []
    # 域名的正则表达式模式
    domain_pattern = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z]{2,6})+$")

    for item in values:
        item = "".join(item.split())  # 去除所有空白字符

        if item.startswith("#") or item.startswith("payload"):
            logging.info(f"跳过行: {item}")
            continue

        if domain_pattern.match(item):
            # 如果是有效的域名，添加 '+.' 前缀
            filtered_values.append(f"+.{item}")
            logging.info(f"添加域名: +.{item}")
            continue

        # 修剪字符串，去除非法字符
        item_trimmed = re.sub(r"^[^\w\u4e00-\u9fa5:+*.]+|[^\w\u4e00-\u9fa5:+*.]+$", "", item)
        # 统计特殊字符的数量
        special_characters_count = len(re.findall(r"[^a-zA-Z0-9\u4e00-\u9fa5()$/\\^,:+*.-]", item_trimmed))
        if special_characters_count > 3:
            logging.info(f"剔除非法内容: {item_trimmed}")
            continue

        filtered_values.append(item_trimmed)  # 添加修剪后的内容
        logging.info(f"添加修剪后的内容: {item_trimmed}")
    return filtered_values  # 返回过滤后的值列表

def classify_values(values):
    """
    将值分类为域名、IP/CIDR 和经典规则。

    参数：
        values (list): 值列表。

    返回：
        tuple: (域名列表, IP/CIDR 列表, 经典规则列表)。
    """
    domain_list = []
    ipcidr_list = []
    classical_list = []

    for item in values:
        item = item.strip()
        try:
            # 尝试将项解析为 IP 地址
            ip_addr = ipaddress.ip_address(item)
            if ip_addr.version == 4:
                ipcidr_list.append(f"{item}/32")  # 添加 IPv4 地址
            else:
                ipcidr_list.append(f"{item}/128")  # 添加 IPv6 地址
            continue
        except ValueError:
            pass

        try:
            # 尝试将项解析为网络地址
            ip_net = ipaddress.ip_network(item, strict=False)
            ipcidr_list.append(item)  # 添加 CIDR
            continue
        except ValueError:
            pass

        # 使用正则表达式判断是否为域名
        if re.match(r"(\+\..*|\*.*|DOMAIN-SUFFIX,.*|DOMAIN,.*|^[a-zA-Z0-9\-.]+$)", item, re.IGNORECASE):
            domain_list.append(item)
        else:
            # 其他情况视为经典规则
            parts = item.split(",")
            if len(parts) > 1:
                try:
                    ip_net = ipaddress.ip_network(parts[1].strip(), strict=False)
                    ipcidr_list.append(parts[1].strip())
                except ValueError:
                    classical_list.append(item)
            else:
                classical_list.append(item)

    return domain_list, ipcidr_list, classical_list  # 返回分类后的列表

def sort_ipcidr_items(items):
    """
    排序 IP/CIDR 项目，先优化再排序。

    参数：
        items (list): IP/CIDR 列表。

    返回：
        list: 排序后的 IP/CIDR 列表。
    """
    if items:
        items = optimize_list(items)  # 先优化列表

    ipv4_items = []
    ipv6_items = []

    # 分别收集 IPv4 和 IPv6 的 CIDR
    for item in items:
        try:
            ip_net = ipaddress.ip_network(item, strict=False)
            if ip_net.version == 4:
                ipv4_items.append(item)
            else:
                ipv6_items.append(item)
        except ValueError:
            pass

    # 分别对 IPv4 和 IPv6 列表进行排序
    ipv4_items.sort(key=lambda x: ipaddress.ip_network(x).with_prefixlen)
    ipv6_items.sort(key=lambda x: ipaddress.ip_network(x).with_prefixlen)

    return ipv4_items + ipv6_items  # 返回排序后的列表

def sort_classical_items(items):
    """
    排序经典规则项目，并统计每种规则的数量。

    参数：
        items (list): 经典规则列表。

    返回：
        tuple: (排序后的列表, 统计计数)。
    """
    # 定义规则的排序顺序
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
        "SUB-RULE": 27,
    }

    item_counts = {key: 0 for key in order.keys()}  # 初始化计数器

    def get_order(item):
        # 获取项目的排序顺序
        parts = item.split(",")
        key = parts[0].upper()
        if key in order:
            item_counts[key] += 1
            return order[key]
        return len(order)

    sorted_items = sorted(items, key=get_order)  # 按顺序排序
    # 过滤计数器中数量为 0 的项
    item_counts = {k: v for k, v in item_counts.items() if v > 0}

    return sorted_items, item_counts  # 返回排序后的列表和计数器

def preprocess_for_sorting(item):
    """
    预处理域名项目以便排序，去除多余的前缀和后缀。

    参数：
        item (str): 域名项目。

    返回：
        str: 预处理后的域名。
    """
    # 去除前缀 "  - '" 和后缀 "'"
    if item.startswith("  - '") and item.endswith("'"):
        item = item[5:-1]
    return item

def sort_formatted_domain_items(items):
    """
    排序格式化后的域名项目，并处理被删除的项。

    参数：
        items (list): 域名列表。

    返回：
        list: 排序并去重后的域名列表。
    """
    # 对域名进行预处理
    pruned_list = [preprocess_for_sorting(item) for item in items]
    original_list = pruned_list.copy()  # 备份原始列表
    pruned_list = optimize_list(pruned_list)  # 优化域名列表

    # 分类域名，方便排序
    plus_items = []
    star_items = []
    dot_items = []
    plain_items = []

    for item in pruned_list:
        if item.startswith("+."):
            plus_items.append(item)
        elif item.startswith("*."):
            star_items.append(item)
        elif item.startswith("."):
            dot_items.append(item)
        else:
            plain_items.append(item)

    # 定义排序函数，按点的数量和字典顺序排序
    def sort_by_parts(items):
        return sorted(items, key=lambda x: (x.count("."), x))

    # 对每个分类的域名进行排序
    plus_items = sort_by_parts(plus_items)
    star_items = sort_by_parts(star_items)
    dot_items = sort_by_parts(dot_items)
    plain_items = sort_by_parts(plain_items)

    domains_list = plus_items + star_items + dot_items + plain_items  # 合并所有域名
    removed_items = list(set(original_list) - set(domains_list))  # 找出被移除的域名

    # 把被删除的项写入文件记录
    if removed_items:
        write_to_delete_file(removed_items)

    return domains_list  # 返回排序后的域名列表

def format_item(item, item_type):
    """
    格式化项目，根据类型添加适当的前缀和后缀。

    参数：
        item (str): 项目内容。
        item_type (str): 项目类型，可以是 'domain', 'ipcidr', 'classic'。

    返回：
        str: 格式化后的项目字符串。
    """
    if item_type == "domain":
        if item.lower().startswith("domain,"):
            item = item[len("domain,"):]
            return f"  - '{item}'"
        elif item.lower().startswith("domain-suffix,"):
            item = item[len("domain-suffix,"):]
            return f"  - '+.{item}'"
        else:
            return f"  - '{item}'"
    elif item_type == "ipcidr":
        return f"  - '{item}'"
    else:
        parts = item.split(",")
        # 定义有效的前缀列表
        valid_prefixes = [
            "DOMAIN-KEYWORD",
            "DOMAIN-REGEX",
            "GEOSITE",
            "IP-SUFFIX",
            "IP-ASN",
            "GEOIP",
            "SRC-GEOIP",
            "SCR-IP-ASN",
            "SRC-IP-CIDR",
            "SRC-IP-SUFFIX",
            "DST-PORT",
            "SRC-PORT",
            "IN-PORT",
            "IN-TYPE",
            "IN-USER",
            "IN-NAME",
            "PROCESS-PATH",
            "PROCESS-PATH-REGEX",
            "PROCESS-NAME",
            "PROCESS-NAME-REGEX",
            "UID",
            "NETWORK",
            "DSCP",
            "RULE-SET",
            "AND",
            "OR",
            "NOT",
            "SUB-RULE",
        ]
        if parts[0].upper() not in valid_prefixes:
            return None  # 无效的前缀，返回 None

        if "ip" in parts[0].lower() and not item.endswith(",no-resolve"):
            item += ",no-resolve"  # 对 IP 规则添加 ',no-resolve'
        return f"  - {item}"

def deduplicate(items):
    """
    去重项目列表，保持原有顺序。

    参数：
        items (list): 项目列表。

    返回：
        list: 去重后的项目列表。
    """
    seen = set()
    deduped_items = []
    for item in items:
        if item and item not in seen:
            deduped_items.append(item)
            seen.add(item)
    return deduped_items  # 返回去重后的列表

def count_classical_items(items):
    """
    统计经典规则项目数量。

    参数：
        items (list): 经典规则列表。

    返回：
        dict: 每种规则的数量字典。
    """
    counts = {}
    for item in items:
        item = item.lstrip("  - ").strip()
        parts = item.split(",")
        type_key = parts[0].strip()
        counts[type_key] = counts.get(type_key, 0) + 1
    return counts  # 返回计数器

def count_ipcidr_items(items):
    """
    统计 IP/CIDR 项目数量，分别统计 IPv4 和 IPv6。

    参数：
        items (list): IP/CIDR 列表。

    返回：
        tuple: (IPv4 数量, IPv6 数量)。
    """
    ipv4_count = 0
    ipv6_count = 0
    for item in items:
        item_cleaned = item[5:-1]  # 去除前缀和后缀
        try:
            ip_net = ipaddress.ip_network(item_cleaned, strict=False)
            if ip_net.version == 4:
                ipv4_count += 1
            else:
                ipv6_count += 1
        except ValueError:
            pass
    return ipv4_count, ipv6_count  # 返回统计结果

def prepare_directories():
    """
    创建并清空 'domain', 'classic' 和 'ipcidr' 文件夹。

    如果文件夹不存在，则创建；如果存在，则清空其中的文件。
    """
    for folder in ["domain", "classic", "ipcidr"]:
        os.makedirs(folder, exist_ok=True)  # 创建文件夹
        folder_path = os.path.join(os.getcwd(), folder)
        # 遍历文件夹中的文件并删除
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # 删除文件或链接
            except Exception as e:
                logging.error(f"删除 {file_path} 失败。原因: {e}")

def process_data(data_dict):
    """
    处理数据字典，生成相应的文件。

    参数：
        data_dict (dict): 数据字典。
    """
    filtered_dict = {}
    # 过滤和修剪每个键对应的值
    for key, content in data_dict.items():
        logging.info(f"过滤和修剪值: {key}")
        filtered_values = filter_and_trim_values(content["values"])
        filtered_dict[key] = {"values": filtered_values, "errors": content["errors"]}

    # 处理每个键对应的内容
    for key, content in filtered_dict.items():
        values = content["values"]

        # 分类值为域名、IP/CIDR 和经典规则
        domain_list, ipcidr_list, classical_list = classify_values(values)
        original_ipcidr_list = ipcidr_list.copy()  # 备份原始的 IP/CIDR 列表

        if ipcidr_list:
            ipcidr_list = sort_ipcidr_items(ipcidr_list)  # 排序 IP/CIDR 列表

        classical_list, _ = sort_classical_items(classical_list)  # 排序经典规则列表

        if domain_list:
            # 格式化域名列表
            formatted_domain_list = [format_item(item, "domain") for item in domain_list]
            # 排序格式化后的域名列表
            sorted_formatted_domain_list = sort_formatted_domain_items(formatted_domain_list)
        else:
            sorted_formatted_domain_list = []

        # 找出被删除的 IP/CIDR 项
        removed_ipcidrs = list(set(original_ipcidr_list) - set(ipcidr_list))
        if removed_ipcidrs:
            write_to_delete_file(removed_ipcidrs)  # 写入删除记录

        # 去重各个列表
        deduped_domain_list = deduplicate(
            [format_item(item, "domain") for item in sorted_formatted_domain_list if item]
        )
        deduped_ipcidr_list = deduplicate(
            [format_item(item, "ipcidr") for item in ipcidr_list if item]
        )
        deduped_classical_list = deduplicate(
            [format_item(item, "classic") for item in classical_list if item]
        )

        # 如果所有列表都为空，跳过当前键
        if not deduped_domain_list and not deduped_ipcidr_list and not deduped_classical_list:
            continue

        # 统计各个列表的数量
        domain_total = len(deduped_domain_list)
        ipcidr_total = len(deduped_ipcidr_list)
        classic_total = len(deduped_classical_list)
        classic_counts = count_classical_items(deduped_classical_list)
        ipv4_count, ipv6_count = count_ipcidr_items(deduped_ipcidr_list)

        logging.info(f"{key} - domain_list count: {domain_total}")
        logging.info(f"{key} - ipcidr_list count: {ipcidr_total}, ipv4_total: {ipv4_count}, ipv6_total: {ipv6_count}")
        logging.info(f"{key} - classical_list count: {classic_total}, classic_counts: {classic_counts}")

        # 获取当前时间，时区为 UTC+8
        current_time = datetime.now(timezone.utc) + timedelta(hours=8)
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

        # 生成 domain 文件
        if domain_total > 0:
            with open(f"domain/{key}.yaml", "w", encoding="utf-8") as file:
                file.write(f"# NAME: {key}\n")
                file.write("# AUTHOR: Angwz\n")
                file.write("# REPO: https://github.com/angwz/DomainRouter\n")
                file.write(f"# UPDATED: {current_time_str} (UTC+8)\n")
                file.write("# TYPE: domain\n")
                file.write(f"# TOTAL: {domain_total}\n")
                file.write("payload:\n")
                for i, item in enumerate(deduped_domain_list):
                    # 写入每一项，最后一项不添加换行符
                    file.write(f"{item}\n" if i < domain_total - 1 else f"{item}")

        # 生成 ipcidr 文件
        if ipcidr_total > 0:
            with open(f"ipcidr/{key}-ipcidr.yaml", "w", encoding="utf-8") as file:
                file.write(f"# NAME: {key}\n")
                file.write("# AUTHOR: Angwz\n")
                file.write("# REPO: https://github.com/angwz/DomainRouter\n")
                file.write(f"# UPDATED: {current_time_str} (UTC+8)\n")
                file.write("# TYPE: ipcidr\n")
                file.write(f"# TOTAL: {ipcidr_total}\n")
                if ipv4_count > 0:
                    file.write(f"# IP-CIDR TOTAL: {ipv4_count}\n")
                if ipv6_count > 0:
                    file.write(f"# IP-CIDR6 TOTAL: {ipv6_count}\n")
                file.write("payload:\n")
                for i, item in enumerate(deduped_ipcidr_list):
                    file.write(f"{item}\n" if i < ipcidr_total - 1 else f"{item}")

        # 生成 classic 文件
        if classic_total > 0:
            with open(f"classic/{key}-classic.yaml", "w", encoding="utf-8") as file:
                file.write(f"# NAME: {key}\n")
                file.write("# AUTHOR: Angwz\n")
                file.write("# REPO: https://github.com/angwz/DomainRouter\n")
                file.write(f"# UPDATED: {current_time_str} (UTC+8)\n")
                file.write("# TYPE: classic\n")
                file.write(f"# TOTAL: {classic_total}\n")
                for k, v in classic_counts.items():
                    if v > 0:
                        file.write(f"# {k} TOTAL: {v}\n")
                file.write("payload:\n")
                previous_prefix = None
                for i, item in enumerate(deduped_classical_list):
                    current_prefix = item.split(",")[0].upper()
                    if previous_prefix and previous_prefix != current_prefix:
                        file.write("\n")  # 不同类型之间添加空行
                    file.write(f"{item}\n" if i < classic_total - 1 else f"{item}")
                    previous_prefix = current_prefix

def main():
    """
    主函数，执行脚本的主要流程。
    """
    content = fetch_config(CONFIG_URL)  # 获取配置文件内容
    if not content:
        return

    data_dict = parse_config(content)  # 解析配置文件
    fetched_contents = fetch_all_urls(data_dict)  # 获取所有 URL 内容
    data_dict = merge_url_contents(data_dict, fetched_contents)  # 合并内容
    prepare_directories()  # 准备目录
    process_data(data_dict)  # 处理数据并生成文件

    print("处理完成，生成的文件在 'domain'、'ipcidr' 和 'classic' 文件夹中。")
    logging.info("处理完成，生成的文件在 'domain'、'ipcidr' 和 'classic' 文件夹中。")

if __name__ == "__main__":
    main()  # 调用主函数
