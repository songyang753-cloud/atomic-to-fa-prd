# 产品 → 交互 → 研发：交接合同 v1

本合同用于已确认范围的生成与检查，不增加 PRD 正文目录。atomic 负责目标、范围、能力事实；voice 负责轮次、话术、修复和节点；研发负责实现执行检查。用户约束与其授权的产品负责人决定工作范围，提供方定义接口事实，平台证据定义可用设备能力。发生冲突显式记录并解决，不以生成的 JSON 取代用户决定。

## 最小交接与消费

任务目录保存两份 JSON：`handoff.json` 是交互输入，`interaction.json` 是交互返回；正文、附录和证据可以是原有文件，无须另造系统。输入冻结后先计算 SHA-256，交互结果引用它。所有产物使用同一 revision。修改输入则重算哈希，重新检查受影响内容；范围/优先级变化由产品负责人在既定能力和用户约束内裁决，同步修改交付件并让受影响角色重新验收。保留稳定功能编号，已废弃编号不再改指其他含义。

输入字段：
- `schema_version: 1`、`revision`、`mode: capability-bounded | target-experience`、`approval`（范围决定、授权原话和来源；允许记录产品负责人基于用户授权的决定）。目标态必须有 `target_experience_authorization`；默认按现有能力闭环。
- `capabilities`：id、来源、验证状态；`platform`：已核实能力、未核实依赖及退路。证据标明原时间/位置/哈希；禁止凭据。
- 若本轮生成了 `discovery.json`，增加 `discovery_source`（path、sha256）；输入 features 仅取产品负责人冻结的 include，保留稳定 id、priority、完成终点与限制。发现记录留存候选取舍和需求证据，不另作已确认范围的正本；重跑先保留旧基线，负责人决定新基线后重发同版合同。
- `features`：id、priority、goal、end_condition、capabilities（能力 id）、limits。每项本期功能有依据，不能用一个查询支撑无依据的交易。
- `critical_rules`：id、feature_ids、自然语言 statement、owner、condition、allowed_action、forbidden_effect、fallback。只编号影响业务后果的规则。
- `metrics`：`precision_min: 0.95`、`recall_min: 0.95`、`first_audio_p50_max_ms: 1000`、`first_audio_p95_lt_ms: 1500`、`task_completion_min: 0.90`。这是本模板建议目标，实测另列；有效答复时延按业务定义。首词从实际说话结束到设备开始播放，任务完成分母保留放弃和外部失败。

返回字段：
- `schema_version`、`revision`、`input_sha256`；`features` 原样继承 id 与 priority。
- `nodes`：id、feature_ids、role、trigger、utterance、next（节点 id 列表）、terminal（布尔）、actions（能力 id）。具体条件分支和行为写入节点；共用修复注明代入话术。只给下一节点列表不能代替语义设计。
- `rule_coverage`：rule_id、owner、guard（执行前必须核对什么）、node_ids、case_ids、status。
- `cases`：id、rule_ids、given、events、expected、forbidden_effects、verification（design / mock / live-query / live-write / device / performance / not-run）、evidence。案例必须有可观察结果与禁止副作用，执行过才引用记录；未执行明确标 not-run。
- `gaps`、`change_proposals`（未批准变更不进入当前 features）、`metrics`、`artifacts`（每项 kind、path、revision、sha256）。必有 body、appendix、flow-source，图从同一 flow-source 投影。

交互方必须先阅读输入再生成返回；产品方消费返回时核查范围、能力、规则与正文一致，研发方必须同时阅读正文、附录和返回合同。可以在案例证据里增加实际工具调用次数、对象、状态及原始事件记录，不要求通用事件数据库。

## 关键规则必须落到动作和用例

对每条适用规则说明：执行责任、进入条件、允许动作、禁止副作用、条件不成立时的退路、影响节点和具体案例。确认必须绑定当前对象、关键条件、有效报价及呈现证据；修改使受影响授权失效；无明确确认不得执行高后果动作。播放回执由 PA 提供，FA 提交前核对；尚无回执契约就列阻塞，不能捏造已播事实。

结果未知保留原执行；能定位才查询，没有标识则说明受阻，不盲目重试。重复提交须有确定性抑制；本地记录只覆盖相应进程/存储范围，跨崩溃保证还需幂等或可定位契约。停播与取消业务分别处理。候选/报价的迟到结果按版本抑制，已发出交易的迟到结果仍记录并处理。服务端营业状态、取消资格、费用及退款须有证据。

## 三层验收与失败注入

1. 运行 `python3 scripts/check_handoff.py <handoff.json> <interaction.json>`：核查输入哈希、同版产物、范围优先级、能力引用、节点去向、关键规则到节点/用例的双向引用、规则责任、指标和文件完整性。路径相对 interaction.json。结构通过后仍需逐条语义走查；检查器无法判断自然语言是否正确。
2. 语义走查：从冻结的规则独立推导预期，核对节点、正文、两图投影和案例，不从生成结果反推“正确答案”。关键规则须全部通过。模拟回放记录动作次数、对象和状态；使用独立于执行模型的固定预期。主动破坏授权失效、未知恢复、停播/取消等规则，必须看到验收失败。结构反例另覆盖混版、额外功能、指标漂移、孤立规则；每个反例记录实际报错。
3. 真实联调：服务写入、PA/FA、播放回执、设备与性能分别验收。设计、模拟、历史查询重放各自报告，不能升级成真实交易通过。普通体验评分不能抵消关键规则失败。

图的语义、原生可编辑、视觉分别检查；发布时回读实际节点与预览，拖动自动跟线仅在做过相应验证后声明。本地回归保留已有资源引用，标明历史证据，不操作远端。能力探索需要实际安全查询；回归采用 evidence-replay 时校验已有证据哈希和原时间，明确没有新服务调用。

## 变更与就绪

每个功能分别报告设计、契约、模拟、查询、写入、PA/设备、性能状态。任何关键契约未定都写清责任方、受影响节点、当前退路和验收方法。变更按功能→规则→节点→话术→图→案例检查，保留无关有效内容。缺陷形成改进建议；只有用户授权才维护 skill。飞书发布授权、当前远端版本和完整回读沿用主 skill，不由合同代替。
