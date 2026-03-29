import sys
import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from api_client import BackendClient
from config import settings

dp = Dispatcher()
api = BackendClient(
    settings.api_base_url,
    timeout_seconds=settings.api_timeout_seconds,
    match_timeout_seconds=settings.match_timeout_seconds,
)

FIELD_LIMITS = {
    "title": (3, 120),
    "category": (2, 60),
    "location": (2, 120),
    "description": (5, 2000),
    "contact_name": (2, 80),
}


class NewItemForm(StatesGroup):
    status = State()
    title = State()
    category = State()
    location = State()
    description = State()
    contact = State()


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 Welcome to Lost & Found Board assistant.\n"
        "Use /new to post an item, /list to see recent posts, /search <keyword> to find items."
    )


@dp.message(Command("list"))
async def cmd_list(message: Message) -> None:
    items = await api.list_items()
    if not items:
        await message.answer("No items yet.")
        return
    text = "\n\n".join(
        f"#{i['id']} [{i['status'].upper()}] {i['title']}\n📍 {i['location']}\n🏷 {i['category']}"
        for i in items[:8]
    )
    await message.answer(text)


@dp.message(Command("lost"))
async def cmd_lost(message: Message) -> None:
    items = await api.list_items({"status": "lost"})
    await message.answer("\n".join(f"• {i['title']} ({i['location']})" for i in items[:10]) or "No lost items.")


@dp.message(Command("found"))
async def cmd_found(message: Message) -> None:
    items = await api.list_items({"status": "found"})
    await message.answer("\n".join(f"• {i['title']} ({i['location']})" for i in items[:10]) or "No found items.")


@dp.message(Command("search"))
async def cmd_search(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Usage: /search <query>")
        return
    items = await api.search_items(command.args)
    if not items:
        await message.answer("No matching items found.")
        return
    text = "\n".join(f"• [{i['status']}] {i['title']} - {i['location']}" for i in items[:10])
    await message.answer(text)


@dp.message(Command("new"))
async def cmd_new(message: Message, state: FSMContext) -> None:
    await state.set_state(NewItemForm.status)
    await message.answer("Is the item *lost* or *found*?", parse_mode="Markdown")


@dp.message(NewItemForm.status)
async def form_status(message: Message, state: FSMContext) -> None:
    value = message.text.strip().lower()
    if value not in {"lost", "found"}:
        await message.answer("Please type exactly: lost or found.")
        return
    await state.update_data(status=value)
    await state.set_state(NewItemForm.title)
    await message.answer("Title of the item?")


@dp.message(NewItemForm.title)
async def form_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if not await _check_length(message, "title", title):
        return
    await state.update_data(title=title)
    await state.set_state(NewItemForm.category)
    await message.answer("Category? (e.g. Electronics, Bags, Accessories)")


@dp.message(NewItemForm.category)
async def form_category(message: Message, state: FSMContext) -> None:
    category = message.text.strip()
    if not await _check_length(message, "category", category):
        return
    await state.update_data(category=category)
    await state.set_state(NewItemForm.location)
    await message.answer("Where was it lost/found?")


@dp.message(NewItemForm.location)
async def form_location(message: Message, state: FSMContext) -> None:
    location = message.text.strip()
    if not await _check_length(message, "location", location):
        return
    await state.update_data(location=location)
    await state.set_state(NewItemForm.description)
    await message.answer("Short description?")


@dp.message(NewItemForm.description)
async def form_description(message: Message, state: FSMContext) -> None:
    description = message.text.strip()
    if not await _check_length(message, "description", description):
        return
    await state.update_data(description=description)
    await state.set_state(NewItemForm.contact)
    await message.answer("Contact name? (or type 'me' to use your Telegram username)")


@dp.message(NewItemForm.contact)
async def form_contact(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    username = message.from_user.username
    contact_raw = message.text.strip()
    contact_name = f"@{username}" if contact_raw.lower() == "me" and username else contact_raw
    if not await _check_length(message, "contact_name", contact_name):
        return

    payload = {
        **data,
        "contact_name": contact_name,
        "telegram_username": f"@{username}" if username else None,
        "telegram_user_id": message.from_user.id,
    }

    try:
        item = await api.create_item(payload)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 422:
            await message.answer(
                "Could not create item because of validation errors:\n"
                f"{_format_validation_error(exc.response)}"
            )
            return
        raise
    await state.clear()
    await message.answer(f"✅ Item created: #{item['id']} {item['title']}")

    try:
        matches = await api.get_matches(item["id"])
    except (httpx.TimeoutException, httpx.HTTPError):
        await message.answer(
            "Item saved successfully. Smart matching is temporarily unavailable, "
            "but we'll keep your item posted for rule-based discovery."
        )
        return

    if matches:
        match_lines = []
        for m in matches:
            reasons = ", ".join(m.get("reasons", [])[:3])
            match_lines.append(
                f"• {m['title']} ({m['category']}, {m['location']})\n"
                f"  score={m['relevance_score']}/10, confidence={m.get('confidence', 'low')}\n"
                f"  why: {reasons or 'similar context'}"
            )
        await message.answer("Possible smart matches:\n" + "\n".join(match_lines))
    else:
        await message.answer("No smart matches yet. We'll keep checking as new items arrive.")


@dp.message(F.text)
async def fallback(message: Message) -> None:
    await message.answer("Try /new, /list, /search <keyword>, /lost, /found")


async def _check_length(message: Message, field_name: str, value: str) -> bool:
    min_length, max_length = FIELD_LIMITS[field_name]
    if len(value) < min_length:
        message_text = f"{field_name.replace('_', ' ').title()} is too short (min {min_length} characters)."
    elif len(value) > max_length:
        message_text = f"{field_name.replace('_', ' ').title()} is too long (max {max_length} characters)."
    else:
        return True

    await message.answer(message_text)
    return False


def _format_validation_error(response: httpx.Response) -> str:
    try:
        details = response.json().get("detail")
    except ValueError:
        return "Unexpected validation response from backend."

    if not isinstance(details, list) or not details:
        return "Request failed validation, but no details were returned."

    issues = []
    for issue in details:
        if not isinstance(issue, dict):
            continue
        loc = issue.get("loc")
        field = loc[-1] if isinstance(loc, list) and loc else "field"
        msg = issue.get("msg", "invalid value")
        issues.append(f"• {field}: {msg}")
    return "\n".join(issues) if issues else "Request failed validation."


def create_bot() -> Bot:
    token = settings.telegram_bot_token
    if not token or token == "replace_me":
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is required to run the bot. Set it in .env and start compose with --profile bot."
        )
    return Bot(token=token)


if __name__ == "__main__":
    try:
        bot = create_bot()
    except RuntimeError as exc:
        print(f"[bot-config-error] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    dp.run_polling(bot)
