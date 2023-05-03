from telebot.async_telebot import AsyncTeleBot
from telebot.callback_data import CallbackData, CallbackDataFilter
from telebot import types
from telebot.asyncio_filters import AdvancedCustomFilter
from furretweet.config import config
from furretweet import filters
from furretweet.models import StreamResponse
from datetime import datetime, timezone
from furretweet.tweepy import client as tweepy_client

import logging

logging.getLogger("TeleBot").setLevel(logging.WARNING)

# ==============================
#
# NOT YET IMPLEMENTED
#
# ==============================


class FurTelegram(AsyncTeleBot):
    def __init__(self, token, **kwargs):
        super().__init__(token, **kwargs)

    def failed_tweet_keyboard(self, tweet_id: str, author_id: str) -> types.InlineKeyboardMarkup:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                text="Retweet",
                callback_data=failed_tweet_factory.new(
                    tweet_id=tweet_id, author_id=author_id, action="retweet"
                ),
            ),
            types.InlineKeyboardButton(
                text="Add to blacklist",
                callback_data=failed_tweet_factory.new(
                    tweet_id=tweet_id, author_id=author_id, action="add_blacklist"
                ),
            ),
            row_width=2,
        )
        return keyboard

    def unretweet_keyboard(self, tweet_id: str, author_id: str) -> types.InlineKeyboardMarkup:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                text="Unretweet",
                callback_data=failed_tweet_factory.new(
                    tweet_id=tweet_id, author_id=author_id, action="unretweet"
                ),
            ),
            row_width=2,
        )
        return keyboard

    def remove_blacklist_keyboard(
        self, tweet_id: str, author_id: str
    ) -> types.InlineKeyboardMarkup:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                text="Remove from blacklist",
                callback_data=failed_tweet_factory.new(
                    tweet_id=tweet_id, author_id=author_id, action="remove_blacklist"
                ),
            ),
            row_width=2,
        )
        return keyboard

    def _format_filter(self, filter: filters.BaseFilter) -> str:
        details: str | None = None

        filter_match = filter
        match filter_match:
            case filters.MinimumFollowersFilter():
                details = f"Followers: {filter.details['followers_count']}, Min: {filter.details['min_followers']}"
            case filters.MinimumAccountAgeFilter():
                details = f"Days: {(datetime.now(timezone.utc) - filter.details['account_created_at']).days}, Min: {filter.details['min_account_days']}"
            case filters.MaximumNewLinesFilter():
                details = f"New lines: {filter.details['new_lines_count']}, Max: {filter.details['max_new_lines']}"
            case filters.MaximumHashtagsFilter():
                details = f"Hashtags: {filter.details['hashtags_count']}, Max: {filter.details['max_hashtags']}"
            case filters.BannedTermsFilter():
                details = ", ".join(filter.details["words_found"])

        if details is None:
            return filter.name

        return f"{filter.name}: [ {details} ]"

    def _format_failed_filters(self, failed_filters: list[filters.BaseFilter]) -> str:
        # Return Exemple:
        # Failed filters:
        # ┠ MinimumFollowersFilter: [ Followers: 1280, Min: 2000 ]
        # ┠ BannedTermsFilter: [ bad, takes, here ]
        # ┖ MinimumAccountAgeFilter: [ Days: 256, Min: 300 ]
        middle_char = "┠"
        end_char = "┖"

        if not failed_filters:
            return "No failed filters"

        formatted_filters = []
        for index, filter in enumerate(failed_filters):
            formatted_filter = self._format_filter(filter)
            if index == len(failed_filters) - 1:
                formatted_filters.append(f"{end_char} {formatted_filter}")
            else:
                formatted_filters.append(f"{middle_char} {formatted_filter}")

        return "Failed filters:\n" + "\n".join(formatted_filters)

    def _format_response(self, response: StreamResponse) -> str:
        return (
            f"Author: {response.author.username}\n"
            + self._format_failed_filters(response.failed_filters)
            + f"\n{response.url}"
        )

    async def send_response_to_feed(self, response: StreamResponse):
        await bot.send_message(
            chat_id=config.telegram.feed_channel_id,
            text=self._format_response(response),
            reply_markup=self.failed_tweet_keyboard(
                tweet_id=str(response.tweet.id), author_id=str(response.author.id)
            ),
        )


