# personal-social-mcp

Personal MCP wrappers for Xiaohongshu (小红书) and Twitter/X.

This is a thin MCP (Model Context Protocol) adapter layer on top of
[xiaohongshu-cli](https://github.com/jackwener/xiaohongshu-cli) and
[twitter-cli](https://github.com/jackwener/twitter-cli). It provides rate-limited,
stdio-based MCP servers that let LLM agents (Claude Code, etc.) search, read, and
interact with both platforms.

**该项目本身只是一个薄包装层，不包含底层 CLI。** 要让它真正工作，你必须先单独安装对应的命令行工具。

| 平台 | 所需 CLI | 安装方式 |
|---|---|---|
| Twitter/X | [twitter-cli](https://github.com/jackwener/twitter-cli) | `pipx install twitter-cli` |
| 小红书 | [xiaohongshu-cli](https://github.com/jackwener/xiaohongshu-cli) | `pipx install xiaohongshu-cli` |

安装完成后，底层 CLI 的可执行文件会自动出现在 `~/.local/bin/` 下。

## Prerequisites

- Python >= 3.10
- [pipx](https://pipx.pypa.io/) (for installing the underlying CLIs)
- `pip` (or `uv`)

## Install

```bash
# 1. 先安装底层 CLI（必须）
pipx install twitter-cli
pipx install xiaohongshu-cli

# 2. 再安装本项目
git clone https://github.com/<your>/personal-social-mcp.git
cd personal-social-mcp
pip install -e .
```

## Configure

### Twitter/X

Set your Twitter auth tokens. The server checks these sources in order:

1. `~/.config/mcp-creds/twitter.yaml`
2. `~/.agent-reach/config.yaml`
3. Environment variables: `TWITTER_AUTH_TOKEN`, `TWITTER_CT0`

Example creds file (`~/.config/mcp-creds/twitter.yaml`):

```yaml
auth_token: "..."
ct0: "..."
```

### Xiaohongshu

[Login with xhs-cli](https://github.com/jackwener/xiaohongshu-cli) — it manages its own session.

## Usage

Each platform runs as a separate MCP server via stdio:

```bash
# Xiaohongshu MCP server
psm-xhs

# Twitter MCP server
psm-twitter
```

### Claude Code integration

Add to your `~/.claude.json` or project `.claude.json`:

```json
"mcpServers": {
  "xiaohongshu": {
    "command": "psm-xhs"
  },
  "twitter": {
    "command": "psm-twitter"
  }
}
```

## Tools

### Xiaohongshu

| Tool | Description |
|---|---|
| `search` | Search notes by keyword |
| `feed` | Browse recommendation feed |
| `hot` | Browse hot/trending notes |
| `read` | Read a note by ID or URL |
| `comments` | View comments on a note |
| `user` | View user profile |
| `user-posts` | List a user's notes |
| `search-user` | Search users |
| `status` | Check login status |
| `whoami` | Show current user profile |

### Twitter

| Tool | Description |
|---|---|
| `search` | Search tweets with advanced filters |
| `feed` | Fetch home timeline |
| `bookmarks` | Fetch bookmarked tweets |
| `show` | View a tweet and replies |
| `likes` | Show liked tweets of a user |
| `user` | View user profile |
| `user-posts` | List a user's tweets |
| `following` | List accounts a user follows |
| `followers` | List followers of a user |
| `status` | Check auth status |
| `whoami` | Show current user |

## Disclaimer

This project is **not affiliated with Xiaohongshu, X (Twitter), or Bilibili**.

The underlying CLIs (`xiaohongshu-cli`, `twitter-cli`) work through
reverse-engineered API endpoints — use at your own risk. See their respective
repositories for license and legal details.
