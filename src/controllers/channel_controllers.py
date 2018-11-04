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
from ..models.post_models import PostModel, Posts
from ..models.channels_model import Channel, ChannelAdmin
from ..utils.function_handlers import to_async
from typing import List, Union, Iterable
from .user_controllers import get_users, get_bots
import datetime


class ChannelAlreadyAdded(BaseException):
    pass


async def add_channel(channel_id: int, user_id: int=None, user_model: User = None, *,
                      title: str = '', description: str = None, username: str = None,
                      private_link: str = None, photo_id: str = None) -> Union[Channel, bool]:
    """
    Adds a channel to the database. A channel can not be added if there is no owner for it.
    :param user_id: Telegram's ID of the channel owner. Only used if `user_model` is None
    :param user_model: [User] instance from the database
    :param channel_id: Telegram's ID of the channel itself
    :param title: A title of the channel, provided in Telegram
    :param description: A description of the channel, provided in Telegram
    :param username: An username (also used as public link) of the channel, provided in Telegram
    :param private_link: The private link (usually used to join) of the channel, provided by Telegram
    :param photo_id: The Telegram File ID identifier of the photo used as profile in the channel
    :return: [Channel] instance from the database
    """

    try:
        get = to_async(Channel.objects.get)
        _channel = await get({'channelId': channel_id})
        if _channel.is_deleted:
            Channel.objects.raw({'channelId'}).update({'$set': {'isDeleted': False}, '$unset': {'deletedDate': ''}})
            return await edit_channel_info(channel_id=channel_id, title=title, description=description,
                                           username=username, private_link=private_link, photo_id=photo_id)
        else:
            raise ChannelAlreadyAdded('Channel is already added.')
    except Channel.DoesNotExist:
        try:
            creator = user_model if user_model is not None else get_users(user_id=user_id)

            channel = Channel(
                _id=channel_id,
                chid=channel_id,
                title=title,
                creator=creator,
                added_date=datetime.datetime.utcnow()
            )

            if description is not None:
                channel.description = description
            if username is not None:
                channel.username = username
            if private_link is not None:
                channel.private_link = private_link
            if photo_id is not None:
                channel.photo_id = photo_id
            if channel.is_valid():
                save = to_async(channel.save)
                await save(full_clean=True)
            else:
                raise channel.full_clean()

            return channel

        except User.DoesNotExist:
            raise


async def add_admins(channel_model: Channel = None, channel_id: int = None, *,
                     user_model: User = None,  user_models: List[User] = None,
                     admin_model: ChannelAdmin = None, admin_models: List[ChannelAdmin] = None) -> bool:
    """
    Adds admins (secondary content creators) to a channel, and gives those authorization to handle certain things in
    the given channel.
    :param channel_model: Model instance of a channel in the database
    :param channel_id: Telegram's ID of the channel itself. Only used if `channel_model` is None
    :param user_model: A [User] instance to be added to the authorized admins.
    :param user_models: A list of [User] instances to be added to the authorized admins.
    :param admin_model: A [ChannelAdmin] instance to be added to the authorized admins.
    :param admin_models: A list of [ChannelAdmin] instances to be added to the authorized admins.
    :return: True if the admins were added, False if no admin was provided to add. Raises [DoesNotExist] in case the
             given channel doesn't exist.
    """

    try:
        channel = channel_model if channel_model is not None else await get_channels(channel_id=channel_id)
        _admins_to_add: List[ChannelAdmin] = []

        if user_model is not None:
            _new_admin = ChannelAdmin(
                uid=user_model,
                admin_since=datetime.datetime.utcnow()
            )
            _admins_to_add.append(_new_admin)

        elif user_models is not None:
            for _user in user_models:
                _new_admin = ChannelAdmin(
                    uid=_user,
                    admin_since=datetime.datetime.utcnow()
                )
                _admins_to_add.append(_new_admin)

        elif admin_model is not None:
            _admins_to_add.append(admin_model)

        elif admin_models is not None:
            _admins_to_add += admin_models

        if len(_admins_to_add) > 0:
            for _admin in _admins_to_add:
                if _admin not in channel.authorized_admins:
                    channel.authorized_admins.append(_admin)
        else:
            return False
        save = to_async(channel.save)
        await save(full_clean=True)
    except Channel.DoesNotExist:
        raise
    return True


async def remove_admins(channel_model: Channel = None, channel_id: int = None, *, user_model: User = None,
                        user_models: List[User] = None) -> bool:
    """
    Remove admins from the authorized admins from a given channel.
    :param channel_model: Model instance of a channel in the database
    :param channel_id: Telegram's ID of the channel itself. Only used if `channel_model` is None
    :param user_model: A [User] instance to be removed from the authorization list
    :param user_models: A list of [User] instances to be removed from the authorization list
    :return: True if the admins were removed, False if no [User] instance were given. Raises [DoesNotExist] in case the
             given channel doesn't exist.
    """

    try:
        channel = channel_model if channel_model is not None else await get_channels(channel_id=channel_id)

        if user_model is not None:
            for _admin in channel.authorized_admins:
                if _admin.uid == user_model.uid:
                    channel.authorized_admins.pop(_admin)
                    break

        elif user_models is not None:
            for _user in user_models:
                for _admin in channel.authorized_admins:
                    if _admin.uid == _user.uid:
                        channel.authorized_admins.pop(_admin)
                        break

        else:
            return False
        save = to_async(channel.save)
        await save()

        return True
    except Channel.DoesNotExist:
        raise


