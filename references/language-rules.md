# 各语言规范要点（Python / JavaScript / TypeScript / Java）

> 用于整理代码时的命名规范、结构规范与风格约定。整理时遵循"项目内一致性优先"——若项目已有既定风格，优先服从现有风格而非强行套用本规范。

## 一、Python

### 命名规范（PEP 8）

| 对象 | 风格 | 示例 |
|------|------|------|
| 模块/文件名 | snake_case | `user_service.py` |
| 类名 | PascalCase | `UserService` |
| 函数/方法 | snake_case | `get_user_by_id()` |
| 变量 | snake_case | `user_count` |
| 常量 | UPPER_SNAKE | `MAX_RETRY = 3` |
| 私有成员 | 单下划线前缀 | `_internal_helper()` |
| 强私有 | 双下划线前缀 | `__private` |

### 结构规范

- 每个 import 独占一行，按「标准库 → 第三方 → 本地」分组，组间空行分隔。
- 顶层函数与类之间用两个空行分隔，方法之间一个空行。
- 优先使用类型提示（type hints）。
- 仅可执行脚本需要 `if __name__ == "__main__":` 入口；库模块不需要人为添加。
- 尊重项目已有导出约定；显式 `__all__` 与包初始化导入可能是公共 API，不作为默认清理项。

### 常见清理项

- 未使用的 import（`detect_dead_code.py` 可检出）。
- 用 `with` 管理资源，避免手动 `close()`。
- 字符串格式化优先 f-string（Python 3.6+）。
- 避免可变默认参数（`def f(x=[])`）。

## 二、JavaScript / TypeScript

### 命名规范（Airbnb / 社区通用）

| 对象 | 风格 | 示例 |
|------|------|------|
| 文件名 | kebab-case 或 camelCase（React 组件用 PascalCase） | `user-service.js`、`UserCard.tsx` |
| 类/组件 | PascalCase | `class UserCard` |
| 函数/变量 | camelCase | `getUserById()` |
| 常量 | UPPER_SNAKE（全大写下划线） | `MAX_RETRY` |
| 私有字段 | `#` 前缀（TS/ES2022）或 `_` 前缀 | `#cache`、`_internal` |
| 布尔变量 | `is`/`has`/`should` 前缀 | `isLoading`、`hasError` |

### 结构规范

- 优先 `const`，其次 `let`，避免 `var`。
- 使用 ES Modules（`import`/`export`），避免 `require`（除非 CommonJS 环境）。
- TS 的 `interface` / `type` 遵循项目已有约定，不为风格偏好改写公开类型。
- 避免 `any`，必要时用 `unknown` + 类型收窄。
- 组件保持单一职责，抽出可复用 hooks / 子组件。
- 使用可选链 `?.` 和空值合并 `??` 替代冗长的判空。

### 常见清理项

- 未使用的 import / 变量（ESLint 的 `no-unused-vars` 对应）。
- 深层回调改为 async/await 或 Promise 链。
- 重复的组件样式/逻辑抽取为共享模块。
- 移除 `console.log` 调试残留。

## 三、Java

### 命名规范（Oracle 官方 / 阿里 Java 规范）

| 对象 | 风格 | 示例 |
|------|------|------|
| 包名 | 全小写，点分隔 | `com.example.user` |
| 类/接口 | PascalCase（UpperCamelCase） | `UserService` |
| 方法 | camelCase（lowerCamelCase） | `getUserById()` |
| 变量 | camelCase | `userCount` |
| 常量 | UPPER_SNAKE | `MAX_RETRY_COUNT` |
| 枚举 | PascalCase，常量全大写 | `Status.SUCCESS` |

### 结构规范

- 一个文件一个公开类，文件名与公开类名一致。
- 字段按「常量 → 静态 → 实例」顺序，方法按职责分组。
- 接口与实现分离（`UserService` + `UserServiceImpl`）。
- 优先使用 `private` 最小可见性。
- 避免过深的包层级（一般不超过 5 层）。

### 常见清理项

- 未使用的 import（IDE 会标灰）。
- 用 `try-with-resources` 替代手动 `finally close()`。
- 用 `Optional` 避免返回 `null`（需判断适用场景）。
- 用 `StringBuilder` 处理循环拼接字符串。
- 修改 getter/setter 前检查序列化、反射和框架约定；不为清理引入 Lombok。

## 四、通用整理原则

1. **一致性优先**：若项目已有既定风格，服从现有风格，不要为了"标准"破坏一致性。
2. **最小改动**：整理时只改该改的，避免顺手重构无关代码。
3. **命名要表达意图**：优先改"神秘命名"（`data`、`tmp`、`foo`），这是性价比最高的整理。
4. **删除依赖版本控制**：删代码前确认已纳入 git 等版本管理，可随时回溯。
5. **改完即验证**：每批改动后跑测试/编译，确认无回归。
