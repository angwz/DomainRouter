# 欢迎使用适用于 Clash 的分流规则集

### 简单说明
本项目主要用于生成适用于 Clash 流量处理的规则集和策略组，并包括一些相关的工具配置文件的说明。

首先介绍仓库的构成，仓库中存在 main 和 release 分支。main 分支用于存放生成规则集的自动处理脚本、工作流文件及配置相关文件，结构如下：

<pre>
DomainRouter
├── main分支
│   ├── .github/              # 存放GitHub工作流的文件目录
│   ├── dnsmasq/              # 存放dnsmasq.conf所需的文本文件
│   ├── script/               # Python脚本
│   ├── subconverter_config/  # 与subconverter有关的配置和资源文件
│   ├── .gitattributes        # 用于定义特定路径或文件的属性
│   ├── my.wei                # 核心配置文件
│   └── README.md             # 描述整个项目的核心说明文件
│
└── release分支
    ├── class-domain/         # 由GitHub Actions工作流工作流生成的规则集文件
    ├── class-ipcidr/         # 由GitHub Actions工作流生成的规则集文件
    ├── class-classic/        # 由GitHub Actions工作流生成的规则集文件
    ├── **-domains.conf       # 由GitHub Actions工作流生成的适用于dnsmasq的白名单文件
    └── rulesets.toml         # 由GitHub Actions工作流生成的适用于subconverter的资源文件
</pre>

### 详细说明和使用指南

在访问全球互联网受限地区时，可能需要使用各种代理工具，如 VPN（Virtual Private Network）或支持流量加密和转发的代理客户端，以突破限制带来的不便。

在2024年，本项目主要用于为 Clash 提供更高级、更方便快速的代理使用方法。本人非开发者非程序员，99%以上的内容由 AI 构建。如有不合理、不科学、不适当的知识误区，请指正。接下来的内容将逐一概括项目涉及的各种内容和原理，最终目的是让更多人了解基本运行原理和流程，能够个人独立配置并使用。

有时，为了满足某些需求，例如下载文献、下载开源项目、观看 Biden 和 Trump 的辩论直播或观看星舰发射，您需要访问在大陆部分受限或完全受限的内容。由于出现的各种不稳定、中断和卡顿可能会让您感到恼怒，您可能会开始好奇并了解为什么会导致这种情况。在了解到 GFW 可能对我们访问互联网产生消极影响时，可能会想要突破限制。此时，大多数人会找到一些方法得以初步访问国际互联网，例如 Chrome 插件、Warp 客户端或其他一些免费代理软件。随着时间推移，可能会接触到更高级的一些工具，例如 VPS 和机场。

#### Q：为什么会随着时间推移使用各种不同甚至更加复杂的代理工具？
A：流量加密代理和 GFW 的关系大致可以比作“矛”与“盾”。随着时间推移，用户对某些代理方式应用的规模增大，GFW 对加密流量的特征探测会越来越有针对性，对我们来说就意味着网络封锁变得越来越严，用户需要更灵活的代理工具来绕过这些限制、保护隐私和提高安全性。同时，大家的需求越来越多样化，免费的工具可能伴随着高延迟、断连和流量限制等问题，简单的工具已经不够用了。新技术的发展也让代理工具变得更高效、更好用，帮助我们在各种情况下顺利上网。

#### 什么是 Clash？
Clash 可以称作一种代理工具，支持多种代理协议，具体支持的协议取决于其内核。Clash 是一个统称，特指能以 Clash 内核运行的代理工具的集合，是运行在客户端的软件代理方式。由于一些原因，目前只有 Clash Meta 内核保持着半更新和维护状态，但依然可以满足大部分复杂和定制化的代理需求。以 Clash 内核运行的代理工具，如果您有一个机场订阅，Clash 工具能以预设的策略和域名规则集对流量进行精准分流。一般来说，机场默认的分流规则或第三方规则已经尽可能覆盖全面和完善，但具体使用时可能仍会遇到各种小问题，有时还需要手动切换节点。因此，本项目旨在提供自动化运行流程和生成一劳永逸的规则文件。如果您想配置个性化的分流规则，本项目也可以为您提供一些引导。

#### 使用指南：
在你熟练使用在 Clash 或者 sing-box 等客户端使用机场订阅后，当你有希望更精细化分流或者让一些特定域名流量走特定路线的需求时，可以尝试直接使用 release 分支的规则；亦可 Fork 本项目后适当修改代码，能得到更满足你一个人需要的分流规则。

无论你是有哪种需求，首先你需要安装对机场订阅进行转换的服务，subconverter 正是能是能提供订阅转换的一种服务，如果不担心机场订阅的泄露风险，你可以在 Google 搜索'机场订阅转换'，得到各种可用的 subconverter 转换服务，对你的机场订阅进行转换，最后导入到 Clash。

如果你有更高隐私要求或者需要更个性化分流规则，则根据接下来的教程操作：

 * 在你的 PC、软路由或者 VPS 上等任意主机安装 subconverter 服务。

 * 这里有几个可选仓库：

- [Subconverter 官方仓库](https://github.com/tindy2013/subconverter)（不支持 VLESS、Hysteria2）
- [MetaCubeX/subconverter](https://github.com/MetaCubeX/subconverter)（Clash Meta 项目作者 Fork 的版本，增加了对 VLESS、Hysteria2 的支持）

 * 参考 [Subconverter 官方文档](https://github.com/tindy2013/subconverter/blob/master/README-cn.md)进行配置。服务的配置文件会按照程序目录的 `pref.toml`、`pref.yml`、`pref.ini` 的优先级顺序加载。

 * 如果你的机场订阅不包含 VLESS 节点和 Hysteria2 节点，以 VPS 上的 Ubuntu 主机举例，则可在终端执行下列命令:
 * 安装和运行 subconverter

```bash
wget https://github.com/tindy2013/subconverter/releases/download/v0.9.0/subconverter_linux64.tar.gz
tar -xzvf subconverter_linux64.tar.gz
chmod +x subconverter
./subconverter
```
 * 开放 subconverter 端口
```bash
sudo ufw enable
sudo ufw allow 25500
```

 * 此时 subconverter 在你的 VPS 上 25500 端口提供服务

 * 在浏览器输入 http://{ip}:25500 并访问，如果页面显示 HTTP ERROR 404，则 subconverter 服务已成功在服务器上运行被能被公网访问。

 * 如果你想定制符合自己需求的配置文件，可 Fork 本仓库，my.wei 是用于生成规则集的核心配置文件。可结合代码自行更改。

 * 由于事务繁忙，后续使用指南日后再补充。