import asyncio
import logging
import re
from typing import Optional

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from .config import load_config
from . import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("imgbot")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "Привет! Пришлите фотографию — я сохраню её и присвою номер.\n"
        "Чтобы получить фото по номеру, отправьте команду /get <номер> или просто число."
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        return
    photo = update.message.photo[-1]
    file_id = photo.file_id
    user_id = update.message.from_user.id if update.message.from_user else 0

    image_id = await db.add_image(file_id=file_id, user_id=user_id)
    logger.info("Saved image %s from user %s", image_id, user_id)

    cfg = context.bot_data["config"]
    sent = await context.bot.send_photo(
        chat_id=cfg.channel_id,
        photo=file_id,
        caption=f"#{image_id}",
    )
    await db.update_channel_message_id(image_id=image_id, message_id=sent.message_id)

    await update.message.reply_text(f"Сохранено как №{image_id}")


def parse_requested_id(text: str) -> Optional[int]:
    m = re.search(r"\b(\d{1,10})\b", text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


async def cmd_get(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    args = context.args
    image_id: Optional[int] = None
    if args:
        try:
            image_id = int(args[0])
        except ValueError:
            image_id = None
    if image_id is None and update.message.text:
        image_id = parse_requested_id(update.message.text)
    if image_id is None:
        await update.message.reply_text("Укажите номер изображения: /get <номер>")
        return

    rec = await db.get_image(image_id)
    if not rec:
        await update.message.reply_text(f"Изображение №{image_id} не найдено")
        return

    if not update.effective_chat:
        return
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=rec["file_id"],
        caption=f"#{image_id}",
    )


async def handle_text_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    image_id = parse_requested_id(update.message.text)
    if image_id is None:
        return
    await cmd_get(update, context)


def main() -> None:
    cfg = load_config()
    asyncio.run(db.init_db(cfg.db_path))

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    app = (
        ApplicationBuilder()
        .token(cfg.token)
        .concurrent_updates(True)
        .build()
    )
    app.bot_data["config"] = cfg

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("get", cmd_get))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_number))

    logger.info("Starting bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
