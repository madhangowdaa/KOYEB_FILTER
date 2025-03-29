import os
from pyrogram import Client, filters, enums
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from pyrogram.types import Message
from info import IMDB_TEMPLATE
from utils import extract_user, get_file_id, get_poster, last_online
import time
from datetime import datetime
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

@Client.on_message(filters.command('id'))
async def showid(client, message):
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        user_id = message.chat.id
        first = message.from_user.first_name
        last = message.from_user.last_name or ""
        username = message.from_user.username
        dc_id = message.from_user.dc_id or ""
        await message.reply_text(
            f"<b>➲ First Name:</b> {first}\n<b>➲ Last Name:</b> {last}\n<b>➲ Username:</b> {username}\n<b>➲ Telegram ID:</b> <code>{user_id}</code>\n<b>➲ Data Centre:</b> <code>{dc_id}</code>",
            quote=True
        )

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        _id = ""
        _id += (
            "<b>➲ Chat ID</b>: "
            f"<code>{message.chat.id}</code>\n"
        )
        if message.reply_to_message:
            _id += (
                "<b>➲ User ID</b>: "
                f"<code>{message.from_user.id if message.from_user else 'Anonymous'}</code>\n"
                "<b>➲ Replied User ID</b>: "
                f"<code>{message.reply_to_message.from_user.id if message.reply_to_message.from_user else 'Anonymous'}</code>\n"
            )
            file_info = get_file_id(message.reply_to_message)
        else:
            _id += (
                "<b>➲ User ID</b>: "
                f"<code>{message.from_user.id if message.from_user else 'Anonymous'}</code>\n"
            )
            file_info = get_file_id(message)
        if file_info:
            _id += (
                f"<b>{file_info.message_type}</b>: "
                f"<code>{file_info.file_id}</code>\n"
            )
        await message.reply_text(
            _id,
            quote=True
        )

