# Python 规范

> **何时读**：编写或审查 Python 代码、新增 Python 模块、配置 Python 工具链时。
> **前提**：[../../core/coding-principles.md](../../core/coding-principles.md)、
> [../../core/engineering-principles.md](../../core/engineering-principles.md)。
> **优先级**：与 [../../core/security-principles.md](../../core/security-principles.md)
> 冲突时以安全规范为准。

---

## 1. 版本与运行环境

- 以项目声明的最低 Python 版本为准编写代码；不使用高于该版本的语法或标准库 API。
- 依赖锁定纳入版本管理；新增依赖必须获得授权，见
  [../../core/ai-behavior.md](../../core/ai-behavior.md) §3.3。
- 虚拟环境、解释器路径、包管理器由项目既有约定决定；不擅自更换。
- 脚本入口使用 `if __name__ == "__main__":`，不在模块导入时执行副作用。

## 2. 命名与结构

- 遵循 PEP 8 命名：`snake_case` 函数/变量、`CapWords` 类、`UPPER_CASE` 常量、
  `_` 前缀表示模块内部。
- 模块名短小、全小写、不用连字符；避免与标准库或已装第三方包同名
  （尤其 `json.py`、`types.py`、`email.py`）。
- 一个模块一个职责；`utils.py` / `helpers.py` 不作为新功能的默认落点。
- 使用相对导入还是绝对导入，遵循项目既有风格，不在同一次改动中混用两套。

## 3. 类型标注

- 公开函数、方法、类属性写类型标注；返回值必须标注，包括 `None`。
- 使用 `X | None` 表达可选值，不用 `Optional` 包裹后再用裸 `None` 兜底混用
  （以项目 Python 版本支持的语法为准）。
- 不用 `Any` 回避建模；与无类型第三方边界交互时，在边界上立即转换为明确类型。
- 有限取值用 `Enum` 或 `Literal`，不用裸字符串比较状态。
- 项目若启用了严格类型检查，改动后必须**实际运行**类型检查，见
  [../../core/testing-principles.md](../../core/testing-principles.md) §12。

## 4. 函数与控制流

- 优先早返回降低嵌套；不在函数末尾堆叠多层 `if/else`。
- 默认参数不用可变对象（`[]`、`{}`、`set()`）；用 `None` 作为哨兵并显式区分
  "未传"与"传了空值"。
- 生成器/迭代器用于大数据流，避免一次性全量载入内存。
- 装饰器保留原函数元信息（`functools.wraps`）；不在装饰器里隐藏 I/O 副作用。
- 不使用 `assert` 做运行时输入校验（可能被优化掉）；校验用显式条件 + 明确异常。

## 5. 异常与资源

- 捕获具体异常类型，禁止裸 `except:` 与 `except Exception: pass`。
- 重新抛出用 `raise`，包装用 `raise NewError(...) from exc` 保留 cause。
- 用 `with` 管理文件、连接、锁；自定义资源实现上下文管理器。
- 异常信息包含操作对象与上下文，不含凭据或完整请求体，见
  [../../core/security-principles.md](../../core/security-principles.md) §10。
- 不用异常表达"查无结果"这类正常业务结果。

## 6. 数据建模

- 值对象优先用 `dataclass(frozen=True)` 或 `NamedTuple`；不用裸字典在层间传递
  有固定结构的数据。
- 字典访问区分"键必然存在"与"可能不存在"：后者用 `.get()` 并显式处理缺失。
- 可变默认状态不放类属性；实例状态在 `__init__` 中初始化。
- 时间统一使用带时区的 `datetime`；不用 naive `datetime` 做业务判断。

## 7. I/O 与外部调用

- 路径用 `pathlib.Path`，不用字符串拼接；跨平台代码不硬编码 `/` 或 `\` 分隔符。
- 所有网络调用设置连接与读取超时、响应大小上限，并显式处理错误。
- 不用 `shell=True` 调用子进程；使用参数列表，见
  [../../core/security-principles.md](../../core/security-principles.md) §7。
- 数据库访问使用参数绑定，不拼接 SQL，见
  [../backend/database.md](../backend/database.md)。
- 日志使用 `logging` 模块，不用 `print` 作为运行时日志；结构化级别见
  [../../core/engineering-principles.md](../../core/engineering-principles.md) §9。

## 8. 测试

- 测试用 `unittest`（标准库）或项目既已采用的框架；不擅自更换测试框架。
- 测试函数命名 `test_<条件>_<期望行为>`；使用 `tmp_path` / 临时目录管理测试数据。
- Mock 遵守 [../../core/testing-principles.md](../../core/testing-principles.md) §10；
  数据库相关行为要有集成测试覆盖真实实现。
- 不把测试依赖真实网络、真实时钟或开发者本机路径。

## 9. 提交前自检

1. 格式化、lint、类型检查、测试、构建**实际运行**并记录结果。
2. 无未使用导入、无调试 `print`、无硬编码环境与密钥。
3. 公开函数有类型标注与文档字符串。
4. 新增依赖已获授权并写入锁定文件。
5. 异常路径与边界值有对应测试断言。
