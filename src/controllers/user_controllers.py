#
# Copyright (C) Halk-lai Liff <halkliff@pm.me> & Werberth Lins <werberth.lins@gmail.com>, 2018-present
# Distributed under GNU AGPLv3 License, found at the root tree of this source, by the name of LICENSE
# You can also find a copy of this license at GNU's site, as it follows <https://www.gnu.org/licenses/agpl-3.0.en.html>
#
# THIS SOFTWARE IS PRESENTED AS-IS, WITHOUT ANY WARRANTY, OR LIABILITY FROM ITS AUTHORS
# EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE.  THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM
# IS WITH YOU.  SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF
# ALL NECESSARY SERVICING, REPAIR OR CORRECTION.
#
# IN NO EVENT UNLESS REQUIRED BY APPLICABLE LAW OR AGREED TO IN WRITING
# WILL ANY COPYRIGHT HOLDER, OR ANY OTHER PARTY WHO MODIFIES AND/OR CONVEYS
# THE PROGRAM AS PERMITTED ABOVE, BE LIABLE TO YOU FOR DAMAGES, INCLUDING ANY
# GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE
# USE OR INABILITY TO USE THE PROGRAM (INCLUDING BUT NOT LIMITED TO LOSS OF
# DATA OR DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD
# PARTIES OR A FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER PROGRAMS),
# EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGES.
#

from ..models.user_models import User, Bot
from ..utils.function_handlers import to_async
import datetime
from typing import Union, List, Iterable
import bcrypt


class UserAlreadyAdded(BaseException):
    pass


class BotAlreadyAdded(BaseException):
    pass


async def add_user(user_id: int, password_hash: str, *, first_name: str = None, last_name: str = None,
                   username: str = None, profile_photo: str = None, profile_thumb: str = None)-> User:
    """
    Adds users to the database. An user is either a channel owner or channel admin; normal Telegram users are not
    Stored.
    :param user_id: Telegram's user ID
    :param password_hash: A password Hash consisting on the sha256 of the user ID + the unicode password, case sensitive
    :param first_name: Telegram user's First Name
    :param last_name: Telegram user's Last Name
    :param username: Telegram user's username
    :param profile_photo: Telegram's unique File identifier of the user's profile photo
    :param profile_thumb: Telegram's unique File identifier of the user's profile thumbnail photo
    :return: [User] instance from the database
    """

    try:
        get = to_async(User.objects.get)
        user = await get({'userId': user_id})
        if user.is_deleted:
            User.objects.raw({'userId': user_id}).update({'$set': {'isDeleted': False}, '$unset': {'deletedDate': ''}})
            user = await get_users(user_id=user_id)
            return await edit_user_info(user_model=user, new_password_hash=password_hash,
                                        first_name=first_name, last_name=last_name, username=username)
        else:
            raise UserAlreadyAdded('User is already added.')

    except User.DoesNotExist:
        join_time = datetime.datetime.utcnow()
        salt = bcrypt.gensalt()
        pw = bcrypt.hashpw(password_hash.encode(), salt)
        user = User(
            _id=user_id,
            uid=user_id,
            user_secure=pw,
            join_date=join_time
        )
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if username is not None:
            user.username = username
        if profile_photo is not None:
            user.profile_photo = profile_photo
            user.profile_thumbnail = profile_thumb
        if user.is_valid():
            save = to_async(user.save)
            await save(full_clean=True)
            return user
        else:
            raise user.full_clean()


async def add_bot(bot_id: int, bot_token: str, *, user_model: User = None, user_id: int = None,
                  bot_name: str = '', username: str = None,
                  profile_photo: str = None, profile_thumb: str = None)-> Bot:
    """
    Adds bots to the database. An user is either a channel owner or channel admin; normal Telegram users are not
    Stored.
    :param bot_id: Telegram's bot ID
    :param bot_token: Telegram's API access token
    :param user_model: Model instance of a user in the database
    :param user_id: Telegram's ID. Used only if `user_model` is None.
    :param bot_name: Telegram bot's name
    :param username: Telegram bot's username
    :param profile_photo: Telegram's unique File identifier of the user's profile photo
    :param profile_thumb: Telegram's unique File identifier of the user's profile thumbnail photo
    :return: [Bot] instance from the database
    """

    try:
        get = to_async(Bot.objects.get)
        bot = await get({'$or': [{'botId': bot_id}, {'botToken': bot_token}]})
        if bot.is_deleted:
            Bot.objects.raw({'$or': [{'botId': bot_id}, {'botToken': bot_token}]})\
                .update({'$set': {'isDeleted': False}, '$unset': {'deletedDate': ''}})
            return await edit_bot_info(bot_id=bot_id, bot_token=bot_token, bot_name=bot_name, username=username,
                                       profile_photo=profile_photo, profile_thumb=profile_thumb)
        else:
            raise BotAlreadyAdded('Bot is already added.')

    except Bot.DoesNotExist:
        try:

            user = user_model if user_model is not None else await get_users(user_id=user_id)
            join_time = datetime.datetime.utcnow()
            bot = User(
                _id=bot_id,
                bot_id=bot_id,
                owner=user,
                join_date=join_time,
                name=bot_name
            )
            if username is not None:
                bot.username = username
            if profile_photo is not None:
                bot.profile_photo = profile_photo
                bot.profile_thumbnail = profile_thumb
            if bot.is_valid():
                save = to_async(bot.save)
                await save(full_clean=True)
                return bot
            else:
                raise bot.full_clean()
        except User.DoesNotExist:
            raise


