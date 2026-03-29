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
    PhotoSize,
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
        [KeyboardButton(text="New Item"), KeyboardButton(text="My Items"), KeyboardButton(text="Recent Items")],
        [KeyboardButton(text="Search"), KeyboardButton(text="Lost Items"), KeyboardButton(text="Found Items")],
        [KeyboardButton(text="Help"), KeyboardButton(text="Clear")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Choose an action",
)
STATUS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="lost"), KeyboardButton(text="found")], [KeyboardButton(text="Back"), KeyboardButton(text="Cancel")]],
    resize_keyboard=True,
    input_field_placeholder="Choose lost/found",
)

FORM_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Back"), KeyboardButton(text="Cancel")]],
    resize_keyboard=True,
    input_field_placeholder="Use Back/Cancel or type your answer",
)
PHOTO_STEP_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Skip Photo")], [KeyboardButton(text="Back"), KeyboardButton(text="Cancel")]],
    resize_keyboard=True,
    input_field_placeholder="Send a photo or choose Skip Photo",
)

BOT_COMMANDS = [
    BotCommand(command="start", description="restart the bot"),
    BotCommand(command="help", description="show instructions"),
    BotCommand(command="new", description="create a lost/found item"),
    BotCommand(command="list", description="show recent items"),
    BotCommand(command="search", description="search items"),
    BotCommand(command="lost", description="show lost items"),
    BotCommand(command="found", description="show found items"),
    BotCommand(command="myitems", description="manage your reports"),
    BotCommand(command="claims", description="view your claim requests"),
    BotCommand(command="link", description="link website session code"),
    BotCommand(command="flag", description="flag suspicious report"),
    BotCommand(command="whoami", description="show your telegram/account details"),
    BotCommand(command="clear", description="cancel current action and clear chat state"),
]


class NewItemForm(StatesGroup):
    status = State()
    title = State()
    category = State()
    location = State()
    description = State()
    contact = State()
    photo = State()
    review = State()


STEP_ORDER = ["status", "title", "category", "location", "description", "contact", "photo"]

STEP_META = {
    "status": {
        "state": NewItemForm.status,
        "title": "Status",
        "prompt": "Choose item status: lost or found.",
    },
    "title": {
        "state": NewItemForm.title,
        "title": "Title",
        "prompt": "Please enter the item title.",
    },
    "category": {
        "state": NewItemForm.category,
        "title": "Category",
        "prompt": "Choose category from the keyboard or type your own.",
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
    "photo": {
        "state": NewItemForm.photo,
        "title": "Photo",
        "prompt": "Send a photo for this item, or tap Skip Photo.",
    },
}

CATEGORY_PAGE_SIZE = 9


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
            [InlineKeyboardButton(text="🖼 Edit Photo", callback_data="review:edit:photo")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="review:cancel")],
        ]
    )


def _item_actions_keyboard(item_id: int, lifecycle: str) -> InlineKeyboardMarkup:
    controls = [
        [
            InlineKeyboardButton(text="🔎 Show Matches", callback_data=f"myitem:matches:{item_id}"),
            InlineKeyboardButton(text="🗑 Delete", callback_data=f"myitem:delete:{item_id}"),
        ]
    ]
    if lifecycle == "active":
        controls.insert(0, [InlineKeyboardButton(text="✅ Mark Resolved", callback_data=f"myitem:resolve:{item_id}")])
    elif lifecycle == "resolved":
        controls.insert(0, [InlineKeyboardButton(text="♻️ Reopen", callback_data=f"myitem:reopen:{item_id}")])
    return InlineKeyboardMarkup(inline_keyboard=controls)


def _claim_actions_keyboard(source_item_id: int, target_item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🤝 Claim this match", callback_data=f"claim:create:{source_item_id}:{target_item_id}")],
            [InlineKeyboardButton(text="🚫 Not a match", callback_data=f"claim:notmatch:{source_item_id}:{target_item_id}")],
        ]
    )


