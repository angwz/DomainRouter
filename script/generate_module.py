import re
import requests
import time
import ipaddress
import os
from datetime import datetime, timedelta


def fetch_url_content_with_retries(url, max_retries=3, delay_between_retries=5):
    """
    获取URL内容，失败时进行重试

    参数:
    url (str): 要获取内容的URL
    max_retries (int): 最大重试次数
    delay_between_retries (int): 重试之间的延迟时间（秒）

    返回:
    list: 处理后的非空行列表
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url)
            response.raise_for_status()

            # 处理获取到的响应内容，去掉空白行和以 # 开头的行
            lines = response.text.splitlines()
            non_empty_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
            return non_empty_lines

        except requests.RequestException as error:
            print(f"第 {attempt + 1} 次请求失败，URL: {url}, 错误信息: {error}")
            if attempt < max_retries - 1:
                print(f"{delay_between_retries} 秒后重试...")
                time.sleep(delay_between_retries)

    print(f"请求 URL 失败: {url}，重试了 {max_retries} 次。")
    return []


def clean_single_line(line):
    """
    对单行进行清理和格式化

    参数:
    line (str): 要清理的行

    返回:
    str: 清理后的行
    """
    cleaned_line = line.strip().strip('"').strip('-').strip()

    # 处理行尾的 'no-resolve'
    if 'no-resolve' in cleaned_line:
        cleaned_line_before_no_resolve = cleaned_line[:cleaned_line.rfind('no-resolve')].rstrip()
        if cleaned_line_before_no_resolve.endswith(','):
            cleaned_line = cleaned_line_before_no_resolve[:-1].strip()
        else:
            cleaned_line = cleaned_line_before_no_resolve

    # 只处理前后以单引号包裹的行
    if cleaned_line.startswith("'") and cleaned_line.endswith("'"):
        cleaned_line = cleaned_line[1:-1].strip()  # 去掉首尾的单引号

        # 如果以 . 开头，删除整行
        if cleaned_line.startswith('.'):
            return ''

        # 如果以 +. 开头，替换为 'DOMAIN-SUFFIX,'
        if cleaned_line.startswith('+.'):
            cleaned_line = 'DOMAIN-SUFFIX,' + cleaned_line[2:]

        # 检查是否为 IP CIDR
        try:
            if '/' in cleaned_line:
                ip_network = ipaddress.ip_network(cleaned_line, strict=False)
                if ip_network.version == 4:
                    cleaned_line = f"IP-CIDR,{cleaned_line}"
                elif ip_network.version == 6:
                    cleaned_line = f"IP-CIDR6,{cleaned_line}"
        except ValueError:
            pass

        # 如果包含 '*', 删除整行
        if '*' in cleaned_line:
            return ''

    return cleaned_line


def preprocess_lines(lines):
    """
    对列表中的每一行进行预处理

    参数:
    lines (list): 要处理的行列表

    返回:
    list: 处理后的行列表
    """
    preprocessed_lines = []

    for line in lines:
        # 处理以 http:// 或 https:// 开头的行
        if line.startswith('http://') or line.startswith('https://'):
            preprocessed_lines.extend(fetch_url_content_with_retries(line))
        else:
            preprocessed_lines.append(line)

    # 清理所有行并过滤掉包含 'payload' 的行
    final_processed_lines = [clean_single_line(l) for l in preprocessed_lines if 'payload' not in l]
    # 移除空字符串
    final_processed_lines = [l for l in final_processed_lines if l]
    return final_processed_lines


def is_valid_domain(domain):
    """
    检查是否为有效域名

    参数:
    domain (str): 要检查的域名

    返回:
    bool: 域名是否有效
    """
    if not (domain[0].isalnum() and domain[-1].isalnum()):
        return False

    if not re.match(r'^[a-zA-Z0-9\-.]+$', domain):
        return False

    if '..' in domain:
        return False

    return True


def is_valid_wildcard_domain(line):
    """
    检查是否为有效的通配符域名

    参数:
    line (str): 要检查的行

    返回:
    bool: 是否为有效的通配符域名
    """
    return line.startswith('+.') and line[-1].isalnum()


def process_ip_and_domains(lines):
    """
    处理IP地址、普通域名和通配符域名

    参数:
    lines (list): 要处理的行列表

    返回:
    list: 处理后的行列表
    """
    processed_lines = []

    for line in lines:
        try:
            ip_address = ipaddress.ip_address(line)

            if ip_address.version == 4:
                processed_lines.append(f"IP-CIDR,{line}/32")
            elif ip_address.version == 6:
                processed_lines.append(f"IP-CIDR6,{line}/128")

        except ValueError:
            if is_valid_wildcard_domain(line):
                processed_lines.append(f"DOMAIN-SUFFIX,{line[2:]}")
            elif is_valid_domain(line):
                processed_lines.append(f"DOMAIN-SUFFIX,{line}")
            else:
                processed_lines.append(line)

    return processed_lines


def is_valid_prefix(element):
    """
    检查元素是否以合法的前缀开始

    参数:
    element (str): 要检查的元素

    返回:
    bool: 元素是否有合法前缀
    """
    valid_prefixes = [
        "DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-REGEX", "GEOSITE",
        "IP-CIDR", "IP-CIDR6", "GEOIP",
        "DST-PORT", "SRC-PORT",
        "PROCESS-PATH", "PROCESS-PATH-REGEX",
        "PROCESS-NAME", "PROCESS-NAME-REGEX"
    ]

    return any(element.startswith(prefix) for prefix in valid_prefixes)


def filter_elements_by_valid_prefix(lines):
    """
    对列表进行合法性检查，保留以有效前缀开始的元素或以 [ ] 包裹的行

    参数:
    lines (list): 要过滤的行列表

    返回:
    list: 过滤后的行列表
    """
    valid_lines = []

    for line in lines:
        if line.startswith('[') and line.endswith(']'):
            valid_lines.append(line)
        elif is_valid_prefix(line):
            valid_lines.append(line)

    return valid_lines


def is_suffix_covered(existing_value, new_value):
    """
    检查 existing_value 是否覆盖 new_value

    参数:
    existing_value (str): 现有的值
    new_value (str): 新的值

    返回:
    bool: existing_value 是否覆盖 new_value
    """
    existing_value = existing_value.lower()
    new_value = new_value.lower()
    if new_value == existing_value:
        return True
    if new_value.endswith('.' + existing_value):
        return True
    return False


def is_ip_subset(sub_cidr, parent_cidr):
    """
    检查 sub_cidr 是否是 parent_cidr 的子集

    参数:
    sub_cidr (str): 子网CIDR
    parent_cidr (str): 父网CIDR

    返回:
    bool: sub_cidr 是否是 parent_cidr 的子集
    """
    try:
        sub_network = ipaddress.ip_network(sub_cidr, strict=False)
        parent_network = ipaddress.ip_network(parent_cidr, strict=False)
        return sub_network.subnet_of(parent_network)
    except ValueError:
        return False


def optimize_rules(lines):
    """
    优化规则列表：去重和覆盖范围优化

    参数:
    lines (list): 要优化的规则列表

    返回:
    list: 优化后的规则列表
    """
    # 去重，保留第一个出现的元素
    seen = set()
    deduped_lines = []
    for line in lines:
        if line not in seen:
            deduped_lines.append(line)
            seen.add(line)

    # 按照原始顺序优化规则
    optimized_lines = []
    for idx, line in enumerate(deduped_lines):
        # 忽略以 [ 开头和 ] 结尾的行
        if line.startswith('[') and line.endswith(']'):
            optimized_lines.append(line)
            continue

        prefix = line.split(',', 1)[0]
        value = line.split(',', 1)[1] if ',' in line else ''

        # 只对指定类型进行优化
        if prefix not in ["DOMAIN-SUFFIX", "IP-CIDR", "IP-CIDR6"]:
            optimized_lines.append(line)
            continue

        to_remove = False

        # 与之前的规则比较
        for prev_line in optimized_lines:
            prev_prefix = prev_line.split(',', 1)[0]
            prev_value = prev_line.split(',', 1)[1] if ',' in prev_line else ''

            if prefix != prev_prefix:
                continue

            if prefix == "DOMAIN-SUFFIX":
                if is_suffix_covered(prev_value, value):
                    to_remove = True
                    break
            elif prefix in ["IP-CIDR", "IP-CIDR6"]:
                if is_ip_subset(value, prev_value):
                    to_remove = True
                    break

        if not to_remove:
            optimized_lines.append(line)

    return optimized_lines


def count_rule_types(lines):
    """
    统计各类规则的数量

    参数:
    lines (list): 规则列表

    返回:
    dict: 各类规则的数量统计
    """
    rule_counts = {}
    for line in lines:
        if ',' in line:
            rule_type = line.split(',')[0]
            rule_counts[rule_type] = rule_counts.get(rule_type, 0) + 1
    return rule_counts


def sort_rules(lines):
    """
    对规则进行排序

    参数:
    lines (list): 要排序的规则列表

    返回:
    list: 排序后的规则列表
    """
    rule_order = [
        "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-REGEX", "DOMAIN",
        "IP-CIDR", "IP-CIDR6", "GEOIP", "GEOSITE",
        "DST-PORT", "SRC-PORT",
        "PROCESS-PATH", "PROCESS-PATH-REGEX",
        "PROCESS-NAME", "PROCESS-NAME-REGEX"
    ]

    def get_rule_type(line):
        return line.split(',')[0] if ',' in line else ''

    def get_domain_or_ip(line):
        parts = line.split(',')
        return parts[1] if len(parts) > 1 else ''

    def domain_level(domain):
        return len(domain.split('.'))

    def ip_to_int(ip):
        try:
            return int(ipaddress.ip_address(ip.split('/')[0]))
        except ValueError:
            return 0  # 对于无效IP返回0

    def sort_key(line):
        rule_type = get_rule_type(line)
        try:
            rule_index = rule_order.index(rule_type)
        except ValueError:
            rule_index = len(rule_order)  # 将未知类型放到最后

        domain_or_ip = get_domain_or_ip(line)

        if rule_type in ["DOMAIN-SUFFIX", "DOMAIN", "DOMAIN-KEYWORD", "DOMAIN-REGEX"]:
            return (rule_index, domain_level(domain_or_ip), domain_or_ip)
        elif rule_type in ["IP-CIDR", "IP-CIDR6"]:
            return (rule_index, ip_to_int(domain_or_ip))
        else:
            return (rule_index, domain_or_ip)

    sorted_sections = []
    current_section = []

    for line in lines:
        if line.startswith('[') and line.endswith(']'):
            if current_section:
                # 对当前部分进行排序并添加到结果中
                sorted_sections.extend(sorted(current_section, key=sort_key))
                sorted_sections.append(line)  # 添加分组标头
                current_section = []
            else:
                sorted_sections.append(line)
        else:
            current_section.append(line)

    # 处理最后一组
    if current_section:
        sorted_sections.extend(sorted(current_section, key=sort_key))

    return sorted_sections


def generate_module_file(lines):
    """
    生成 module 文件

    参数:
    lines (list): 规则列表
    """
    # 确保 module 目录存在
    os.makedirs('module', exist_ok=True)

    # 清空 module 目录
    for file in os.listdir('module'):
        os.remove(os.path.join('module', file))

    # 统计规则数量
    rule_counts = count_rule_types(lines)
    rule_count_str = ' '.join([f"{k}:{v}" for k, v in rule_counts.items() if v > 0])

    # 获取当前时间（UTC+8）
    current_time = datetime.utcnow() + timedelta(hours=8)
    time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

    # 生成文件内容
    content = [
        '#!name=想你了',
        f'#!desc=Updated:{time_str} (UTC+8) Rlues:{sum(rule_counts.values())} ({rule_count_str})',
        '#!url=https://raw.angwz.com/beii.module',
        '[Rule]'
    ]

    current_group = None
    for line in lines:
        if line.startswith('[') and line.endswith(']'):
            current_group = line[1:-1]
        elif ',' in line:
            rule_type = line.split(',')[0]
            if rule_type in ['IP-CIDR', 'IP-CIDR6', 'GEOIP']:
                line = f'{line},{current_group},no-resolve'
            else:
                line = f'{line},{current_group}'
            content.append(line)

    # 写入文件
    with open('module/beii.module', 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))


def main():
    """
    主函数：执行整个处理流程
    """
    # 从URL获取配置
    url = 'https://raw.githubusercontent.com/angwz/DomainRouter/refs/heads/main/config/my.shadowrocket'
    print("正在从URL获取配置...")
    raw_lines = fetch_url_content_with_retries(url)
    print(f"成功获取 {len(raw_lines)} 行配置。")

    # 对列表内容进行预处理
    print("正在预处理配置内容...")
    preprocessed_lines = preprocess_lines(raw_lines)
    print(f"预处理后剩余 {len(preprocessed_lines)} 行。")

    # 对处理后的列表进行IP地址、域名和通配符域名判断和处理
    print("正在处理IP地址和域名...")
    processed_lines = process_ip_and_domains(preprocessed_lines)
    print(f"处理后共有 {len(processed_lines)} 行。")

    # 对列表进行合法性检查，保留有效元素
    print("正在进行合法性检查...")
    valid_filtered_lines = filter_elements_by_valid_prefix(processed_lines)
    print(f"合法性检查后剩余 {len(valid_filtered_lines)} 行。")

    # 进行优化：去重和覆盖范围优化，不改变规则顺序
    print("正在优化规则...")
    optimized_lines = optimize_rules(valid_filtered_lines)
    print(f"优化后剩余 {len(optimized_lines)} 行。")

    # 对规则进行排序
    print("正在对规则进行排序...")
    sorted_lines = sort_rules(optimized_lines)
    print("排序完成。")
    
    # 排序后再次优化
    print("再次优化一遍...")
    optimized_lines = optimize_rules(sorted_lines)
    print("最终优化完成.")

    # 生成 module 文件
    print("正在生成 module 文件...")
    generate_module_file(optimized_lines)
    print("module 文件生成完成。")

    print("处理完成，module 文件已生成。")


if __name__ == "__main__":
    main()