@Client.on_message(filters.command(["info"]))
async def who_is(client, message):
    # https://github.com/SpEcHiDe/PyroGramBot/blob/master/pyrobot/plugins/admemes/whois.py#L19
    status_message = await message.reply_text(
        "`Fetching user info...`"
    )
    await status_message.edit(
        "`Processing user info...`"
    )
    from_user = None
    from_user_id, _ = extract_user(message)
    try:
        from_user = await client.get_users(from_user_id)
    except Exception as error:
        await status_message.edit(str(error))
        return
    if from_user is None:
        return await status_message.edit("no valid user_id / message specified")
    message_out_str = ""
    message_out_str += f"<b>➲First Name:</b> {from_user.first_name}\n"
    last_name = from_user.last_name or "<b>None</b>"
    message_out_str += f"<b>➲Last Name:</b> {last_name}\n"
    message_out_str += f"<b>➲Telegram ID:</b> <code>{from_user.id}</code>\n"
    username = from_user.username or "<b>None</b>"
    dc_id = from_user.dc_id or "[User Doesn't Have A Valid DP]"
    message_out_str += f"<b>➲Data Centre:</b> <code>{dc_id}</code>\n"
    message_out_str += f"<b>➲User Name:</b> @{username}\n"
    message_out_str += f"<b>➲User 𝖫𝗂𝗇𝗄:</b> <a href='tg://user?id={from_user.id}'><b>Click Here</b></a>\n"
    if message.chat.type in ((enums.ChatType.SUPERGROUP, enums.ChatType.CHANNEL)):
        try:
            chat_member_p = await message.chat.get_member(from_user.id)
            joined_date = (
                chat_member_p.joined_date or datetime.now()
            ).strftime("%Y.%m.%d %H:%M:%S")
            message_out_str += (
                "<b>➲Joined this Chat on:</b> <code>"
                f"{joined_date}"
                "</code>\n"
            )
        except UserNotParticipant:
            pass
    chat_photo = from_user.photo
    if chat_photo:
        local_user_photo = await client.download_media(
            message=chat_photo.big_file_id
        )
        buttons = [[
            InlineKeyboardButton('🔐 Close', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=local_user_photo,
            quote=True,
            reply_markup=reply_markup,
            caption=message_out_str,
            parse_mode=enums.ParseMode.HTML,
            disable_notification=True
        )
        os.remove(local_user_photo)
    else:
        buttons = [[
            InlineKeyboardButton('🔐 Close', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_text(
            text=message_out_str,
            reply_markup=reply_markup,
            quote=True,
            parse_mode=enums.ParseMode.HTML,
            disable_notification=True
        )
    await status_message.delete()

@Client.on_message(filters.command(["imdb", 'search']))
async def imdb_search(client, message):
    if ' ' in message.text:
        k = await message.reply('Searching ImDB')
        r, title = message.text.split(None, 1)
        movies = await get_poster(title, bulk=True)
        if not movies:
            return await message.reply("No results Found")
        btn = [
            [
                InlineKeyboardButton(
                    text=f"{movie.get('title')} - {movie.get('year')}",
                    callback_data=f"imdb#{movie.movieID}",
                )
            ]
            for movie in movies
        ]
        await k.edit('Here is what i found on IMDb', reply_markup=InlineKeyboardMarkup(btn))
    else:
        await message.reply('Give me a movie / series Name')

@Client.on_callback_query(filters.regex('^imdb'))
async def imdb_callback(bot: Client, quer_y: CallbackQuery):
    i, movie = quer_y.data.split('#')
    imdb = await get_poster(query=movie, id=True)
    btn = [
            [
                InlineKeyboardButton(
                    text=f"{imdb.get('title')}",
                    url=imdb['url'],
                )
            ]
        ]
    message = quer_y.message.reply_to_message or quer_y.message
    if imdb:
        caption = IMDB_TEMPLATE.format(
            query = imdb['title'],
            title = imdb['title'],
            votes = imdb['votes'],
            aka = imdb["aka"],
            seasons = imdb["seasons"],
            box_office = imdb['box_office'],
            localized_title = imdb['localized_title'],
            kind = imdb['kind'],
            imdb_id = imdb["imdb_id"],
            cast = imdb["cast"],
            runtime = imdb["runtime"],
            countries = imdb["countries"],
            certificates = imdb["certificates"],
            languages = imdb["languages"],
            director = imdb["director"],
            writer = imdb["writer"],
            producer = imdb["producer"],
            composer = imdb["composer"],
            cinematographer = imdb["cinematographer"],
            music_team = imdb["music_team"],
            distributors = imdb["distributors"],
            release_date = imdb['release_date'],
            year = imdb['year'],
            genres = imdb['genres'],
            poster = imdb['poster'],
            plot = imdb['plot'],
            rating = imdb['rating'],
            url = imdb['url'],
            **locals()
        )
    else:
        caption = "No Results"
    if imdb.get('poster'):
        try:
            await quer_y.message.reply_photo(photo=imdb['poster'], caption=caption, reply_markup=InlineKeyboardMarkup(btn))
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            await quer_y.message.reply_photo(photo=poster, caption=caption, reply_markup=InlineKeyboardMarkup(btn))
        except Exception as e:
            logger.exception(e)
            await quer_y.message.reply(caption, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=False)
        await quer_y.message.delete()
    else:
        await quer_y.message.edit(caption, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=False)
    await quer_y.answer()

GENRE_EMOJIS = {
    "Action": "🔥", "Adventure": "🧭", "Animation": "🎨",
    "Comedy": "😂", "Crime": "🔫", "Drama": "🎭",
    "Fantasy": "🧙‍♂️", "Horror": "👻", "Mystery": "🕵️‍♂️",
    "Romance": "❤️", "Sci-Fi": "🚀", "Thriller": "🔪",
    "War": "⚔️", "Western": "🤠"
}

def format_genres(genre_list):
    """Formats genres with emojis and limits to 2 genres."""
    formatted = [f"#{g} {GENRE_EMOJIS.get(g, '')}" for g in genre_list[:2]]
    return " | ".join(formatted) if formatted else "N/A"

@Client.on_message(filters.command(["get"]))
async def imdb_search(client, message: Message):
    if ' ' in message.text:
        k = await message.reply('🔎 Searching IMDb...')
        _, title = message.text.split(None, 1)
        movies = await get_poster(title, bulk=True)
        if not movies:
            return await message.reply("❌ No results found.")
        
        # Generate buttons for multiple search results
        btn = [
            [
                InlineKeyboardButton(
                    text=f"{movie.get('title')} - {movie.get('year')}",
                    callback_data=f"imdb#{movie.movieID}",
                )
            ]
            for movie in movies
        ]
        await k.edit('🎬 Here is what I found on IMDb:', reply_markup=InlineKeyboardMarkup(btn))
    else:
        await message.reply('❗ Provide a movie or series name after the command.')

@Client.on_message(filters.command(["getimg"]))
async def imdb_poster_search(client, message: Message):
    if ' ' in message.text:
        k = await message.reply('🔎 Searching IMDb...')
        _, title = message.text.split(None, 1)
        movies = await get_poster(title, bulk=True)

        if not movies:
            return await k.edit("❌ No results found.")

        # Generate buttons for multiple search results
        btn = [
            [
                InlineKeyboardButton(
                    text=f"{movie.get('title')} - {movie.get('year')}",
                    callback_data=f"poster#{movie.movieID}",
                )
            ]
            for movie in movies
        ]
        await k.edit('🖼 Select a movie to get the poster:', reply_markup=InlineKeyboardMarkup(btn))
    else:
        await message.reply('❗ Provide a movie or series name after the command.')

# Callback handler for fetching only the poster
@Client.on_callback_query(filters.regex('^poster'))
async def imdb_poster_callback(bot: Client, query: CallbackQuery):
    _, movie_id = query.data.split('#')
    imdb = await get_poster(query=movie_id, id=True)

    if not imdb or "poster" not in imdb:
        return await query.message.edit("❌ No poster found.", reply_markup=None)

    poster_url = imdb.get("poster")
    movie_title = imdb.get("title", "Unknown Movie")
    imdb_link = imdb.get("url", "https://www.imdb.com/")

    await query.message.reply_photo(
        photo=poster_url,
        caption=f"<b>{movie_title}</b>\n\n🔗 <b>Uploaded by: @MoviezAddaKA</b>",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 View on IMDb", url=imdb_link)]]) 
    )
    await query.answer()



@Client.on_callback_query(filters.regex('^imdb'))
async def imdb_callback(bot: Client, query: CallbackQuery):
    _, movie_id = query.data.split('#')
    imdb = await get_poster(query=movie_id, id=True)

    if not imdb:
        return await query.message.edit("❌ No details found.", reply_markup=None)

    imdb_id = imdb.get('id', '').strip()  # Ensure it's a valid string

    # IMDb Links
    imdb_link = imdb.get('url', 'https://www.imdb.com/')
    release_info_link = f"https://www.imdb.com/title/{imdb_id}/releaseinfo" if imdb_id else "https://www.imdb.com/"
    imdb_releaseinfo_link = imdb_link + "/releaseinfo"

    # Convert release date format to DD/MM/YYYY safely
    raw_release_date = imdb.get('release_date', 'N/A')

    if isinstance(raw_release_date, str) and raw_release_date not in ["N/A", ""]:
        raw_release_date = " ".join(raw_release_date.split())  # Fix extra spaces
        try:
            formatted_date = datetime.strptime(raw_release_date, "%d %B %Y").strftime("%d/%m/%Y")
        except ValueError:
            formatted_date = raw_release_date  # Use the original if parsing fails
    else:
        formatted_date = "N/A"  # Default if missing

    # Format genres with only ONE emoji
    genres = [g.strip() for g in imdb.get('genres', '').split(',') if g.strip()]  # Removes empty entries
    first_genre = genres[0] if genres else "Unknown"
    emoji = GENRE_EMOJIS.get(first_genre, "🎭")  # Default emoji if not found
    genres_text = f"{emoji} " + ", ".join([f"#{g.replace(' ', '_')}" for g in genres])  # Added comma


    # Format languages properly
    languages = imdb.get('languages', '').split(',')
    languages_text = " ".join([f"#{l.strip().replace(' ', '_')}" for l in languages if l.strip()])

    # Only use ONE "Also Known As" title (without the year)
    main_title = imdb.get('title', 'N/A')
    aka_titles = imdb.get('aka', '').split(',')
    also_known_as = aka_titles[0] if aka_titles else main_title  # Remove year from "Also Known As"

    # Convert runtime (if available) to "H h M min" format
    runtime_minutes = imdb.get('runtime', 'N/A')
    if isinstance(runtime_minutes, str) and runtime_minutes.isdigit():
        hours, minutes = divmod(int(runtime_minutes), 60)
        formatted_runtime = f"{hours}h {minutes}min" if hours else f"{minutes}min"
    else:
        formatted_runtime = runtime_minutes  # If runtime is not a digit, use original

    # Formatting the response
    response_text = (
        f"<b>Movie:</b> <a href='{imdb_link}'>{imdb.get('title', 'N/A')} [{imdb.get('year', '2020')}]</a>\n"
        f"<i>Also Known As</i>: {imdb.get('title', '')}\n"
        f"<b>Rating ⭐️:</b> {imdb.get('rating', '')} / 10\n"
        f"<code>({imdb.get('rating','')} based on {imdb.get('votes', '0')} user ratings) || {formatted_runtime} |</code>\n"
        f"<b>Release Date:</b> <a href='{imdb_releaseinfo_link}'>{formatted_date}</a>\n"
        f"<b>Genre:</b> {genres_text}\n"
        f"<b>Language:</b> {languages_text}"
    )

    # Send message with formatted response
    await query.message.reply(
        response_text,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 View on IMDb", url=imdb_link)]])
    )

    await query.answer()
        

        
