import sys

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

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

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="New Item"), KeyboardButton(text="Recent Items")],
        [KeyboardButton(text="Search"), KeyboardButton(text="Lost Items"), KeyboardButton(text="Found Items")],
        [KeyboardButton(text="Help"), KeyboardButton(text="Clear")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Choose an action",
)

FORM_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Back"), KeyboardButton(text="Cancel")]],
    resize_keyboard=True,
    input_field_placeholder="Use Back/Cancel or type your answer",
)

BOT_COMMANDS = [
    BotCommand(command="start", description="restart the bot"),
    BotCommand(command="help", description="show instructions"),
    BotCommand(command="new", description="create a lost/found item"),
    BotCommand(command="list", description="show recent items"),
    BotCommand(command="search", description="search items"),
    BotCommand(command="lost", description="show lost items"),
    BotCommand(command="found", description="show found items"),
    BotCommand(command="clear", description="cancel current action and clear chat state"),
]


class NewItemForm(StatesGroup):
    status = State()
    title = State()
    category = State()
    location = State()
    description = State()
    contact = State()
    review = State()


STEP_ORDER = ["status", "title", "category", "location", "description", "contact"]

STEP_META = {
    "status": {
        "state": NewItemForm.status,
        "title": "Status",
        "prompt": "Please enter item status: lost or found.",
    },
    "title": {
        "state": NewItemForm.title,
        "title": "Title",
        "prompt": "Please enter the item title.",
    },
    "category": {
        "state": NewItemForm.category,
        "title": "Category",
        "prompt": "Please enter the category (e.g. Electronics, Bags, Accessories).",
    },
    "location": {
        "state": NewItemForm.location,
        "title": "Location",
        "prompt": "Where was it lost/found?",
    },
    "description": {
        "state": NewItemForm.description,
        "title": "Description",
        "prompt": "Short description?",
    },
    "contact": {
        "state": NewItemForm.contact,
        "title": "Contact",
        "prompt": "Contact name? (or type 'me' to use your Telegram username)",
    },
}


def _review_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Submit", callback_data="review:submit")],
            [
                InlineKeyboardButton(text="✏️ Edit Status", callback_data="review:edit:status"),
                InlineKeyboardButton(text="✏️ Edit Title", callback_data="review:edit:title"),
            ],
            [
                InlineKeyboardButton(text="✏️ Edit Category", callback_data="review:edit:category"),
                InlineKeyboardButton(text="✏️ Edit Location", callback_data="review:edit:location"),
            ],
            [
                InlineKeyboardButton(text="✏️ Edit Description", callback_data="review:edit:description"),
                InlineKeyboardButton(text="✏️ Edit Contact", callback_data="review:edit:contact"),
            ],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="review:cancel")],
        ]
    )


async def _clear_state(state: FSMContext) -> None:
    await state.clear()


async def _cancel_wizard(message: Message, state: FSMContext) -> None:
    await _clear_state(state)
    await message.answer("Current action cleared. You can start again.", reply_markup=MAIN_KEYBOARD)


async def _show_help(message: Message) -> None:
    await message.answer(
        "Use the menu or keyboard:\n"
        "• /new — post an item\n"
        "• /list — recent items\n"
        "• /search <query> — find by keyword\n"
        "• /lost /found — filtered lists\n"
        "• /clear — cancel current action",
        reply_markup=MAIN_KEYBOARD,
    )


async def _set_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(BOT_COMMANDS)


async def on_startup(bot: Bot) -> None:
    await _set_bot_commands(bot)


def _step_header(step_key: str) -> str:
    step_number = STEP_ORDER.index(step_key) + 1
    total = len(STEP_ORDER)
    return f"Step {step_number}/{total} — {STEP_META[step_key]['title']}"


async def _ask_step(message: Message, state: FSMContext, step_key: str) -> None:
    await state.set_state(STEP_META[step_key]["state"])
    await message.answer(
        f"{_step_header(step_key)}\n{STEP_META[step_key]['prompt']}",
        reply_markup=FORM_KEYBOARD,
    )