class FailedTweetCallbackFilter(AdvancedCustomFilter):
    key = "config"

    async def check(self, call: types.CallbackQuery, config: CallbackDataFilter):
        return config.check(query=call)


bot = FurTelegram(config.telegram.token)
bot.add_custom_filter(FailedTweetCallbackFilter())
failed_tweet_factory = CallbackData("tweet_id", "author_id", "action", prefix="failed_tweet")


@bot.message_handler(commands=["start"])
async def start(message: types.Message):
    await bot.reply_to(message, "Welcome to Furretweet Bot!")


@bot.callback_query_handler(func=None, config=failed_tweet_factory.filter(action="add_blacklist"))
async def failed_tweet_add_blacklist_callback(callback: types.CallbackQuery):
    callback_data: dict = failed_tweet_factory.parse(callback_data=callback.data)
    author_id = callback_data["author_id"]
    tweet_id = callback_data["tweet_id"]

    # TODO: Add author to blacklist

    await bot.edit_message_reply_markup(
        callback.message.chat.id,
        callback.message.message_id,
        reply_markup=bot.remove_blacklist_keyboard(tweet_id=tweet_id, author_id=author_id),
    )
    await bot.answer_callback_query(
        callback.id, f"Opa, vou adicionar o autor {callback_data['author_id']} na blacklist"
    )


@bot.callback_query_handler(
    func=None, config=failed_tweet_factory.filter(action="remove_blacklist")
)
async def failed_tweet_remove_blacklist_callback(callback: types.CallbackQuery):
    callback_data: dict = failed_tweet_factory.parse(callback_data=callback.data)
    author_id = callback_data["author_id"]
    tweet_id = callback_data["tweet_id"]

    # TODO: Remove author from blacklist

    await bot.edit_message_reply_markup(
        callback.message.chat.id,
        callback.message.message_id,
        reply_markup=bot.failed_tweet_keyboard(tweet_id=tweet_id, author_id=author_id),
    )
    await bot.answer_callback_query(
        callback.id, f"Opa, vou remover o autor {callback_data['author_id']} da blacklist"
    )


@bot.callback_query_handler(func=None, config=failed_tweet_factory.filter(action="retweet"))
async def failed_tweet_retweet_callback(callback: types.CallbackQuery):
    callback_data: dict = failed_tweet_factory.parse(callback_data=callback.data)
    author_id = callback_data["author_id"]
    tweet_id = callback_data["tweet_id"]

    # TODO: Retweet tweet but check the rate limit

    await bot.edit_message_reply_markup(
        callback.message.chat.id,
        callback.message.message_id,
        reply_markup=bot.unretweet_keyboard(tweet_id=tweet_id, author_id=author_id),
    )
    await bot.answer_callback_query(
        callback.id, f"Eba, vou retweetar o tweet {callback_data['tweet_id']}"
    )


@bot.callback_query_handler(func=None, config=failed_tweet_factory.filter(action="unretweet"))
async def failed_tweet_unretweet_callback(callback: types.CallbackQuery):
    callback_data: dict = failed_tweet_factory.parse(callback_data=callback.data)
    author_id = callback_data["author_id"]
    tweet_id = callback_data["tweet_id"]

    # TODO: Unretweet tweet but check the rate limit somehow

    await bot.edit_message_reply_markup(
        callback.message.chat.id,
        callback.message.message_id,
        reply_markup=bot.failed_tweet_keyboard(tweet_id=tweet_id, author_id=author_id),
    )
    await bot.answer_callback_query(
        callback.id, f"Ok, vou desretweetar o tweet {callback_data['tweet_id']}"
    )


import asyncio

asyncio.run(bot.polling())
