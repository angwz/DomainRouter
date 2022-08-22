# Clash_Rules

### 来源
 - 从 [LM-Firefly / Rules](https://github.com/LM-Firefly/Rules) 维护，规则数量最多，维护得最频繁，列表为不带短横线的list列表，需转换
 - 从 [Semporia / ClashX-Pro](https://github.com/Semporia/ClashX-Pro) 引用规则，规则数量类别多，规则数量一般
 - 从 [Loyalsoldier / clash-rules](https://github.com/Loyalsoldier/clash-rules) 引用规则，规则数量多

### [官方规则格式](https://lancellc.gitbook.io/clash/clash-config-file/rule-provider#example-of-a-rule-provider-file)
**If arule-provider file named as testproviderand behavior is domain:**
```
payload:
  - '.blogger.com'
  - '*.*.microsoft.com'
  - 'books.itunes.apple.com'
```
**If arule-provider file named as testprovider2and behavior is ipcidr:**
```
payload:
  - '192.168.1.0/24'
  - '10.0.0.0.1/32'
```
**If arule-provider file named as testprovider3and behavior is classical:**
```
payload:
  - DOMAIN-SUFFIX,google.com
  - DOMAIN-KEYWORD,google
  - DOMAIN,ad.com
  - SRC-IP-CIDR,192.168.1.201/32
  - IP-CIDR,127.0.0.0/8
  - GEOIP,CN
  - DST-PORT,80
  - SRC-PORT,7777
```

> 手动维护...
