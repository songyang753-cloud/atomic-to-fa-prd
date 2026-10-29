# 统一项目验收

当前项目执行 `python3 scripts/check_project.py <project>/project.json`。独立检查器保留为定位及历史复查工具；新项目必须通过统一入口。它依次执行协作、发现、信息保全、产品交互交接、统一用例、执行与关键规则验收、缺陷检查，任一失败即整体失败。历史格式不能绕过新版发现和原始要求基线。

project.json：`project_version:1, revision, mode:local|published, producer_agent_ids:[], inputs:{...}`。inputs 必须包括 collaboration、discovery、continuity、product、interaction、corpus、execution、acceptance、defects、semantic_review，各值为 `{path,sha256,revision}`。引用同一轮冻结文件，不复制业务规则。所有源文件及间接引用变更后重新生成哈希和消费验收。

semantic_review 为独立终审者实际读取同版产物的记录：`revision, reviewer_agent_id, status:pass|fail, input_hashes:{输入名:sha256}, checks:{检查名:{status,evidence}}`。input_hashes 包含其余九个输入的实际哈希。检查名为 original-requirements、capability-boundaries、body-appendix、flow-text、rules-cases、metrics、correctness。evidence 给具体原件位置、图边、用例及结论。主持及产物生产者不能充当终审者。检查器校验记录完整性；实际消费与结论真实性仍由独立审阅承担，不能预填通过。

通过含义：同版交接和已登记检查通过。runtime 单独返回 blocked、recorded-fail 或 recorded-pass，具体方法仍按执行回执读取，模拟不能称真实业务通过。local 的 delivery 固定 not-run；published 还须 collaboration=delivered 及其原生图文回读检查。发布时另核测试表全量行内容、版本、链接及两图原始节点和预览，不能只检查链接存在。关键规则无真实实现时保留研发 blocked，允许设计交付但不称上线就绪。

原始要求及语义回归覆盖附近门店地址查询、真实字段排序、可查询候选范围、完整点单主流程、修改后重预览、未知结果恢复；顺路与他人偏好分别核路线/记忆合同，缺依赖降级或转缺口。暂缓认证及个人信息继续只登记范围决定。

维护时至少破坏一个缺失检查、一个旧 schema、一个过期哈希和一个缺原始要求处置，证明入口能阻断；另由独立 Agent 反查规则冲突、图边与用例预期。正文模板与远端交付形式保持原样。

发布模式另在 project.json 提交 publication：`revision,corpus_sha256,table_url,status:readback-pass,sheets:{标注query:{expected:{path,sha256},readback:{path,sha256}},泛化query:{expected:{path,sha256},readback:{path,sha256}}}`。expected 来自同版 corpus 的完整发布投影，readback 来自官方 CLI 全量回读；两者均还原为完整 case 对象数组（含所有字段），按 id 排序后输出 JSON；检查器从 corpus.cases 重新读取标注和泛化记录，逐字段核对 expected，避免相同空快照绕过。检查器核对两张 sheet 快照文件哈希及内容一致；远端真实来源由独立评审核验，禁止自行复制 expected 冒充读回。缺失或不一致阻断 published。
