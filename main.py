"""
Social Media Manager — Telegram Bot Interface
=============================================
Replaces the CLI with a full Telegram chat interface.
Each Telegram user gets their own conversation history.

Setup:
  pip install groq python-telegram-bot
  export GROQ_API_KEY="gsk_..."
  export TELEGRAM_BOT_TOKEN="7123456789:AAF..."
  python telegram_bot.py
"""

import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from agents import orchestrator, state

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Per-user conversation history ──────────────────────────────────────────────
# { telegram_user_id: [ {role, content}, ... ] }
user_histories: dict[int, list] = {}

MAX_HISTORY = 20  # keep last 10 turns per user


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_history(user_id: int) -> list:
    return user_histories.setdefault(user_id, [])


def update_history(user_id: int, role: str, content: str):
    history = get_history(user_id)
    history.append({"role": role, "content": content})
    # Trim to last MAX_HISTORY messages
    if len(history) > MAX_HISTORY:
        user_histories[user_id] = history[-MAX_HISTORY:]


def pipeline_summary() -> str:
    posts      = state["posts"]
    scheduled  = sum(1 for p in posts if p["status"] == "scheduled")
    drafts     = sum(1 for p in posts if p["status"] == "draft")
    return (
        f"📊 *Pipeline*: {len(posts)} posts total "
        f"({scheduled} scheduled · {drafts} drafts)"
    )


# ── Command Handlers ───────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hey *{user.first_name}*\\! I'm your *Social Media Manager* — powered by Groq \\+ Llama 3\\.3\\.\n\n"
        "I have a team of specialist agents ready to help you:\n"
        "• ✍️ *Content Agent* — writes platform\\-specific posts\n"
        "• 📊 *Analyst Agent* — performance insights & strategy\n"
        "• 📅 *Scheduler Agent* — content calendars & timing\n"
        "• \\#️⃣ *Hashtag Agent* — hashtag research & strategy\n\n"
        "Just chat with me naturally\\! Try:\n"
        "_\"Write Instagram and LinkedIn posts about our product launch\"_\n"
        "_\"Analyse our performance and tell me what's working\"_\n"
        "_\"Create a 2\\-week content calendar\"_\n\n"
        "Type /help for more examples or /status to see your pipeline\\.",
        parse_mode="MarkdownV2",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Social Media Manager — Commands*\n\n"
        "*Chat naturally, for example:*\n"
        "• Write a Twitter thread about AI trends\n"
        "• Find hashtags for a fitness brand on Instagram\n"
        "• Schedule this week's posts for max engagement\n"
        "• What's our best performing platform?\n"
        "• Create posts for our summer sale — make it fun\n\n"
        "*Bot commands:*\n"
        "/start — Welcome message\n"
        "/help — This menu\n"
        "/status — Pipeline stats\n"
        "/posts — List all drafts & scheduled posts\n"
        "/clear — Clear your conversation history\n"
        "/platforms — Show managed platforms\n",
        parse_mode="Markdown",
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts     = state["posts"]
    scheduled = [p for p in posts if p["status"] == "scheduled"]
    drafts    = [p for p in posts if p["status"] == "draft"]

    text = (
        f"📊 *Pipeline Status*\n\n"
        f"Platforms   : {', '.join(state['platforms'])}\n"
        f"Brand voice : {state['brand_voice']}\n"
        f"Total posts : {len(posts)}\n"
        f"✅ Scheduled : {len(scheduled)}\n"
        f"📝 Drafts    : {len(drafts)}\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = state["posts"]
    if not posts:
        await update.message.reply_text(
            "No posts yet\\! Ask me to write some content to get started\\.",
            parse_mode="MarkdownV2",
        )
        return

    lines = ["📋 *All Posts*\n"]
    for p in posts[-15:]:  # show last 15
        icon    = "📅" if p["status"] == "scheduled" else "📝"
        preview = p["content"][:80].replace("\n", " ")
        if len(p["content"]) > 80:
            preview += "…"
        lines.append(
            f"{icon} *\\[{p['id']}\\] {p['platform']}* — {p['status'].upper()}\n"
            f"_{preview}_\n"
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="MarkdownV2",
    )


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text(
        "🧹 Conversation history cleared\\! Starting fresh\\.",
        parse_mode="MarkdownV2",
    )


async def cmd_platforms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    platforms = "\n".join(f"• {p}" for p in state["platforms"])
    await update.message.reply_text(
        f"📱 *Managed Platforms*\n\n{platforms}",
        parse_mode="Markdown",
    )


# ── Main Message Handler ───────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id      = update.effective_user.id
    user_message = update.message.text

    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing",
    )

    # Notify user agents are working
    thinking_msg = await update.message.reply_text(
        "🤖 Agents working on it\\.\\.\\.",
        parse_mode="MarkdownV2",
    )

    try:
        history  = get_history(user_id)
        response = orchestrator(user_message, history)

        # Update history
        update_history(user_id, "user",      user_message)
        update_history(user_id, "assistant", response)

        # Delete the "thinking" message
        await thinking_msg.delete()

        # Send response — split if too long (Telegram limit: 4096 chars)
        chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk)

    except Exception as e:
        logger.error(f"Error handling message from {user_id}: {e}", exc_info=True)
        await thinking_msg.edit_text(
            f"⚠️ Something went wrong: {str(e)[:200]}\n\nPlease try again."
        )


# ── Error Handler ──────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error: {context.error}", exc_info=True)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN not set.\n"
            "Get one from @BotFather and run:\n"
            "  export TELEGRAM_BOT_TOKEN='your-token-here'"
        )

    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        raise ValueError(
            "GROQ_API_KEY not set.\n"
            "  export GROQ_API_KEY='gsk_...'"
        )

    print("🚀 Social Media Manager Bot starting...")
    print(f"   Model    : llama-3.3-70b-versatile (Groq)")
    print(f"   Platforms: {', '.join(state['platforms'])}")
    print("   Waiting for messages...\n")

    app = Application.builder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("help",      cmd_help))
    app.add_handler(CommandHandler("status",    cmd_status))
    app.add_handler(CommandHandler("posts",     cmd_posts))
    app.add_handler(CommandHandler("clear",     cmd_clear))
    app.add_handler(CommandHandler("platforms", cmd_platforms))

    # All regular text messages → orchestrator
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Errors
    app.add_error_handler(error_handler)

    # Run (long polling — no server needed)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()