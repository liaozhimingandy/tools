# API 设计规范

> **何时读**：新增或修改 HTTP/RPC 接口、错误码、分页、认证要求、契约文档时。
> **前提**：[../../core/architecture-principles.md](../../core/architecture-principles.md) §4（接口契约）、
> [../../core/security-principles.md](../../core/security-principles.md)（授权与注入）。
> 认证实现见 [authentication.md](authentication.md)，数据访问见 [database.md](database.md)。

---

## 1. 契约优先

- 接口的路径、方法、请求/响应字段、类型、错误码、状态码、幂等性、超时与限流
  必须在实现前定义清楚，并以可验证形式（schema / 类型 / 契约测试）固化。
- 契约变更按破坏性变更处理，见
  [../../core/engineering-principles.md](../../core/engineering-principles.md) §13 与
  [../../core/ai-behavior.md](../../core/ai-behavior.md) §3.5。
- 不暴露内部数据结构；内部模型重构不应迫使调用方改动。
- 优先"新增字段 + 并行运行 + 渐进淘汰"，不直接替换既有字段语义。

## 2. 方法与语义

- `GET` 只读取，无副作用、可缓存；`HEAD`/`OPTIONS` 同样不得改状态。
- `POST` 创建或触发非幂等操作；`PUT` 全量替换且幂等；`PATCH` 局部更新；
  `DELETE` 幂等（重复删除返回一致结果）。
- 写接口必须定义幂等策略（幂等键或自然键），并测试重复请求。
- 不用 `GET` 承载批量导出/删除等副作用，避免 CSRF 与爬虫误触发。

## 3. 请求与响应

- 请求体字段在**边界**校验：类型、必填、长度、范围、枚举、集合大小、格式。
- 响应结构稳定：成功与失败分别有固定形状；不因为某个分支返回不同顶层结构。
- 分页统一参数与返回（如 `page`/`page_size` + `total`/`items`），设置上限，
  不返回无界集合。
- 时间字段使用统一时区与格式；金额使用明确的单位与精度，不用浮点隐式表示。
- 不返回调用方无权查看的字段；列表接口逐条过滤权限，见
  [../../core/security-principles.md](../../core/security-principles.md) §13。

## 4. 状态码与错误

- 使用语义正确的状态码；不把所有失败都返回 `200` + 自定义 `code`，
  也不把所有异常返回 `500`。
- 错误响应包含稳定的机器可读错误码、可读信息、可选的请求 ID；
  **不得**包含堆栈、SQL、内部路径或敏感数据。
- 4xx 表示调用方可修正的错误，5xx 表示服务端故障；不混淆二者。
- 校验失败要指出具体字段，但避免泄漏"资源是否存在"以外的信息。

## 5. 认证与对象级授权

- 每个非公开接口在**服务端**独立完成认证与授权；前端隐藏、网关拦截都不是替代。
- 对象级授权按"当前身份 + 目标对象 + 操作"判定，不能只判断"已登录/有角色"。
- 批量、导出、管理端、内部接口、调试接口同样逐个校验对象权限。
- 身份来自可信会话/令牌，不信任请求体中传入的用户 ID，见
  [../../core/security-principles.md](../../core/security-principles.md) §1、§13。
- 多租户接口在数据访问层强制带租户条件，见
  [../../core/security-principles.md](../../core/security-principles.md) §14。

## 6. 注入与输入安全

- 查询参数、路径参数、请求体不得拼接进 SQL 或命令，见
  [../../core/security-principles.md](../../core/security-principles.md) §3、§7。
- 服务端代表用户发起的请求必须走目标白名单，防 SSRF，见
  [../../core/security-principles.md](../../core/security-principles.md) §6。
- 基于 Cookie 的状态变更接口必须有 CSRF 防护，见
  [../../core/security-principles.md](../../core/security-principles.md) §5。
- 文件上传按内容校验、服务端命名、不可执行存储，见
  [../../core/security-principles.md](../../core/security-principles.md) §11。

## 7. 版本与兼容

- 版本策略由项目既有约定决定；新增接口不擅自引入新的版本机制。
- 新增可选字段对旧客户端应无害；删除/改义字段必须走破坏性变更流程。
- 废弃接口保留至少一个版本周期，并在文档与响应中给出替代路径。

## 8. 性能与可靠性

- 所有外部调用设置超时、重试上限与退避；重试仅用于明确的瞬时故障。
- 避免 N+1 查询、无界 `SELECT *`、全量加载；见 [database.md](database.md)。
- 写操作明确事务边界与失败时的数据状态。
- 限流与配额防滥用与枚举，但不替代授权。
- 关键接口提供可关联的请求 ID，便于日志排查，见
  [../../core/engineering-principles.md](../../core/engineering-principles.md) §9。

## 9. 可观测与文档

- 每个接口文档写明：用途、认证要求、请求/响应 schema、错误码、限流、幂等性、示例。
- 日志与指标不记录敏感字段，见
  [../../core/security-principles.md](../../core/security-principles.md) §10。
- 契约必须有自动化测试覆盖：正常、校验失败、未认证、越权、错误分支、分页边界，
  见 [../../core/testing-principles.md](../../core/testing-principles.md) §4。
