# 测试 Agent 消费、执行与研发验收

只补充内部流程和研发附录；六章正文、两张原生图、五项指标及独立飞书测试表不变。复用 corpus.json/cases.jsonl，执行结果另存，绝不改写冻结预期。

## 先接收，再执行

主入口调用 `fa-test-engineering` 指定独立测试 Agent；用例生成、执行与缺陷回归由同一角色贯穿，独立评审负责复核。它先读取同版正文、附录、能力、交互、两图源和用例，交付 intake（revision、consumer_agent_id、corpus引用、与corpus一致的sources引用、capability_modes只读/写入/未知分类及依据）：输入哈希、可执行/阻塞 case、缺少的夹具与接口、执行通道、安全边界、判据及所需证据。由产品/能力/交互接受方确认疑点；不能消费就退回具体字段或场景，不把收到文件当完成交接。

执行前固定 target（实现版本/入口/配置）、用例及预期哈希、环境、隔离方式、授权范围。没有真实 FA 入口，实际 FA 用例标 blocked；可另做参考 Agent 文本事件模拟或历史回放，target 与报告注明对象，只支持该通道结论。测试 Agent 不能用自己编写的理想答案充当被测输出；输出由独立被测 Agent/程序生成，评分在输出之后进行。留出集预期不交被测 Agent。交付给被测对象的输入须裁剪掉interaction.cases、Query冻结预期、评分断言及同族历史答案；只传必要实现合同和本例输入。若已读到预期，标合同驱动参考模拟，不能报告盲测。

按通道分别运行：design 不运行；mock 在隔离夹具中；evidence-replay 重放既有真实回执；live-query 使用合法输入实际查询；live-write 须有与动作/对象/环境匹配的明确用户授权；device/performance 要有设备/计时记录。能力方在intake中冻结风险分类及依据；所有真实通道（含device/performance）对未知副作用阻塞、写动作核验授权。工具名或HTTP方法不决定副作用；测试授权不覆盖真实交易。mock不外发写请求；超时或结果未知不自动重试写入。

## 执行结果与判定

每次执行保存 execution.json：
- revision；corpus:{path,sha256}；target:{kind,version,entrypoint}；consumer:{agent_id,intake:{path,sha256}}。
- runs：每例 case_id、method、status、reason、evidence:[{path,sha256}]。blocked/not-run 写缺项和下一步；pass/fail 必有证据；mock还须填写isolation说明夹具隔离和零外发写入。
- pass/fail 证据 JSON 必含 target_version、case_id、method、observed:{actions:[{capability_id,target}],outcome,forbidden_effects:[]}、assertions:[{kind:outcome|forbidden,status:pass|fail,basis}]。actions 记录实际调用/模拟动作，不复制预期；basis 定位实际输出或trace。对象语义与outcome由独立评分者核对，动作计数由脚本复算。fail 必有失败断言或动作/禁止行为违规。
- live-write 的 run 另附 authorization:{path,sha256}，证据说明授权来源、动作、对象、环境与有效范围；评分者核对实际动作范围。设备/性能证据保留实际事件时间及采样条件。
- findings：问题、证据、影响case/规则、负责人、修复版本、重跑结果；测试 Agent 不修改产品预期。实现缺陷交研发修复；规格歧义交产品负责人裁决，再由能力/交互/测试重验。失效结果保留历史，新版重跑受影响场景和关键反例。

运行 `python3 scripts/check_execution.py execution.json` 核对引用、逐例完整性、实际动作次数、禁止行为、结果断言和授权凭证。脚本不能证明自然语言对象匹配、证据真实性或业务正确，独立评分必须实际阅读证据。执行报告分别列各通道 pass/fail/blocked/not-run；缺入口的 blocked 不影响文档设计交付，仍阻塞对应实现验收。

## 关键规则研发验收

每条 critical_rule 在附录建立 acceptance.json 的 rules 条目：rule_id、owner、implementation（status:pending|implemented、entrypoint、version）、inputs、guard、on_reject、positive_case_ids、negative_case_ids、assertion、evidence、status:blocked|pass|fail。每条case必须在统一正本且引用该规则。项目若确无正分支，写 positive_exception 与理由，不伪造正例；负例不可省。脚本检查引用，独立技术/测试评审检查场景是否真的正负成对。

- inputs：执行判断真正读取的字段/事件/回执及提供者；缺失、过期、乱序时如何判定。
- guard：执行前可观察的检查条件；on_reject：缺条件时阻断什么、保留什么、用户下一步。
- assertion：允许路径的实际动作/次数/对象与拒绝路径零副作用，并核对结果反馈。
- owner：落实到PA/FA/适配层等责任边界；代码位置未提供就pending，不虚构模块或实现已存在。
- pass 需 implemented、实际实现入口与版本、正负分支执行证据；参考Agent、历史回放或文档走查只能验证设计，保留blocked及已完成的设计检查。设备依赖须有相应回执。

优先验收本项目真正有风险的规则：当前对象/版本与确认绑定、摘要实际呈现、改动后授权失效、重复/迟到事件、未知结果恢复、停播与取消分离。不要为普通查询增加交易门禁。

## 关闭与交付

测试消费者出具消费回执与分层执行报告；研发给实现及规则验收证据；独立评审复核，负责人收敛。执行结果通过case ID回链至测试表，发布时保留冻结预期与最新执行状态/证据入口；用户只授权本地时仅生成本地附件，不写飞书。附录保留 intake、规则验收、执行结果、缺陷及重跑索引，正文不增加章节或过程说明。


## 缺陷回归记录

在工作区/附录保存defects.json；每项包含id、status（open/assigned/fixed-pending-retest/closed）、severity、case_ids、rule_ids、evidence、expected、actual、owner、close_when、fix_version、reruns。每次rerun记录目标版本、环境、用例ID及execution回执引用。blocked不是缺陷修复证据；无法复现可记录原因并保持待核实，不静默关闭。

fixed-pending-retest须有修复说明与版本；closed须有原失败例和受影响/关键反例的复验记录、满足close_when的证据及独立复核者。规格修改另记负责人裁决、预期变更原因与新哈希；原失败和旧预期保留。两轮仍失败则报告开放问题，不通过放宽预期收敛。
