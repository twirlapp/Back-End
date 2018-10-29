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
import datetime
from typing import Union, List, Iterable


class UserAlreadyAdded(BaseException):
    pass


def add_user(user_id: int, *, first_name: str = None, last_name: str = None, username: str = None)-> Bot:
    """
    Adds users to the database. An user is either a channel owner or channel admin; normal Telegram users are not
    Stored.
    :param user_id: Telegram's user ID
    :param first_name: Telegram user's First Name
    :param last_name: Telegram user's Last Name
    :param username: Telegram user's username
    :return: [User] instance from the database
    """

    try:
        user = User.objects.get({'userId': user_id})
        if user.is_deleted:
            User.objects.raw({'userId': user_id}).update({'$set': {'isDeleted': False}, '$unset': {'deletedDate': ''}})
            return edit_user_info(user_id, first_name=first_name, last_name=last_name, username=username)
        else:
            raise UserAlreadyAdded('User is already added.')

    except User.DoesNotExist:
        join_time = datetime.datetime.utcnow()
        user = User(
            _id=user_id,
            uid=user_id,
            join_date=join_time
        )
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if username is not None:
            user.username = username
        if user.is_valid():
            user.save(full_clean=True)
            return user
        else:
            raise user.full_clean()


def add_bot(bot_id: int, bot_token: str, *, bot_name: str = '', username: str = None)-> User:
    """
    Adds bots to the database. An user is either a channel owner or channel admin; normal Telegram users are not
    Stored.
    :param bot_id: Telegram's bot ID
    :param bot_token: Telegram's API access token
    :param bot_name: Telegram bot's name
    :param username: Telegram bot's username
    :return: [Bot] instance from the database
    """

    try:
        bot = Bot.objects.get({'$or': [{'botId': bot_id}, {'botToken': bot_token}]})
        if bot.is_deleted:
            Bot.objects.raw({'$or': [{'botId': bot_id}, {'botToken': bot_token}]})\
                .update({'$set': {'isDeleted': False}, '$unset': {'deletedDate': ''}})
        return edit_bot_info(bot_id, bot_token, bot_name=bot_name, username=username)

    except Bot.DoesNotExist:
        join_time = datetime.datetime.utcnow()
        bot = User(
            _id=bot_id,
            bot_id=bot_id,
            join_date=join_time,
            name=bot_name
        )
        if username is not None:
            bot.username = username
        if bot.is_valid():
            bot.save(full_clean=True)
            return bot
        else:
            raise bot.full_clean()


def edit_user_info(user_id: int, *, first_name: str = None, last_name: str = None, username: str = None)-> User:
    """
    Helper to edit User Info in the database.
    :param user_id: Telegram's user ID
    :param first_name: Telegram user's First Name
    :param last_name: Telegram user's Last Name
    :param username: Telegram user's username
    :return: [User] updated instance from the database
    """

    try:
        user = User.objects.get({'userId': user_id})

        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if username is not None:
            user.username = username

        if user.is_valid():
            user.save(full_clean=True)
            return user
        else:
            raise user.full_clean()

    except User.DoesNotExist:
        return add_user(user_id=user_id, first_name=first_name, last_name=last_name, username=username)


def edit_bot_info(bot_id: int, bot_token: str, *, bot_name: str = None, username: str = None)-> Bot:
    """
    Helper to edit Bot Info in the database.
    :param bot_id: Telegram's bot ID
    :param bot_token: Telegram's API access token
    :param bot_name: Telegram bot's name
    :param username: Telegram bot's username
    :return: [Bot] updated instance from the database
    """

    try:
        bot = Bot.objects.get({'$or': [{'botId': bot_id}, {'botToken': bot_token}]})
        bot.bot_token = bot_token

        if bot_name is not None:
            bot.bot_name = bot_name
        if username is not None:
            bot.username = username

        if bot.is_valid():
            bot.save(full_clean=True)
            return bot
        else:
            raise bot.full_clean()

    except User.DoesNotExist:
        return add_bot(bot_id=bot_id, bot_token=bot_token, bot_name=bot_name, username=username)


def delete_user(user_model: User = None, user_id: int = None)-> bool:
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
            user.save(full_clean=True)
            data = {'$set': {'isDeleted': True, 'deletedDate': datetime.datetime.utcnow()}}
            all_posts = PostModel.objects.raw({'creator': user.uid})
            all_comments = Comment.objects.raw({'userId': user.uid})
            all_channels = Channel.objects.raw({'channelCreator': user.uid})
            all_admin_only_channels = Channel.objects.raw({'channelAdmins.uid': user.uid})

            all_posts.update(data)
            all_comments.update(data)
            all_channels.update(data)
            for channel_model in all_admin_only_channels:
                remove_admins(channel_model=channel_model, user_model=user)

            return True
        else:
            raise user.full_clean()

    except User.DoesNotExist:
        return False


def delete_bot(bot_model: Bot = None, bot_id: int = None, bot_token: str = None)-> bool:
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
        bot = bot_model if bot_model is not None else get_bots(bot_id=bot_id, bot_token=bot_token)
        bot.is_deleted = True
        bot.deleted_date = datetime.datetime.utcnow()

        if bot.is_valid():
            bot.save(full_clean=True)
            data = {'$set': {'channelBot': None}}
            all_posts = PostModel.objects.raw({'channelBot': bot.bot_id})
            all_channels = Channel.objects.raw({'channelBot': bot.bot_id})

            all_posts.update(data)
            all_channels.update(data)

            return True
        else:
            raise bot.full_clean()

    except User.DoesNotExist:
        return False


def get_users(user_id: int = None, user_ids: List[int] = None)-> Union[User, Iterable[User]]:
    """
    Gets a single user, or an iterable array of users from the database. Required either `user_id` or `user_ids`
    :param user_id: (Optional) the Telegram's ID of a given user
    :param user_ids: (Optional) a list of Telegram IDs of given users
    :return: a single [User] instance, an iterable of [User] instances, or None, if either the params are None, or there
             are no database matches.
    """

    try:
        if user_id is not None:
            user = User.objects.get({'userId': user_id, 'isDeleted': False})
            return user
        elif user_ids is not None:
            users = User.object.raw({'userId': {'$in': user_ids}, 'isDeleted': False})
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
        if bot_id is not None or bot_token is not None:
            bot = Bot.objects.get({'$or': [{'botId': bot_id}, {'botToken': bot_token}]})
            return bot
        elif bot_ids is not None or bot_tokens is not None:
            bots = Bot.object.raw({'$or': [{'botId': {'$in': bot_ids}}, {'botToken': {'$in': bot_tokens}}]})
            return bots
        else:
            raise User.DoesNotExist
    except Bot.DoesNotExist:
        raise
