# DomainRouter v2 实施规范：交接入口

版本：1.5 · 日期：2026-11-08 · 适用环境：新电脑、已创建但尚无实现的 `domainrouter_v2` 工作区

本交接包只包含文档，尚未实现 v2、编写工作流或启动每日任务。它保留了完整的输入语义、算法、MRS 接入、验证和开源实施要求，供 Claude Code 后续编码。原单文件已拆为以下四份分册，全部共同生效；本入口不能代替正文。

## 在新电脑上开始

1. 把交接 ZIP 传到新电脑，解压后将整个 `docs/` 放在 `domainrouter_v2` 项目根目录下。不要多套一层 `domainrouter_v2`；解压后应能看到 `domainrouter_v2/docs/v2-implementation-spec.md`。
2. 用 VS Code 打开 `domainrouter_v2`，确认以下六个 Markdown 文件都在工作区里。
3. 聊天框只粘贴 [claude-code-start.md](claude-code-start.md) 的短提示语，让 Claude Code 自己读取入口和四份分册。也可用文件 @ 引用选择该入口；不要把全部正文合并粘进聊天框。
4. Claude Code 按第 0.1 节只读获取旧仓库的固定提交，然后在当前工作区新建实现。新电脑无需有旧工程目录，也不使用旧电脑的用户名或盘符。

## 规范文件与阅读顺序

| 顺序 | 文件 | 必读内容 |
| --- | --- | --- |
| 1 | [01：基础、输入与来源](v2/01-foundations-and-input.md) | 第 0～6 节：空工作区启动、远端迁移、命名、语义、解析、来源与快照 |
| 2 | [02：核心架构、算法与排序](v2/02-engine-and-algorithms.md) | 第 7～10 节：模型、no-resolve、通配包含、去重合并、分区与排序 |
| 3 | [03：产物、兼容、验证与 CLI](v2/03-artifacts-and-verification.md) | 第 11～14 节：MRS/TOML/base、subconverter 接入、正确性与性能、命令契约 |
| 4 | [04：每日生成、开源交付与实施](v2/04-delivery-and-handoff.md) | 第 15～19 节：每日自动化、发布一致性、开源交付、阶段与启动提示 |
| 启动 | [短提示语](claude-code-start.md) | 仅此内容需要粘贴；与第 19 节保持一致 |

以上四份分册都低于 50,000 字符。使用文件读取工具时也应逐份或分段读取，不能把工具截断当作已经读完。

快速定位：[输入语义](v2/01-foundations-and-input.md#input-semantics) · [核心架构](v2/02-engine-and-algorithms.md#core-architecture) · [优化算法](v2/02-engine-and-algorithms.md#optimization) · [排序](v2/02-engine-and-algorithms.md#ordering) · [产物](v2/03-artifacts-and-verification.md#outputs) · [兼容](v2/03-artifacts-and-verification.md#compatibility) · [验证](v2/03-artifacts-and-verification.md#verification) · [实施阶段](v2/04-delivery-and-handoff.md#milestones)。

## 本版特别确定的三件事

- **新电脑从空目录开展**：项目根是当前 VS Code 工作区。旧项目只读来源为 [angwz/DomainRouter](https://github.com/angwz/DomainRouter)，固定参考提交 `5bcb86f540883712726d37129c5ff493585be6bb`；具体文件与获取方式见第 0.1 节。规范本身使用本地交接包，不假设未提交的规范已在旧仓库公开。
- **三类规则每天生成**：每日刷新上游来源，生成 domain MRS、ipcidr MRS、classical YAML 与同代配套配置，验证成功后统一发布；空分区省略。默认香港时间 04:17，由 GitHub Actions 执行，新电脑无需常开。每日流程实现属于 M4a，实际远端启用属于 M4b，见第 15.5 节。
- **编码阶段与外部启用分开**：下一位实施者按 M1→M2→M3→M4a 编码和验证，Web/AI 暂不做；创建/推送远端、实际发布和 VPS 切换另行接入。当前交接不表示这些操作已经执行。

项目标识统一 `domainrouter_v2`，产品显示为 `DomainRouter v2`。最终开源许可仍须在首次正式开源发布前确定，不阻塞独立核心开发。

## 版本与状态

1.5 包含先前 1.4 的完整算法和验收要求，并补充新电脑迁移、文件交接和每日生成。本轮只修正文档、拆分与打包；所有回归场景仍是待实施的验收要求，未声称已经运行内核或生产验证。