async def edit_user_info(user_model: User = None, user_id: int = None, *, new_password_hash: str = None,
                         first_name: str = None, last_name: str = None, username: str = None,
                         profile_photo: str = None, profile_thumb: str = None)-> User:
    """
    Helper to edit User Info in the database.
    :param user_model: Model instance of a user in the database.
    :param user_id: Telegram's ID. Used only if `user_model` is None
    :param new_password_hash: A new password hash to be the new password.
    :param first_name: Telegram user's First Name
    :param last_name: Telegram user's Last Name
    :param username: Telegram user's username
    :param profile_photo: Telegram's unique File identifier of the user's profile photo
    :param profile_thumb: Telegram's unique File identifier of the user's profile thumbnail photo
    :return: [User] updated instance from the database
    """

    try:
        user = user_model if user_model is not None else await get_users(user_id=user_id)

        if new_password_hash is not None:
            # Only edit the password of an user that is authenticated
            if user_model is not None:
                new_pw = bcrypt.hashpw(new_password_hash.encode(), user.user_secure)
                user.user_secure = new_pw

        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if username is not None:
            user.username = username
        if profile_photo is not None:
            user.profile_photo = profile_photo
            user.profile_thumbnail = profile_thumb

        if user.is_valid():
            save = to_async(user.save)
            await save(full_clean=True)
            return user
        else:
            raise user.full_clean()

    except User.DoesNotExist:
        if user_id is not None and new_password_hash is not None:
            return await add_user(user_id=user_id, password_hash=new_password_hash, first_name=first_name,
                                  last_name=last_name, username=username)
        else:
            raise


async def edit_bot_info(bot_model: Bot = None, bot_id: int = None, bot_token: str = None, *,
                        bot_name: str = None, username: str = None,
                        profile_photo: str = None, profile_thumb: str = None)-> Bot:
    """
    Helper to edit Bot Info in the database.
    :param bot_model: Model instance of a bot in the database
    :param bot_id: Telegram's bot ID. Only used if `bot_model` is None
    :param bot_token: Telegram's API access token
    :param bot_name: Telegram bot's name
    :param username: Telegram bot's username
    :param profile_photo: Telegram's unique File identifier of the user's profile photo
    :param profile_thumb: Telegram's unique File identifier of the user's profile thumbnail photo
    :return: [Bot] updated instance from the database
    """

    try:
        bot = bot_model if bot_model is not None else await get_bots(bot_id=bot_id, bot_token=bot_token)

        if bot_token is not None:
            bot.bot_token = bot_token
        if bot_name is not None:
            bot.bot_name = bot_name
        if username is not None:
            bot.username = username
        if profile_photo is not None:
            bot.profile_photo = profile_photo
            bot.profile_thumbnail = profile_thumb

        if bot.is_valid():
            save = to_async(bot.save)
            await save(full_clean=True)
            return bot
        else:
            raise bot.full_clean()

    except Bot.DoesNotExist:
        if bot_id is not None and bot_token is not None:
            return await add_bot(bot_id=bot_id, bot_token=bot_token, bot_name=bot_name, username=username,
                                 profile_photo=profile_photo, profile_thumb=profile_thumb)
        else:
            raise