def _incoming_claim_keyboard(claim_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Approve", callback_data=f"claim:approve:{claim_id}")],
            [InlineKeyboardButton(text="❌ Reject", callback_data=f"claim:reject:{claim_id}")],
            [InlineKeyboardButton(text="🎯 Mark returned", callback_data=f"claim:complete:{claim_id}")],
        ]
    )


def _render_item_summary(item: dict) -> str:
    return (
        f"#{item['id']} {item['title']}\n"
        f"Type: {str(item['status']).upper()} • Lifecycle: {str(item['lifecycle']).upper()}\n"
        f"Moderation: {str(item.get('moderation_status', 'approved')).upper()} • Verified: {'YES' if item.get('is_verified') else 'NO'}\n"
        f"Category: {item['category']}\n"
        f"Location: {item['location']}\n"
        f"Created: {item['created_at'][:10]}"
    )


def _photo_url(image_path: str | None) -> str | None:
    if not image_path:
        return None
    return f"{api.base_url.removesuffix('/api')}/media/{image_path}"


async def _clear_state(state: FSMContext) -> None:
    await state.clear()


async def _cancel_wizard(message: Message, state: FSMContext) -> None:
    await _clear_state(state)
    await message.answer("Current action cleared. You can start again.", reply_markup=MAIN_KEYBOARD)


async def _clear_chat_context(message: Message) -> tuple[int, int]:
    if not message.chat or message.chat.type != "private":
        return 0, 0
    deleted = 0
    failed = 0
    min_id = max(1, message.message_id - 45)
    for msg_id in range(message.message_id, min_id - 1, -1):
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
            deleted += 1
        except Exception:
            failed += 1
    return deleted, failed


