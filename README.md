# Atomic to FA PRD

将 MCP、CLI、API 或工具能力转成 **PA 调用的纯语音 FA 产品 PRD**。包含一个统一入口与七个配套专家 skill，适用于支持多 Agent 与本地文件操作的 Codex / Claude Code 环境。

- **PA**：个人助手 / OS 入口；**FA**：独立业务 Agent。产品无 UI。
- 从原子能力、常用任务、跨能力编排、开发者文档及示例四路发现需求。
- 角色链路：能力尽调 → 领域调研 → 产品设计 → 语音交互 → 测试 → 独立评审 → 产品负责人收敛。
- 交付：固定六章 PRD、研发附录、两张飞书原生可编辑流程图，以及独立 Query 测试表。
- 原始要求逐项处置，跨阶段版本、文件哈希与消费回执核验，检查需求、交互、图、用例的一致性。

## 安装

```bash
git clone https://github.com/songyang753-cloud/atomic-to-fa-prd.git
cd atomic-to-fa-prd
python3 install.py
```

安装程序将八个 skill 复制到 `~/.agents/skills`，并在 `~/.codex/skills` 和 `~/.claude/skills` 建发现链接。已有同名内容时停止，避免覆盖自定义技能。Python 3.10+；检查脚本仅使用标准库。

## 使用

在 Agent 中明确调用 `atomic-to-fa-prd`，例如：

> 使用 atomic-to-fa-prd。我提供以下 MCP 开发者文档及接口；PA 可提供定位、思考及用户记忆，其他能力待核实。请基于实际能力设计纯语音 FA，完成需求、交互、测试及独立评审，最后新建飞书 PRD。

同时提供原子能力入口及开发者文档、PA基线、业务约束、验证权限，以及飞书目标空间。安全查询应实际验证；下单、支付、取消等真实操作须单独明确授权。

## 飞书及研究依赖

本仓库包含八个产品与交互专家 skill，不包含第三方工具或凭据。完整飞书发布还需配置官方 `@larksuite/cli`、自己的 OAuth/profile、文档/画板/电子表格权限，并准备可用的 `lark-doc`、`lark-whiteboard`、`lark-sheets` skills 或明确等价的已验证实现。SYBuilder/product-flow 是可选方法参考，不是运行必需包。

首次配置时将技能中的 `<your-profile>` 替换成自己的 profile，或由 Agent 解析用户提供的配置。无发布能力时可以生成本地设计稿并报告阻塞；本地 Mermaid / JSON / 图片不满足“飞书原生可编辑图”的交付标准。不要自动沿用原作者的组织、账号或项目基线。

## 项目检查

```bash
python3 skills/atomic-to-fa-prd/scripts/check_project.py /path/to/project/project.json
```

项目数据格式与各阶段交付标准见 `skills/atomic-to-fa-prd/references/`。结构检查、独立语义评审、真实业务执行和远端交付分别报告；检查器通过并不自动证明业务成功。不存在真实FA或设备入口时，执行标记为 blocked / NOT_RUN。

## 包含内容

| Skill | 职责 |
|---|---|
| atomic-to-fa-prd | 统一组织、交接、验收 |
| fa-capability-analysis | 文档尽调、能力验证、可实现性 |
| fa-domain-research | 领域与同类产品研究 |
| fa-product-design | 需求与功能设计 |
| voice-interaction-design | 语音交互与恢复规则 |
| fa-test-engineering | 用例、执行、缺陷回归 |
| fa-prd-review | 独立多视角评审 |
| fa-product-owner | 裁决、正文附录收敛及发布 |

## 公开包边界

本包移除了内部飞书链接、个人账号配置和历史项目凭证；不包含瑞幸真实接口凭据、业务数据或内部PRD。六章正文结构、指标口径和原生图/测试表交付要求保留。来源与方法参考见各 skill 的 references；项目专属规则需要使用者重新确认。