def _build_review_text(data: dict) -> str:
    return (
        "Please review your item:\n\n"
        f"Status: {str(data.get('status', '')).title()}\n"
        f"Title: {data.get('title', '')}\n"
        f"Category: {data.get('category', '')}\n"
        f"Location: {data.get('location', '')}\n"
        f"Description: {data.get('description', '')}\n"
        f"Contact: {data.get('contact_name', '')}\n\n"
        "Choose an action below."
    )


async def _show_review(message: Message, state: FSMContext) -> None:
    await state.set_state(NewItemForm.review)
    data = await state.get_data()
    await message.answer(_build_review_text(data), reply_markup=_review_keyboard())


async def _go_back(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    state_to_key = {
        NewItemForm.status.state: "status",
        NewItemForm.title.state: "title",
        NewItemForm.category.state: "category",
        NewItemForm.location.state: "location",
        NewItemForm.description.state: "description",
        NewItemForm.contact.state: "contact",
        NewItemForm.review.state: "review",
    }
    current_key = state_to_key.get(current)

    if current_key == "review":
        await _ask_step(message, state, "contact")
        return

    if not current_key or current_key == "status":
        await message.answer("You are already at the first step.", reply_markup=FORM_KEYBOARD)
        return

    prev_key = STEP_ORDER[STEP_ORDER.index(current_key) - 1]
    await _ask_step(message, state, prev_key)


async def _store_and_continue(message: Message, state: FSMContext, step_key: str, value: str) -> None:
    update_key = "contact_name" if step_key == "contact" else step_key
    await state.update_data(**{update_key: value})

    is_editing = bool((await state.get_data()).get("editing_field"))
    if is_editing:
        await state.update_data(editing_field=None)
        await _show_review(message, state)
        return

    if step_key == "contact":
        await _show_review(message, state)
        return

    next_key = STEP_ORDER[STEP_ORDER.index(step_key) + 1]
    await _ask_step(message, state, next_key)


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await _clear_state(state)
    await message.answer("👋 Welcome to Lost & Found Board assistant.", reply_markup=MAIN_KEYBOARD)
    await _show_help(message)


@dp.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext) -> None:
    await _clear_state(state)
    await _show_help(message)


@dp.message(Command("clear"))
async def cmd_clear(message: Message, state: FSMContext) -> None:
    await _cancel_wizard(message, state)


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
    await _clear_state(state)
    await _ask_step(message, state, "status")


@dp.message(F.text.casefold() == "new item")
async def keyboard_new_item(message: Message, state: FSMContext) -> None:
    await cmd_new(message, state)


@dp.message(F.text.casefold() == "recent items")
async def keyboard_recent_items(message: Message) -> None:
    await cmd_list(message)


@dp.message(F.text.casefold() == "search")
async def keyboard_search_hint(message: Message) -> None:
    await message.answer("Send /search <keyword> to search items.", reply_markup=MAIN_KEYBOARD)


@dp.message(F.text.casefold() == "lost items")
async def keyboard_lost_items(message: Message) -> None:
    await cmd_lost(message)


@dp.message(F.text.casefold() == "found items")
async def keyboard_found_items(message: Message) -> None:
    await cmd_found(message)


@dp.message(F.text.casefold() == "help")
async def keyboard_help(message: Message, state: FSMContext) -> None:
    await cmd_help(message, state)


@dp.message(F.text.casefold() == "clear")
async def keyboard_clear(message: Message, state: FSMContext) -> None:
    await cmd_clear(message, state)


@dp.message(NewItemForm, F.text.casefold() == "cancel")
async def wizard_cancel(message: Message, state: FSMContext) -> None:
    await _cancel_wizard(message, state)


@dp.message(NewItemForm, F.text.casefold() == "back")
async def wizard_back(message: Message, state: FSMContext) -> None:
    await _go_back(message, state)


@dp.message(NewItemForm.status)
async def form_status(message: Message, state: FSMContext) -> None:
    value = message.text.strip().lower()
    if value not in {"lost", "found"}:
        await message.answer("Please type exactly: lost or found.", reply_markup=FORM_KEYBOARD)
        return
    await _store_and_continue(message, state, "status", value)


@dp.message(NewItemForm.title)
async def form_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if not await _check_length(message, "title", title):
        return
    await _store_and_continue(message, state, "title", title)


