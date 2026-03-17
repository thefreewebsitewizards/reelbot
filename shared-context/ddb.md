# DDB / Like-Minded Individuals (LMI) — Project Context

## What It Does
Personal brand (Dylan Does Business / @dylandoesbusiness) with community Discord server (Like-Minded Individuals). DDB is the content/social brand, LMI is the Discord community it funnels into. Custom bot handles onboarding, engagement, matchmaking, and admin.

## Stack
- **Runtime**: Python 3.12, discord.py v2
- **Infra**: Docker on Coolify VPS (76.13.29.110), GitHub Actions CI/CD
- **Repo**: `github.com/thefreewebsitewizards/ddb` (private)

## Capabilities
- **Discord Bot (LMI Bot#8676)**: 6 cogs — setup (server scaffolding), welcome (onboarding modal + DM), og_tracker (founding member roles), engagement (scheduled content/prompts), connect (interest-based matchmaking), admin (/announce, /ogstatus, /member, /engagement, /prompt, /seed)
- **Auto-deploy**: Push to `main` (path: `bot/**`) triggers GitHub Actions → Coolify deploy
- **Discord server**: Fully branded channels, welcome-rules with interest reactions, seed content in all resource channels, private admin category with #bot-logs
- **Third-party bots**: Carl-bot, Statbot, Ticket Tool, ProBot invited
- **Content planning**: Brand guide, 4 content pillars, 50+ content ideas, first-20 playbook
- **Growth funnel docs**: ManyChat setup guide (3 IG flows), LMI social profile templates (@lmicommunity)

## Current Status
- Bot deployed and running on Coolify (app uuid: `qs00cg4g8wsk4soowc8cw4wc`)
- Welcome flow tested and working (DM + OG role + admin notification)
- 17/17 tests passing
- All channels seeded with starter content
- Next: Manual setup — ManyChat account, LMI social profiles, Beehiiv, domain, Stan Store, first-20 outreach

## Integration Points
- **Coolify API**: `http://76.13.29.110:8000/api/v1/` (token in `.env`)
- **Discord webhook (#bot-logs)**: `https://discord.com/api/webhooks/1480399012594061312/...`
- **GitHub Actions secrets**: COOLIFY_API_TOKEN, COOLIFY_URL, COOLIFY_APP_UUID, COOLIFY_HOST, SSH_PRIVATE_KEY
