# social-mcp

Rate-limited MCP (Model Context Protocol) adapters for Xiaohongshu (小红书) and Twitter/X.

These are thin adapters that wrap [xiaohongshu-cli](https://github.com/jackwener/xiaohongshu-cli) and [twitter-cli](https://github.com/jackwener/twitter-cli) into stdio-based MCP servers, enabling LLM agents (Claude Code, etc.) to interact with both platforms.

## Prerequisites

- Python 3.10+
- [pipx](https://pipx.pypa.io/)

## Install

```bash
# 1. Install the underlying CLI tools
pipx install twitter-cli
pipx install xiaohongshu-cli

# 2. Install this project
git clone https://github.com/<your-org>/social-mcp.git
cd social-mcp
pip install -e .

# Or install directly from GitHub:
# pip install git+https://github.com/<your-org>/social-mcp.git
```

## Configure

### Twitter/X

Set these environment variables:

```bash
export TWITTER_AUTH_TOKEN="your_auth_token"
export TWITTER_CT0="your_ct0_cookie"
```

> **Where to find them**: After logging into twitter.com in your browser, open Developer Tools → Application → Cookies → find `auth_token` and `ct0`.

### Xiaohongshu

Login via xhs-cli (it manages its own session):

```bash
xhs login
```

## Usage

Each platform runs as a separate MCP server over stdio:

```bash
# Xiaohongshu server
social-mcp-xhs

# Twitter server
social-mcp-twitter
```

### Claude Code

Add to `~/.claude.json` or your project's `.claude.json`:

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

### Custom CLI paths

Override the default CLI binary paths via environment variables:

```bash
export XHS_CLI_PATH="/custom/path/to/xhs"
export TWITTER_CLI_PATH="/custom/path/to/twitter"
```

## Tools

### Xiaohongshu

| Tool | Description |
|---|---|
| `search` | Search notes by keyword |
| `feed` | Browse recommendation feed |
| `hot` | Browse trending notes by category |
| `read` | Read a note by ID or URL |
| `comments` | View comments on a note |
| `user` | View user profile |
| `user-posts` | List a user's notes |
| `search-user` | Search for users |
| `status` | Check login status |
| `whoami` | Show current user profile |

### Twitter

| Tool | Description |
|---|---|
| `search` | Search tweets with advanced filters |
| `feed` | Fetch home timeline |
| `bookmarks` | Fetch bookmarked tweets |
| `show` | View a tweet and its replies |
| `likes` | Show tweets liked by a user |
| `user` | View user profile |
| `user-posts` | List a user's tweets |
| `following` | List accounts a user follows |
| `followers` | List followers of a user |
| `status` | Check authentication status |
| `whoami` | Show current authenticated user |

## Rate limits

Both servers enforce a default rate limit of **1 request/second** with a **daily cap of 500 requests**. These can be adjusted in the `RateLimiter` constructor in each server file.

## Disclaimer & Risk

**This project is not affiliated with, endorsed by, or connected to Xiaohongshu or X (Twitter).**

### Account Ban Risk

The underlying CLI tools interact with platform APIs through methods that are not officially supported or authorized. **Using this project may violate the Terms of Service of Xiaohongshu and/or X (Twitter).** If detected, your account may be temporarily or permanently restricted or banned. This risk exists for both the account whose credentials are used and any accounts you interact with.

**Recommendations to mitigate risk:**
- Use a dedicated account (not your primary account) when using this project
- Respect the built-in rate limits — aggressive usage increases detection risk
- Be aware that platform detection techniques may improve over time

### No Warranty

This project is provided "AS IS", without warranty of any kind. The authors and contributors are not liable for any account actions taken against you (including but not limited to suspension, restriction, or permanent ban) resulting from the use of this software.

### Security

Your authentication credentials and session tokens are handled by the underlying CLI tools. Review their security practices before use. Never share your tokens or session data with others.

## Acknowledgements

- [xiaohongshu-cli](https://github.com/jackwener/xiaohongshu-cli) — Copyright 2024 jackwener (Apache-2.0)
- [twitter-cli](https://github.com/jackwener/twitter-cli) — Copyright 2024 jackwener (Apache-2.0)

## License

Apache-2.0