async def edit_channel_bot(user_model: User = None, user_id: int = None,
                           channel_model: Channel = None, channel_id: int = None, *,
                           bot_model: Bot = None, bot_id: int = None, bot_token: str = None)-> bool:
    """
    Edits the channel bot in said channel. Only the creator can do such operation.
    :param user_model: [User] instance of the owner from the database
    :param user_id: Telegram's ID of the channel owner. Only used if `user_model` is None
    :param channel_model: [Channel] instance of the channel from the database
    :param channel_id: Telegram's ID of the channel. Only used if `channel_model` is None
    :param bot_model: [Bot] instance of the bot to be added / replaced. Passing None means removing the bot from the
                      channel.
    :param bot_id: Telegram bot's ID. Only used if `bot_model` is None. Passing None means removing the bot from the
                   channel.
    :param bot_token: Telegram's API access token. Only used if `bot_model` is None.  Passing None means removing the
                      bot from the channel.
    :return: True if the addition / edition / deletion of the bot in the channel was successful. False if something
             happened, like the user isn't the creator. Raises `DoesNotExist` if either the user, the channel or the bot
             doesn't exist at all.
    """
    try:
        user = user_model if user_model is not None else await get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else await get_channels(channel_id=channel_id)

        if channel.creator == user.uid:
            if bot_model is None and bot_id is None and bot_token is None:
                Channel.objects.raw({'channelId': channel_id}).update({'$unset': {'channelBot': None}})
                return True
            else:
                bot = bot_model if bot_model is not None else await get_bots(bot_id=bot_id, bot_token=bot_token)
                channel.channel_bot = bot
                save = to_async(channel.save)
                await save()
                return True
        else:
            return False

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise
    except Bot.DoesNotExist:
        raise


async def edit_channel_info(channel_model: Channel = None, channel_id: int = None, *,
                            title: str = None, description: str = None,
                            username: str = None, private_link: str = None, photo_id: str = None)-> Channel:
    """
    Helper to edit a channel info in the database
    :param channel_model: Model instance of a channel in the database
    :param channel_id: Telegram's ID of the channel itself. Only used if `channel_model` is None
    :param title: A title of the channel, provided in Telegram
    :param description: A description of the channel, provided in Telegram
    :param username: An username (also used as public link) of the channel, provided in Telegram
    :param private_link: The private link (usually used to join) of the channel, provided by Telegram
    :param photo_id: The Telegram File ID identifier of the photo used as profile in the channel
    :return: [Channel] instance from the database
    """

    try:
        channel = channel_model if channel_model is not None else await get_channels(channel_id=channel_id)

        if title is not None:
            channel.title = title
        if description is not None:
            channel.description = description
        if username is not None:
            channel.username = username
        if private_link is not None:
            channel.private_link = private_link
        if photo_id is not None:
            channel.photo_id = photo_id

        if channel.is_valid():
            save = to_async(channel.save)
            await save(full_clean=True)
            return channel
        else:
            raise channel.full_clean()

    except Channel.DoesNotExist:
        raise


async def delete_channel(channel_model: Channel = None, channel_id: int = None)-> bool:
    """
    Delete a channel from the database, using it's Telegram's ID, by setting the deleted flag.
    :param channel_model: Model instance of a channel in the database
    :param channel_id: Telegram's ID of the channel itself. Only used if `channel_model` is None
    :return: True if deleted, False if channel has never been added,  or the Exception raised by the data validation
            (less likely to happen).
    """
    try:
        now = datetime.datetime.utcnow()
        channel = channel_model if channel_model is not None else await get_channels(channel_id=channel_id)
        channel.is_deleted = True
        channel.deleted_date = now

        if channel.is_valid():
            save = to_async(channel.save)
            posts_raw = to_async(PostModel.objects.raw)
            posts_clt_raw = to_async(Posts.objects.raw)
            posts_clt = await posts_clt_raw({'channelId': channel.chid})
            all_posts = await posts_raw({'channelId': channel.chid})
            posts_update = to_async(all_posts.update)
            posts_clt_update = to_async(posts_clt.update)
            await posts_update({'isDeleted': True, 'deletedDate': now})
            await posts_clt_update({'isDeleted': True, 'deletedDate': now})
            await save(full_clean=True)
            return True
        else:
            raise channel.full_clean()

    except Channel.DoesNotExist:
        return False


async def get_channels(channel_id: int = None, channel_ids: List[int] = None)-> Union[Channel, Iterable[Channel]]:
    try:
        get = to_async(Channel.objects.get)
        raw = to_async(Channel.objects.raw)
        if channel_id is not None:
            channel = await get({'channelId': channel_id, 'isDeleted': False})
            return channel
        elif channel_ids is not None:
            channels = await raw({'channelId': {'$in': channel_id}, 'isDeleted': False})
            return channels
        else:
            raise Channel.DoesNotExist
    except Channel.DoesNotExist:
        raise
