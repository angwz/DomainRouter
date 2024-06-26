import time
import requests
import re
import os
import ipaddress
from datetime import datetime

# 请求URL内容
url = 'https://raw.githubusercontent.com/angwz/DomainRouter/main/my.wei'
try:
    response = requests.get(url)
    response.raise_for_status()
    content = response.text
except requests.exceptions.RequestException as e:
    print(f"Error fetching the main content: {e}")
    content = ""

# 初始化字典
data_dict = {}

# 使用正则表达式解析内容
pattern = re.compile(r'\[([^\]]+)\]([^\[]*)')
matches = pattern.findall(content)

for match in matches:
    key = match[0].strip()
    value = match[1].strip().split('\n')
    value = [v.strip() for v in value if v.strip()]  # 清理空白行
    final_value = []
    error_urls = []

    for item in value:
        if item.startswith('http'):
            try:
                sub_response = requests.get(item)
                time.sleep(2)
                sub_response.raise_for_status()
                sub_content = sub_response.text
                sub_lines = sub_content.split('\n')
                final_value.extend([line.strip() for line in sub_lines if line.strip()])  # 清理空白行
            except requests.exceptions.RequestException as e:
                error_urls.append(item)
                print(f"Error fetching the sub content from {item}: {e}")
                continue
        else:
            final_value.append(item)

    data_dict[key] = {
        "values": final_value,
        "errors": error_urls
    }


# 定义过滤和修剪函数
def filter_and_trim_values(values):
    filtered_values = []
    for item in values:
        # 过滤掉以#或payload开头的行
        if item.startswith('#') or item.startswith('payload'):
            continue
        # 修剪内容，去掉多余的空格、-和单引号
        item = item.strip().strip('-').strip().strip("'")
        # 仅保留特定模式的内容
        if re.match(r'^[a-zA-Z0-9\+\*\.].*[a-zA-Z0-9\+\*\.]$', item):
            filtered_values.append(item)
    return filtered_values


# 处理字典中的每一组数据
filtered_dict = {}
for key, content in data_dict.items():
    filtered_values = filter_and_trim_values(content["values"])
    filtered_dict[key] = {
        "values": filtered_values,
        "errors": content["errors"]
    }


# 分类和排序函数
def classify_and_sort(values):
    categories = {
        "DOMAIN-SUFFIX": [],
        "DOMAIN-KEYWORD": [],
        "DOMAIN": [],
        "SRC-IP-CIDR": [],
        "IP-CIDR": [],
        "GEOIP": [],
        "DST-PORT": [],
        "SRC-PORT": []
    }

    for item in values:
        matched = False
        for category in categories:
            if item.startswith(category):
                categories[category].append(item)
                matched = True
                break
        if not matched:
            categories["DOMAIN"].append(item)

    sorted_items = []
    for category in ["DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN", "SRC-IP-CIDR", "IP-CIDR", "GEOIP", "DST-PORT", "SRC-PORT"]:
        sorted_items.extend(sorted(categories[category]))

    return sorted_items


# 创建domain和classic文件夹
os.makedirs('domain', exist_ok=True)
os.makedirs('classic', exist_ok=True)

# 清空domain和classic文件夹中的所有文件
for folder in ['domain', 'classic']:
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                os.rmdir(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

# 获取当前时间
current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


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
    else:
        try:
            ip_net = ipaddress.ip_network(item, strict=False)
            if ip_net.version == 4:
                return f"  - IP-CIDR,{item},no-resolve"
            else:
                return f"  - IP-CIDR6,{item},no-resolve"
        except ValueError:
            pass

        if item.startswith('IP-CIDR') and not item.endswith(',no-resolve'):
            item += ',no-resolve'
        elif item.startswith('IP-CIDR6') and not item.endswith(',no-resolve'):
            item += ',no-resolve'
        return f"  - {item}"


# 去重函数
def deduplicate(items):
    seen = set()
    deduped_items = []
    for item in items:
        if item not in seen:
            deduped_items.append(item)
            seen.add(item)
    return deduped_items


# 处理并生成文件
for key, content in filtered_dict.items():
    values = content["values"]
    errors = content["errors"]
    domain_list = classify_and_sort(values)

    if domain_list or errors:
        formatted_domain_list = [format_item(item, "domain") for item in domain_list]
        deduped_domain_list = deduplicate(formatted_domain_list)
        with open(f'domain/{key}.yaml', 'w') as file:
            file.write(f"# NAME: {key}\n")
            file.write("# AUTHOR: angwz\n")
            file.write("# REPO: https://github.com/angwz/DomainRouter\n")
            file.write(f"# UPDATED: {current_time}\n")
            file.write(f"# TYPE: domain\n")
            file.write(f"# TOTAL: {len(deduped_domain_list)}\n")
            if errors:
                file.write(f"# ERROR: {', '.join(errors)}\n")
            file.write("payload:\n")
            for item in deduped_domain_list:
                file.write(f"{item}\n")

    if errors:
        formatted_classical_list = [format_item(item, "classic") for item in classify_and_sort(values)]
        deduped_classical_list = deduplicate(formatted_classical_list)
        with open(f'classic/{key}.yaml', 'w') as file:
            file.write(f"# NAME: {key}\n")
            file.write("# AUTHOR: angwz\n")
            file.write("# REPO: https://github.com/angwz/DomainRouter\n")
            file.write(f"# UPDATED: {current_time}\n")
            file.write(f"# TYPE: classic\n")
            file.write(f"# TOTAL: {len(deduped_classical_list)}\n")
            if errors:
                file.write(f"# ERROR: {', '.join(errors)}\n")
            file.write("payload:\n")
            for item in deduped_classical_list:
                file.write(f"{item}\n")

print("处理完成，生成的文件在'domain'和'classic'文件夹中。")