@dp.message(NewItemForm.category)
async def form_category(message: Message, state: FSMContext) -> None:
    category = message.text.strip()
    if not await _check_length(message, "category", category):
        return
    await _store_and_continue(message, state, "category", category)


@dp.message(NewItemForm.location)
async def form_location(message: Message, state: FSMContext) -> None:
    location = message.text.strip()
    if not await _check_length(message, "location", location):
        return
    await _store_and_continue(message, state, "location", location)


@dp.message(NewItemForm.description)
async def form_description(message: Message, state: FSMContext) -> None:
    description = message.text.strip()
    if not await _check_length(message, "description", description):
        return
    await _store_and_continue(message, state, "description", description)


@dp.message(NewItemForm.contact)
async def form_contact(message: Message, state: FSMContext) -> None:
    username = message.from_user.username
    contact_raw = message.text.strip()
    contact_name = f"@{username}" if contact_raw.lower() == "me" and username else contact_raw
    if not await _check_length(message, "contact_name", contact_name):
        return
    await _store_and_continue(message, state, "contact", contact_name)


@dp.callback_query(NewItemForm.review, F.data.startswith("review:"))
async def review_action(callback: CallbackQuery, state: FSMContext) -> None:
    action = callback.data

    if action == "review:cancel":
        await state.clear()
        await callback.message.answer("Current action cleared. You can start again.", reply_markup=MAIN_KEYBOARD)
        await callback.answer()
        return

    if action == "review:submit":
        data = await state.get_data()
        payload = {
            "status": data["status"],
            "title": data["title"],
            "category": data["category"],
            "location": data["location"],
            "description": data["description"],
            "contact_name": data["contact_name"],
            "telegram_username": f"@{callback.from_user.username}" if callback.from_user.username else None,
            "telegram_user_id": callback.from_user.id,
        }

        try:
            item = await api.create_item(payload)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 422:
                await callback.message.answer(
                    "Could not create item because of validation errors:\n"
                    f"{_format_validation_error(exc.response)}",
                    reply_markup=MAIN_KEYBOARD,
                )
                await callback.answer()
                return
            raise

        await state.clear()
        await callback.message.answer(f"✅ Item created: #{item['id']} {item['title']}", reply_markup=MAIN_KEYBOARD)

        try:
            matches = await api.get_matches(item["id"])
        except (httpx.TimeoutException, httpx.HTTPError):
            await callback.message.answer(
                "Item saved successfully. Smart matching is temporarily unavailable, "
                "but we'll keep your item posted for rule-based discovery."
            )
            await callback.answer()
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
            await callback.message.answer("Possible smart matches:\n" + "\n".join(match_lines), reply_markup=MAIN_KEYBOARD)
        else:
            await callback.message.answer("No smart matches yet. We'll keep checking as new items arrive.", reply_markup=MAIN_KEYBOARD)

        await callback.answer()
        return

    # review:edit:<field>
    _, _, field = action.split(":", maxsplit=2)
    if field not in STEP_META:
        await callback.answer("Unknown field", show_alert=True)
        return

    await state.update_data(editing_field=field)
    await state.set_state(STEP_META[field]["state"])
    await callback.message.answer(
        f"Editing {STEP_META[field]['title']}.\n{STEP_META[field]['prompt']}",
        reply_markup=FORM_KEYBOARD,
    )
    await callback.answer()


@dp.message(F.text)
async def fallback(message: Message) -> None:
    await message.answer("Try /new, /list, /search <keyword>, /lost, /found", reply_markup=MAIN_KEYBOARD)


async def _check_length(message: Message, field_name: str, value: str) -> bool:
    min_length, max_length = FIELD_LIMITS[field_name]
    if len(value) < min_length:
        message_text = f"{field_name.replace('_', ' ').title()} is too short (min {min_length} characters)."
    elif len(value) > max_length:
        message_text = f"{field_name.replace('_', ' ').title()} is too long (max {max_length} characters)."
    else:
        return True

    await message.answer(message_text, reply_markup=FORM_KEYBOARD)
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

    dp.startup.register(on_startup)
    dp.run_polling(bot)