async def delete_user(user_model: User = None, user_id: int = None)-> bool:
    """
    Remove a user from the database, using it's Telegram's ID, by setting the deleted flag.
    :param user_model: Model instance of a user in the database.
    :param user_id: Telegram's ID. Used only if `user_model` is None.
    :return: True if deleted, False if the user was never added, or the Exception raised by the data validation
             (less likely to happen).
    """
    from ..models.post_models import PostModel
    from ..models.comments_model import Comment
    from ..models.channels_model import Channel
    from .channel_controllers import remove_admins
    try:
        user = user_model if user_model is not None else get_users(user_id=user_id)
        user.is_deleted = True
        user.deleted_date = datetime.datetime.utcnow()

        if user.is_valid():
            save = to_async(user.save)
            await save(full_clean=True)
            data = {'$set': {'isDeleted': True, 'deletedDate': datetime.datetime.utcnow()}}
            comments_raw = to_async(Comment.objects.raw)
            channels_raw = to_async(Channel.objects.raw)
            all_comments = await comments_raw({'userId': user.uid})
            all_channels = await channels_raw({'channelCreator': user.uid, 'isDeleted': False})
            all_admin_only_channels = await channels_raw({'channelAdmins.uid': user.uid})

            comment_update = to_async(all_comments.update)
            channels_update = to_async(all_channels.update)

            await comment_update(data)
            await channels_update(data)
            all_channels = await channels_raw({'channelCreator': user.uid, 'isDeleted': True})
            for channel in all_channels:
                posts_raw = to_async(PostModel.objects.raw)
                all_posts = await posts_raw({'channelId': channel.chid})
                posts_update = to_async(all_posts.update)
                await posts_update(data)
            for channel_model in all_admin_only_channels:
                await remove_admins(channel_model=channel_model, user_model=user)

            return True
        else:
            raise user.full_clean()

    except User.DoesNotExist:
        return False


async def delete_bot(bot_model: Bot = None, bot_id: int = None, bot_token: str = None)-> bool:
    """
    Remove a bot from the database, using it's Telegram's ID or API Token, by setting the deleted flag.
    :param bot_model: Model instance of a user in the database.
    :param bot_id: Telegram's ID. Used only if `bot_model` is None.
    :param bot_token: Telegram's API access token
    :return: True if deleted, False if the user was never added, or the Exception raised by the data validation
             (less likely to happen).
    """
    from ..models.post_models import PostModel
    from ..models.channels_model import Channel
    try:
        bot = bot_model if bot_model is not None else await get_bots(bot_id=bot_id, bot_token=bot_token)
        bot.is_deleted = True
        bot.deleted_date = datetime.datetime.utcnow()

        if bot.is_valid():
            save = to_async(bot.save)
            await save(full_clean=True)
            data = {'$set': {'channelBot': None}}
            posts_raw = to_async(PostModel.objects.raw)
            channels_raw = to_async(Channel.objects.raw)
            all_posts = await posts_raw({'channelBot': bot.bot_id})
            all_channels = await channels_raw({'channelBot': bot.bot_id})

            posts_update = to_async(all_posts.update)
            channels_update = to_async(all_channels.update)
            await posts_update(data)
            await channels_update(data)

            return True
        else:
            raise bot.full_clean()

    except Bot.DoesNotExist:
        return False


async def get_users(user_id: int = None, user_ids: List[int] = None)-> Union[User, Iterable[User]]:
    """
    Gets a single user, or an iterable array of users from the database. Required either `user_id` or `user_ids`
    :param user_id: (Optional) the Telegram's ID of a given user
    :param user_ids: (Optional) a list of Telegram IDs of given users
    :return: a single [User] instance, an iterable of [User] instances, or None, if either the params are None, or there
             are no database matches.
    """

    try:
        get = to_async(User.objects.get)
        raw = to_async(User.objects.raw)
        if user_id is not None:
            user = await get({'userId': user_id, 'isDeleted': False})
            return user
        elif user_ids is not None:
            users = await raw({'userId': {'$in': user_ids}, 'isDeleted': False})
            return users
        else:
            raise User.DoesNotExist
    except User.DoesNotExist:
        raise


def get_bots(bot_id: int = None, bot_ids: List[int] = None,
             bot_token: str = None, bot_tokens: List[str] = None)-> Union[Bot, Iterable[Bot]]:
    """

    Gets a single user, or an iterable array of users from the database. Required either `bot_id`, `bot_ids`,
    `bot_token` or `bot_tokens`
    :param bot_id: Telegram's bot ID
    :param bot_ids: List of Telegram's bot IDs
    :param bot_token: Telegram's API access token
    :param bot_tokens: List of Telegram's API access tokens
    :return: a single [Bot] instance, an iterable of [Bot] instances, or None, if either the params are None, or there
             are no database matches.
    """

    try:
        get = to_async(Bot.objects.get)
        raw = to_async(Bot.objects.raw)
        if bot_id is not None or bot_token is not None:
            bot = await get({'$or': [{'botId': bot_id}, {'botToken': bot_token}]})
            return bot
        elif bot_ids is not None or bot_tokens is not None:
            bots = await raw({'$or': [{'botId': {'$in': bot_ids}}, {'botToken': {'$in': bot_tokens}}]})
            return bots
        else:
            raise Bot.DoesNotExist
    except Bot.DoesNotExist:
        raise
