# social-mcp

> [English](README.md)

基于浏览器自动化的 MCP (Model Context Protocol) 适配器，支持小红书和 Twitter/X。

**小红书服务器** 使用 Playwright (Chromium) 进行完整的浏览器自动化操作——支持扫码登录、笔记发布、评论、点赞、收藏等功能。
**Twitter 服务器** 封装了 [twitter-cli](https://github.com/jackwener/twitter-cli)，提供限速的 MCP 适配。

## 前置条件

- Python 3.10+
- Chromium（Playwright 会自动安装）

## 安装

```bash
# 1. 安装本项目
git clone https://github.com/TheOneAC/social-mcp.git
cd social-mcp
pip install -e .
python3 -m playwright install chromium

# 2. （可选）Twitter 需要安装底层 CLI 工具
pipx install twitter-cli

# 或直接从 GitHub 安装：
# pip install git+https://github.com/TheOneAC/social-mcp.git
```

## 配置

### Twitter/X

设置以下环境变量：

```bash
export TWITTER_AUTH_TOKEN="your_auth_token"
export TWITTER_CT0="your_ct0_cookie"
```

> **获取方式**：在浏览器中登录 twitter.com 后，打开开发者工具 → Application → Cookies → 找到 `auth_token` 和 `ct0`。

### 小红书

使用 MCP 工具的 `login` 命令通过扫码登录。会话会自动持久化到本地磁盘，无需额外配置。

## 使用

每个平台作为一个独立的 MCP 服务器运行（基于 stdio）：

```bash
# 小红书服务器
social-mcp-xhs

# Twitter 服务器
social-mcp-twitter
```

### Claude Code

添加到 `~/.claude.json` 或项目下的 `.claude.json`：

```json
{
  "mcpServers": {
    "xiaohongshu": {
      "command": "social-mcp-xhs"
    },
    "twitter": {
      "command": "social-mcp-twitter"
    }
  }
}
```

### 自定义 CLI 路径（仅 Twitter）

通过环境变量覆盖默认的 CLI 路径：

```bash
export XHS_CLI_PATH="/custom/path/to/xhs"
export TWITTER_CLI_PATH="/custom/path/to/twitter"
```

## 工具列表

### 小红书

| 工具 | 说明 |
|---|---|
| `login` | 扫码登录（基于浏览器） |
| `logout` | 清除登录会话 |
| `status` | 检查登录状态 |
| `whoami` | 查看当前登录用户信息 |
| `search` | 按关键词搜索笔记 |
| `feed` | 浏览推荐流 |
| `hot` | 按分类浏览热门笔记 |
| `read` | 按 ID 查看笔记详情 |
| `comments` | 查看笔记评论 |
| `user` | 查看用户信息 |
| `user-posts` | 列出用户发布的笔记 |
| `search-user` | 搜索用户 |
| `like` | 点赞/取消点赞笔记 |
| `favorite` | 收藏/取消收藏笔记 |
| `comment` | 发表评论 |
| `reply-comment` | 回复评论 |
| `delete-note` | 删除自己的笔记 |
| `publish` | 发布图文或视频笔记 |

### Twitter

| 工具 | 说明 |
|---|---|
| `search` | 使用高级筛选搜索推文 |
| `feed` | 获取首页时间线 |
| `bookmarks` | 获取收藏的推文 |
| `show` | 查看推文及其回复 |
| `likes` | 查看用户点赞的推文 |
| `user` | 查看用户信息 |
| `user-posts` | 列出用户发布的推文 |
| `following` | 列出用户关注的人 |
| `followers` | 列出用户的粉丝 |
| `status` | 检查认证状态 |
| `whoami` | 查看当前登录用户 |

## 限流

两个服务器默认执行 **1 请求/秒** 的速率限制，每日上限为 **500 次请求**。可在各服务器文件的 `RateLimiter` 构造函数中调整这些参数。

## 免责声明与风险提示

**本项目与小红书、X (Twitter) 没有任何关联、背书或从属关系。**

### 账号封禁风险

底层 CLI 工具通过非官方、未经授权的方式与平台 API 交互。**使用本项目可能违反小红书和/或 X (Twitter) 的服务条款。** 一旦被检测到，你的账号可能面临临时或永久限制甚至封禁。此风险同时适用于你用于登录的账号以及你与之交互的账号。

**降低风险的建议：**
- 使用专用账号（而非主账号）来使用本项目
- 遵守内置的速率限制 — 激进的调用频率会增加检测风险
- 注意平台的检测技术可能会不断升级

### 无担保声明

本项目按"现状"提供，不提供任何形式的担保。作者和贡献者不对因使用本软件而导致的任何账号处理行为（包括但不限于冻结、限制或永久封禁）承担任何责任。

### 安全提醒

你的认证凭据和会话令牌由底层 CLI 工具处理。使用前请自行审查其安全实践。切勿将令牌或会话数据分享给他人。

## 致谢

- [twitter-cli](https://github.com/jackwener/twitter-cli) — Copyright 2024 jackwener (Apache-2.0)

## 许可证

Apache-2.0