async def _show_help(message: Message) -> None:
    await message.answer(
        "Use the menu or keyboard:\n"
        "• /new — guided multi-step report flow\n"
        "• /list — recent items\n"
        "• /search <query> — typo-tolerant smart search\n"
        "• /lost /found — filtered lists\n"
        "• /myitems — dashboard summary of your reports\n"
        "• /claims — review your claim workflow\n"
        "• /link <code> — connect website session securely\n"
        "• /flag <item_id> <reason> — report abuse\n"
        "• /whoami — show your account details\n"
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


def _category_keyboard(categories: list[str], page: int = 0, suggested: str | None = None) -> InlineKeyboardMarkup:
    start = page * CATEGORY_PAGE_SIZE
    chunk = categories[start:start + CATEGORY_PAGE_SIZE]
    rows: list[list[InlineKeyboardButton]] = []
    if suggested and suggested in categories:
        rows.append([InlineKeyboardButton(text=f"✨ Use suggested: {suggested}", callback_data=f"cat:choose:{suggested}")])
    for idx in range(0, len(chunk), 3):
        row_items = chunk[idx:idx + 3]
        rows.append([InlineKeyboardButton(text=name, callback_data=f"cat:choose:{name}") for name in row_items])
    nav: list[InlineKeyboardButton] = []
    if start > 0:
        nav.append(InlineKeyboardButton(text="◀ Prev", callback_data=f"cat:page:{page - 1}"))
    if start + CATEGORY_PAGE_SIZE < len(categories):
        nav.append(InlineKeyboardButton(text="Next ▶", callback_data=f"cat:page:{page + 1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _ask_step(message: Message, state: FSMContext, step_key: str) -> None:
    await state.set_state(STEP_META[step_key]["state"])
    keyboard = PHOTO_STEP_KEYBOARD if step_key == "photo" else STATUS_KEYBOARD if step_key == "status" else FORM_KEYBOARD
    prompt = f"{_step_header(step_key)}\n{STEP_META[step_key]['prompt']}"
    if step_key == "category":
        data = await state.get_data()
        title = str(data.get("title", "")).strip()
        categories = await api.get_categories()
        suggestion_text = ""
        suggested = None
        if title:
            suggestion = await api.suggest_category(title)
            suggested = suggestion.get("category")
            confidence = float(suggestion.get("confidence", 0))
            if suggested and confidence >= 0.35 and suggested.lower() != "other":
                suggestion_text = f"\nSuggested category: {suggested} ({int(confidence * 100)}% confidence)."
                await state.update_data(category_suggested=suggested)
        await message.answer(
            f"{prompt}{suggestion_text}",
            reply_markup=keyboard,
        )
        await message.answer(
            "Tap a category below or type your own custom category.",
            reply_markup=_category_keyboard(categories, page=0, suggested=suggested),
        )
        return
    await message.answer(prompt, reply_markup=keyboard)


def _build_review_text(data: dict) -> str:
    return (
        "Please review your item:\n\n"
        f"Status: {str(data.get('status', '')).title()}\n"
        f"Title: {data.get('title', '')}\n"
        f"Category: {data.get('category', '')}\n"
        f"Location: {data.get('location', '')}\n"
        f"Description: {data.get('description', '')}\n"
        f"Contact: {data.get('contact_name', '')}\n\n"
        f"Photo: {'attached' if data.get('image_path') else 'not attached'}\n\n"
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
        NewItemForm.photo.state: "photo",
        NewItemForm.review.state: "review",
    }
    current_key = state_to_key.get(current)

    if current_key == "review":
        await _ask_step(message, state, "photo")
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

    if step_key == "photo":
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
    await _clear_state(state)
    await _clear_chat_context(message)
    await message.answer(
        "👋 Fresh start. Choose an action below.",
        reply_markup=MAIN_KEYBOARD,
    )


@dp.message(Command("whoami"))
async def cmd_whoami(message: Message) -> None:
    user = message.from_user
    if not user:
        await message.answer("Could not read Telegram account details.")
        return

    username = f"@{user.username}" if user.username else "not set"
    first_name = user.first_name or "not set"

    lines = [
        f"Telegram user id: {user.id}",
        f"Username: {username}",
        f"First name: {first_name}",
    ]

    try:
        access = await api.telegram_admin_access(user.id, user.username)
        is_admin = bool(access.get("admin_access"))
        role = access.get("role") or "none"
        lines.append(f"Admin access: {'yes' if is_admin else 'no'}")
        lines.append(f"Role: {role}")
    except httpx.HTTPError:
        pass

    await message.answer("\n".join(lines))


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
    items = await api.search_items_smart(command.args, limit=6)
    if not items:
        await message.answer("No good matches found. Try another keyword, location, or shorter phrase.")
        return
    text = "\n\n".join(
        f"• [{row['item']['status'].upper()}] {row['item']['title']} — {row['item']['location']}\n"
        f"  score: {row['relevance_score']}/100\n"
        f"  why: {', '.join(row.get('reasons', [])[:2]) or 'fuzzy/token match'}"
        for row in items
    )
    await message.answer(text)


@dp.message(Command("myitems"))
async def cmd_my_items(message: Message) -> None:
    user_id = message.from_user.id
    items = await api.list_my_items(user_id)
    if not items:
        await message.answer("You have no reports yet. Use /new to create one.", reply_markup=MAIN_KEYBOARD)
        return

    active = [item for item in items if item["lifecycle"] == "active"]
    resolved = [item for item in items if item["lifecycle"] == "resolved"]
    deleted = [item for item in items if item["lifecycle"] == "deleted"]
    await message.answer(
        f"My Reports\nActive: {len(active)} • Resolved: {len(resolved)} • Deleted: {len(deleted)}",
        reply_markup=MAIN_KEYBOARD,
    )
    for item in items[:20]:
        image_url = _photo_url(item.get("image_path"))
        if image_url:
            await message.answer_photo(
                photo=image_url,
                caption=_render_item_summary(item),
                reply_markup=_item_actions_keyboard(item["id"], item["lifecycle"]),
            )
        else:
            await message.answer(_render_item_summary(item), reply_markup=_item_actions_keyboard(item["id"], item["lifecycle"]))


@dp.message(Command("claims"))
async def cmd_claims(message: Message) -> None:
    claims = await api.list_claims(message.from_user.id, direction="all")
    if not claims:
        await message.answer("No claim requests yet.", reply_markup=MAIN_KEYBOARD)
        return
    incoming = [claim for claim in claims if claim.get("owner_telegram_user_id") == message.from_user.id]
    outgoing = [claim for claim in claims if claim.get("requester_telegram_user_id") == message.from_user.id]
    await message.answer(
        f"Claim Dashboard\nIncoming: {len(incoming)} • Outgoing: {len(outgoing)} • Total: {len(claims)}",
        reply_markup=MAIN_KEYBOARD,
    )
    for claim in claims[:20]:
        text = (
            f"Claim #{claim['id']} — {claim['status'].upper()}\n"
            f"Source: #{claim['source_item_id']} {claim.get('source_item_title') or ''}\n"
            f"Target: #{claim['target_item_id']} {claim.get('target_item_title') or ''}\n"
        )
        if claim.get("shared_source_contact") or claim.get("shared_target_contact"):
            text += (
                f"\nContact shared:\n"
                f"• Source: {claim.get('shared_source_contact') or '-'}\n"
                f"• Target: {claim.get('shared_target_contact') or '-'}\n"
            )
        await message.answer(text, reply_markup=MAIN_KEYBOARD)


@dp.message(Command("link"))
async def cmd_link(message: Message, command: CommandObject) -> None:
    code = (command.args or "").strip().upper()
    if not code:
        await message.answer(
            "Usage: /link <code>\n\nWebsite flow:\n1) Open My Reports or Report Item.\n2) Generate secure link code.\n3) Paste here using /link.",
            reply_markup=MAIN_KEYBOARD,
        )
        return
    try:
        await api.confirm_web_link(
            code=code,
            telegram_user_id=message.from_user.id,
            telegram_username=message.from_user.username,
            display_name=message.from_user.full_name,
        )
    except httpx.HTTPError:
        await message.answer("Could not link this code. It may be expired. Generate a new code on the website.", reply_markup=MAIN_KEYBOARD)
        return
    await message.answer(
        "✅ Website linked to your Telegram account.\nReload My Reports on the website to see synced ownership and claims.",
        reply_markup=MAIN_KEYBOARD,
    )


@dp.message(Command("flag"))
async def cmd_flag(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Usage: /flag <item_id> <reason>", reply_markup=MAIN_KEYBOARD)
        return
    parts = command.args.split(maxsplit=1)
    if len(parts) < 2 or not parts[0].isdigit():
        await message.answer("Usage: /flag <item_id> <reason>", reply_markup=MAIN_KEYBOARD)
        return
    item_id = int(parts[0])
    reason = parts[1]
    try:
        await api.flag_item(item_id, reason)
        await message.answer("🚩 Report flagged for admin review.", reply_markup=MAIN_KEYBOARD)
    except httpx.HTTPError:
        await message.answer("Could not flag report right now.", reply_markup=MAIN_KEYBOARD)


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


@dp.message(F.text.casefold() == "my items")
async def keyboard_my_items(message: Message) -> None:
    await cmd_my_items(message)


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


@dp.message(NewItemForm.photo, F.text.casefold() == "skip photo")
async def wizard_skip_photo(message: Message, state: FSMContext) -> None:
    await state.update_data(image_path=None, image_filename=None, image_mime_type=None)
    await _store_and_continue(message, state, "photo", "")


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


@dp.callback_query(NewItemForm.category, F.data.startswith("cat:"))
async def category_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.data:
        await callback.answer()
        return
    payload = callback.data.split(":", maxsplit=2)
    if len(payload) != 3:
        await callback.answer("Invalid category action", show_alert=True)
        return
    action, value = payload[1], payload[2]
    categories = await api.get_categories()
    if action == "page":
        page = max(0, int(value))
        data = await state.get_data()
        suggested = data.get("category_suggested")
        await callback.message.edit_reply_markup(reply_markup=_category_keyboard(categories, page=page, suggested=suggested))
        await callback.answer()
        return
    if action == "choose":
        await _store_and_continue(callback.message, state, "category", value)
        await callback.answer(f"Category selected: {value}")
        return
    await callback.answer()


@dp.message(NewItemForm.category)
async def form_category(message: Message, state: FSMContext) -> None:
    category = message.text.strip()
    categories = await api.get_categories()
    lookup = {name.lower(): name for name in categories}
    category = lookup.get(category.lower(), category)
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


@dp.message(NewItemForm.photo, F.photo)
async def form_photo(message: Message, state: FSMContext) -> None:
    photo: PhotoSize = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    try:
        image_data = await api.upload_item_image(file_bytes.read(), filename=f"{photo.file_id}.jpg", mime_type="image/jpeg")
    except httpx.HTTPError:
        await message.answer("Photo upload failed. Please try another image or tap Skip Photo.", reply_markup=PHOTO_STEP_KEYBOARD)
        return
    await state.update_data(**image_data)
    await _store_and_continue(message, state, "photo", "uploaded")


@dp.message(NewItemForm.photo)
async def form_photo_invalid(message: Message) -> None:
    await message.answer("Please send a photo, or tap Skip Photo.", reply_markup=PHOTO_STEP_KEYBOARD)


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
            "image_path": data.get("image_path"),
            "image_filename": data.get("image_filename"),
            "image_mime_type": data.get("image_mime_type"),
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
        image_url = _photo_url(item.get("image_path"))
        if image_url:
            await callback.message.answer_photo(photo=image_url, caption=f"✅ Item created: #{item['id']} {item['title']}", reply_markup=MAIN_KEYBOARD)
        else:
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
            for m in matches[:3]:
                await callback.message.answer(
                    f"Match candidate: #{m['id']} {m['title']}",
                    reply_markup=_claim_actions_keyboard(item["id"], m["id"]),
                )

            strong_matches = [m for m in matches if float(m.get("relevance_score", 0)) >= 7.0]
            if strong_matches:
                await _notify_strong_matches(callback.bot, item, strong_matches)
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
    keyboard = PHOTO_STEP_KEYBOARD if field == "photo" else FORM_KEYBOARD
    await callback.message.answer(
        f"Editing {STEP_META[field]['title']}.\n{STEP_META[field]['prompt']}",
        reply_markup=keyboard,
    )
    await callback.answer()


async def _notify_strong_matches(bot: Bot, source_item: dict, matches: list[dict]) -> None:
    creator_id = source_item.get("telegram_user_id")
    notified: set[int] = set()
    if creator_id:
        notified.add(int(creator_id))

    for match in matches:
        owner_id = match.get("telegram_user_id")
        if not owner_id:
            continue
        owner_id = int(owner_id)
        if owner_id in notified:
            continue
        notified.add(owner_id)
        try:
            await bot.send_message(
                owner_id,
                "🔔 Possible match found for your report.\n"
                f"Your potential match: {match['title']}\n"
                f"New report: {source_item['title']}\n"
                f"Confidence: {match.get('confidence', 'low').title()}\n"
                f"Why: {', '.join(match.get('reasons', [])[:3]) or 'similar signals'}",
                reply_markup=MAIN_KEYBOARD,
            )
            if match.get("image_path"):
                await bot.send_photo(owner_id, photo=_photo_url(match["image_path"]))
        except Exception:
            continue

    if creator_id and matches:
        try:
            top = matches[0]
            await bot.send_message(
                int(creator_id),
                "🔔 Strong possible match detected for your new report.\n"
                f"Matched item: {top['title']}\n"
                f"Confidence: {top.get('confidence', 'low').title()}",
                reply_markup=MAIN_KEYBOARD,
            )
            if top.get("image_path"):
                await bot.send_photo(int(creator_id), photo=_photo_url(top["image_path"]))
        except Exception:
            return


@dp.callback_query(F.data.startswith("myitem:"))
async def my_item_action(callback: CallbackQuery) -> None:
    _, action, item_id_raw = callback.data.split(":")
    item_id = int(item_id_raw)
    user_id = callback.from_user.id

    try:
        if action == "matches":
            matches = await api.get_matches(item_id)
            if not matches:
                await callback.message.answer("No matches yet for this report.", reply_markup=MAIN_KEYBOARD)
            else:
                lines = [
                    f"• {m['title']} ({m['category']}, {m['location']}) — {m['confidence']} ({m['relevance_score']}/10)"
                    for m in matches[:5]
                ]
                await callback.message.answer("Matches:\n" + "\n".join(lines), reply_markup=MAIN_KEYBOARD)
        elif action == "resolve":
            item = await api.resolve_item(item_id, user_id)
            await callback.message.answer(
                f"✅ Report #{item['id']} marked as resolved.",
                reply_markup=_item_actions_keyboard(item['id'], item['lifecycle']),
            )
        elif action == "reopen":
            item = await api.reopen_item(item_id, user_id)
            await callback.message.answer(
                f"♻️ Report #{item['id']} reopened.",
                reply_markup=_item_actions_keyboard(item['id'], item['lifecycle']),
            )
        elif action == "delete":
            item = await api.delete_item(item_id, user_id)
            await callback.message.answer(
                f"🗑 Report #{item['id']} moved to deleted.",
                reply_markup=MAIN_KEYBOARD,
            )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 403:
            await callback.message.answer("You can manage only your own reports.", reply_markup=MAIN_KEYBOARD)
        elif exc.response.status_code == 404:
            await callback.message.answer("Report not found.", reply_markup=MAIN_KEYBOARD)
        else:
            await callback.message.answer("Could not complete this action right now.", reply_markup=MAIN_KEYBOARD)

    await callback.answer()


@dp.callback_query(F.data.startswith("claim:"))
async def claim_action(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    user_id = callback.from_user.id
    try:
        if action == "create":
            source_item_id = int(parts[2])
            target_item_id = int(parts[3])
            claim = await api.create_claim(source_item_id, target_item_id, user_id)
            await callback.message.answer(f"✅ Claim #{claim['id']} submitted. Waiting for owner approval.", reply_markup=MAIN_KEYBOARD)
            owner_id = claim.get("owner_telegram_user_id")
            if owner_id:
                try:
                    await callback.bot.send_message(
                        int(owner_id),
                        f"New claim #{claim['id']} for your report #{claim['target_item_id']}.\n"
                        f"Requester item: #{claim['source_item_id']}\n"
                        f"Message: {claim.get('claim_message') or 'No message'}",
                        reply_markup=_incoming_claim_keyboard(claim["id"]),
                    )
                except Exception:
                    pass
        elif action == "notmatch":
            source_item_id = int(parts[2])
            target_item_id = int(parts[3])
            claim = await api.create_claim(source_item_id, target_item_id, user_id, claim_message="Marked as not match")
            claim = await api.claim_action(claim["id"], "not-match", user_id)
            await callback.message.answer(f"Marked pair as not-match (claim #{claim['id']}).", reply_markup=MAIN_KEYBOARD)
        elif action in {"approve", "reject", "complete"}:
            claim_id = int(parts[2])
            claim = await api.claim_action(claim_id, action, user_id)
            await callback.message.answer(f"Claim #{claim['id']} updated: {claim['status'].upper()}.", reply_markup=MAIN_KEYBOARD)
            other_id = (
                claim.get("requester_telegram_user_id")
                if claim.get("owner_telegram_user_id") == user_id
                else claim.get("owner_telegram_user_id")
            )
            if other_id:
                text = f"Claim #{claim['id']} is now {claim['status'].upper()}."
                if claim.get("shared_source_contact") or claim.get("shared_target_contact"):
                    text += (
                        "\nApproved contact details:\n"
                        f"• Source: {claim.get('shared_source_contact') or '-'}\n"
                        f"• Target: {claim.get('shared_target_contact') or '-'}"
                    )
                try:
                    await callback.bot.send_message(int(other_id), text, reply_markup=MAIN_KEYBOARD)
                except Exception:
                    pass
    except httpx.HTTPError:
        await callback.message.answer("Claim action failed. Please try again.", reply_markup=MAIN_KEYBOARD)
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
