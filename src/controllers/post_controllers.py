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

from ..models.post_models import ImagePost, TextPost, AnimationPost, AudioPost, LocationPost, VenuePost
from ..models.post_models import VideoPost, VoicePost, VideoNotePost, DocumentPost, PostModel
from ..models.post_models import Posts, Link, LinkList, GlobalPostAnalytics
from ..models.reactions_model import Reaction
from ..models.user_models import User
from ..models.channels_model import Channel
from ..models.comments_model import Comment
from .user_controllers import get_users
from .channel_controllers import get_channels
from typing import List, Union, Dict, Iterable
from ..utils.security import id_generator, hash_generator
from ..utils.function_handlers import to_async, temp_lru_cache
from .reaction_controllers import create_reaction
import datetime


__POST_CACHE = temp_lru_cache(max_size=8192)
__POST_GROUP_CACHE = temp_lru_cache(max_size=2048)


async def add_post_group(posts: List[PostModel],
                         user_model: User = None, user_id: int = None,
                         channel_model: Channel = None, channel_id: int = None)-> Posts:
    """
    Adds posts to a group.
    :param posts: Posts to be grouped
    :param user_model: Creator of the posts. Should be either it's model, or it's ID
    :param user_id: Creator of the posts. Should be either it's model, or it's ID
    :param channel_model: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param channel_id: Channel to where the posts belongs. Should be either it's model, or it's ID
    :return: [Posts] object containing a reference to all the posts in the group
    """
    try:
        post_strings = []
        _post_hash = ''
        for post in posts:
            post_strings.append(post.post_id)
            _post_hash += post.post_id

        posts_hash = hash_generator(_post_hash)

        creator = user_model if user_model is not None else await get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else await get_channels(channel_id=channel_id)

        _posts = Posts(
            _id=posts_hash,
            posts_hash=posts_hash,
            creator=creator,
            channel=channel,
            date_created=datetime.datetime.utcnow(),
            posts=post_strings
        )
        if _posts.is_valid():
            save = to_async(_posts.save)
            await save(full_clean=True)
            raw = to_async(PostModel.objects.raw)
            posts_group = await raw({'postId': {'$in': post_strings}})
            update = to_async(posts_group.update)
            await update({'$set': {'groupHash': posts_hash}})
            __POST_GROUP_CACHE[_posts.posts_hash] = _posts
            for post in posts:
                __POST_CACHE[post.post_id] = post
        else:
            raise _posts.full_clean()

        return _posts
    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


async def remove_post_group(group_model: Posts = None, group_hash: str = None)-> bool:
    """
    Remove a group of posts, the posts themselves, and any reactions / comments associated with this group.
    :param group_model: The model instance of the group posts in the database
    :param group_hash: The identifier of the group in the database. Only used if `group_model` is None
    :return: True if deleted, False if the group never existed, or the Exception raised by the data validation
             (less likely to happen).
    """
    try:
        posts_group = group_model if group_model is not None else await get_post_group(group_hash=group_hash)
        posts = await get_posts(post_ids=posts_group.posts)
        posts_group.is_deleted = True
        posts_group.deleted_date = datetime.datetime.utcnow()
        raw_comments = to_async(Comment.objects.raw)
        _comments = await raw_comments({'postReference': {'$in': posts_group.posts}})
        if posts_group.is_valid():
            data = {'$set': {'deletedDate': datetime.datetime.utcnow(), 'isDeleted': True}}
            update_comments = to_async(_comments.update)
            await update_comments(data)
            posts_update = to_async(posts.update)
            await posts_update(data)
            group_save = to_async(posts_group.save)
            await group_save(full_clean=True)
            del __POST_GROUP_CACHE[posts_group.posts_hash]
            for post in posts_group.posts:
                del __POST_GROUP_CACHE[post]
            return True
        else:
            raise posts_group.full_clean()
    except Posts.DoesNotExist:
        return False


async def get_post_group(group_hash: str)-> Posts:
    """
    Gets a model instance of a Post group
    :param group_hash: The identifier of the post group
    :return: A [Posts] instance
    """
    try:
        get = to_async(Posts.objects.get)
        post_group = __POST_GROUP_CACHE[group_hash]
        if post_group is None:
            post_group = await get({'groupHash': group_hash})
        return post_group
    except Posts.DoesNotExist:
        raise


async def add_text_post(user_model: User = None, user_id: int = None,
                        channel_model: Channel = None, channel_id: int = None, *,
                        message_id: int,
                        text: str,
                        tags: List[str] = None,
                        source: Link = None,
                        source_map: Dict[str, str] = None,
                        links: LinkList = None,
                        links_map: Union[Dict[str, List[Dict[str, str]]], Dict[str, int]] = None,
                        reactions: Reaction = None,
                        reactions_list: List[str] = None,
                        reactions_map: List[Union[Dict[str, str], Dict[str, int]]] = None) -> TextPost:
    """
    Adds a Text Post to the database.
    :param user_model: Creator of the posts. Should be either it's model, or it's ID
    :param user_id: Creator of the posts. Should be either it's model, or it's ID
    :param channel_model: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param channel_id: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param message_id: The Telegram's message ID to identify a message in a channel
    :param text: The text, in unicode format
    :param tags: The tags detected within the Post
    :param source: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param source_map: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param links: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param links_map: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param reactions: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a dict
                      mapping the emojis and an initial count
    :param reactions_list: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis,
                           or a dict mapping the emojis and an initial count
    :param reactions_map: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a
                          dict mapping the emojis and an initial count
    :return: [TextPost] object referencing the post saved on the database.
    """

    try:
        creator = user_model if user_model is not None else await get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else await get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)

        global_analytics.created_posts += 1
        global_analytics.save()

        _id = id_generator(16, global_analytics.created_posts)

        _source = None
        if source is not None:
            _source = source
        elif source_map is not None:
            _source = _create_link(source_map)

        _links = None
        if links is not None:
            _links = links
        elif links_map is not None:
            _links = _create_link_list(links_map)

        text_post = TextPost(
            _id=_id,
            post_id=_id,
            creator=creator,
            channel=channel,
            message_id=message_id,
            mime_type='text/plain',
            type='text',
            created_date=datetime.datetime.utcnow(),
            text=text
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = create_reaction(  # text_post,
                                         reactions_list=reactions_list, reactions_map=reactions_map)

        if _reactions is not None:
            text_post.reactions = _reactions
        if tags is not None:
            text_post.tags = tags
        if _source is not None:
            text_post.source = _source
        if _links is not None:
            text_post.links = _links

        if text_post.is_valid():
            save = to_async(text_post.save)
            await save(full_clean=True)
            global_analytics.added_posts += 1
            global_analytics.save()
            __POST_CACHE[text_post.post_id] = text_post
        else:
            raise text_post.full_clean()

        return text_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


async def add_image_post(user_model: User = None, user_id: int = None,
                         channel_model: Channel = None, channel_id: int = None, *,
                         message_id: int,
                         file_id: str,
                         file_size: int,
                         width: int,
                         height: int,
                         thumbnail_file_id: str = None,
                         thumbnail_size: int = None,
                         caption: str = None, tags: List[str] = None,
                         source: Link = None,
                         source_map: Dict[str, str] = None,
                         links: LinkList = None,
                         links_map: Union[Dict[str, List[Dict[str, str]]], Dict[str, int]] = None,
                         reactions: Reaction = None,
                         reactions_list: List[str] = None,
                         reactions_map: List[Union[Dict[str, str], Dict[str, int]]] = None) -> ImagePost:
    """
    Adds an Image Post to the database.
    :param user_model: Creator of the posts. Should be either it's model, or it's ID
    :param user_id: Creator of the posts. Should be either it's model, or it's ID
    :param channel_model: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param channel_id: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param message_id: The Telegram's message ID to identify a message in a channel
    :param file_id: The identifier of the file in Telegram's Database
    :param file_size: The size of the file
    :param width: The width of the file
    :param height: The height of the file
    :param thumbnail_file_id: (Optional) The identifier of the thumbnail in Telegram's Database
    :param thumbnail_size: (Optional) The size of the thumbnail
    :param caption: A caption is a small text, up to 1024 characters, that can be presented with the file
    :param tags: The tags detected within the Post
    :param source: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param source_map: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param links: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param links_map: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param reactions: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a dict
                      mapping the emojis and an initial count
    :param reactions_list: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis,
                           or a dict mapping the emojis and an initial count
    :param reactions_map: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a
                          dict mapping the emojis and an initial count
    :return: [ImagePost] object referencing the post saved on the database.
    """

    try:
        creator = user_model if user_model is not None else await get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else await get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)

        global_analytics.created_posts += 1
        global_analytics.save()

        _id = id_generator(16, global_analytics.created_posts)

        _source = None
        if source is not None:
            _source = source
        elif source_map is not None:
            _source = _create_link(source_map)

        _links = None
        if links is not None:
            _links = links
        elif links_map is not None:
            _links = _create_link_list(links_map)

        image_post = ImagePost(
            _id=_id,
            post_id=_id,
            creator=creator,
            channel=channel,
            message_id=message_id,
            mime_type='image/jpeg',
            type='image',
            created_date=datetime.datetime.utcnow(),
            file_id=file_id,
            file_size=file_size,
            width=width,
            height=height
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = create_reaction(  # image_post,
                                         reactions_list=reactions_list, reactions_map=reactions_map)

        if _reactions is not None:
            image_post.reactions = _reactions
        if tags is not None:
            image_post.tags = tags
        if _source is not None:
            image_post.source = _source
        if _links is not None:
            image_post.links = _links
        if caption is not None:
            image_post.caption = caption
        if thumbnail_file_id is not None:
            image_post.thumbnail_file_id = thumbnail_file_id
        if thumbnail_size is not None:
            image_post.thumbnail_size = thumbnail_size

        if image_post.is_valid():
            save = to_async(image_post.save)
            await save(full_clean=True)

            global_analytics.added_posts += 1
            global_analytics.save()
            __POST_CACHE[image_post.post_id] = image_post

        else:
            raise image_post.full_clean()

        return image_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


async def add_video_post(user_model: User = None, user_id: int = None,
                         channel_model: Channel = None, channel_id: int = None, *,
                         message_id: int,
                         file_id: str,
                         file_size: int,
                         width: int,
                         height: int,
                         duration: int,
                         mime_type: str = None,
                         thumbnail_file_id: str = None,
                         thumbnail_size: int = None,
                         caption: str = None, tags: List[str] = None,
                         source: Link = None,
                         source_map: Dict[str, str] = None,
                         links: LinkList = None,
                         links_map: Union[Dict[str, List[Dict[str, str]]], Dict[str, int]] = None,
                         reactions: Reaction = None,
                         reactions_list: List[str] = None,
                         reactions_map: List[Union[Dict[str, str], Dict[str, int]]] = None) -> VideoPost:
    """
    Adds a Video Post to the database.
    :param user_model: Creator of the posts. Should be either it's model, or it's ID
    :param user_id: Creator of the posts. Should be either it's model, or it's ID
    :param channel_model: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param channel_id: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param message_id: The Telegram's message ID to identify a message in a channel
    :param file_id: The identifier of the file in Telegram's Database
    :param file_size: The size of the file
    :param width: The width of the file
    :param height: The height of the file
    :param duration: The duration of the file
    :param mime_type: The mime type of the file. Defaults to 'video/mp4'
    :param thumbnail_file_id: (Optional) The identifier of the thumbnail in Telegram's Database
    :param thumbnail_size: (Optional) The size of the thumbnail
    :param caption: A caption is a small text, up to 1024 characters, that can be presented with the file
    :param tags: The tags detected within the Post
    :param source: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param source_map: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param links: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param links_map: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param reactions: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a dict
                      mapping the emojis and an initial count
    :param reactions_list: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis,
                           or a dict mapping the emojis and an initial count
    :param reactions_map: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a
                          dict mapping the emojis and an initial count
    :return: [VideoPost] object referencing the post saved on the database.
    """

    try:
        creator = user_model if user_model is not None else await get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else await get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)

        global_analytics.created_posts += 1
        global_analytics.save()

        _id = id_generator(16, global_analytics.created_posts)

        _source = None
        if source is not None:
            _source = source
        elif source_map is not None:
            _source = _create_link(source_map)

        _links = None
        if links is not None:
            _links = links
        elif links_map is not None:
            _links = _create_link_list(links_map)

        video_post = VideoPost(
            _id=_id,
            post_id=_id,
            creator=creator,
            channel=channel,
            message_id=message_id,
            mime_type=mime_type if mime_type is not None else 'video/mp4',
            type='video',
            created_date=datetime.datetime.utcnow(),
            file_id=file_id,
            file_size=file_size,
            duration=duration,
            width=width,
            height=height
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = create_reaction(  # video_post,
                                         reactions_list=reactions_list, reactions_map=reactions_map)

        if _reactions is not None:
            video_post.reactions = _reactions
        if tags is not None:
            video_post.tags = tags
        if _source is not None:
            video_post.source = _source
        if _links is not None:
            video_post.links = _links
        if caption is not None:
            video_post.caption = caption
        if thumbnail_file_id is not None:
            video_post.thumbnail_file_id = thumbnail_file_id
        if thumbnail_size is not None:
            video_post.thumbnail_size = thumbnail_size

        if video_post.is_valid():
            save = to_async(video_post.save)
            await save(full_clean=True)

            global_analytics.added_posts += 1
            global_analytics.save()
            __POST_CACHE[video_post.post_id] = video_post

        else:
            raise video_post.full_clean()

        return video_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


async def add_video_note_post(user_model: User = None, user_id: int = None,
                              channel_model: Channel = None, channel_id: int = None, *,
                              message_id: int,
                              file_id: str,
                              file_size: int,
                              length: int,
                              duration: int,
                              mime_type: str = None,
                              thumbnail_file_id: str = None,
                              thumbnail_size: int = None,
                              caption: str = None, tags: List[str] = None,
                              source: Link = None,
                              source_map: Dict[str, str] = None,
                              links: LinkList = None,
                              links_map: Union[Dict[str, List[Dict[str, str]]], Dict[str, int]] = None,
                              reactions: Reaction = None,
                              reactions_list: List[str] = None,
                              reactions_map: List[Union[Dict[str, str], Dict[str, int]]] = None) -> VideoNotePost:
    """
    Adds a VideoNote Post to the database.
    :param user_model: Creator of the posts. Should be either it's model, or it's ID
    :param user_id: Creator of the posts. Should be either it's model, or it's ID
    :param channel_model: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param channel_id: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param message_id: The Telegram's message ID to identify a message in a channel
    :param file_id: The identifier of the file in Telegram's Database
    :param file_size: The size of the file
    :param length: The file's width and height (diameter of the video message) as defined by sender
    :param duration: The duration of the file
    :param mime_type: The mime type of the file. Defaults to 'video/mp4'
    :param thumbnail_file_id: (Optional) The identifier of the thumbnail in Telegram's Database
    :param thumbnail_size: (Optional) The size of the thumbnail
    :param caption: A caption is a small text, up to 1024 characters, that can be presented with the file
    :param tags: The tags detected within the Post
    :param source: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param source_map: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param links: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param links_map: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param reactions: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a dict
                      mapping the emojis and an initial count
    :param reactions_list: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis,
                           or a dict mapping the emojis and an initial count
    :param reactions_map: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a
                          dict mapping the emojis and an initial count
    :return: [VideoNotePost] object referencing the post saved on the database.
    """

    try:
        creator = user_model if user_model is not None else await get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else await get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)

        global_analytics.created_posts += 1
        global_analytics.save()

        _id = id_generator(16, global_analytics.created_posts)

        _source = None
        if source is not None:
            _source = source
        elif source_map is not None:
            _source = _create_link(source_map)

        _links = None
        if links is not None:
            _links = links
        elif links_map is not None:
            _links = _create_link_list(links_map)

        video_note_post = VideoNotePost(
            _id=_id,
            post_id=_id,
            creator=creator,
            channel=channel,
            message_id=message_id,
            mime_type=mime_type if mime_type is not None else 'video/mp4',
            type='video_note',
            created_date=datetime.datetime.utcnow(),
            file_id=file_id,
            file_size=file_size,
            duration=duration,
            length=length
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = create_reaction(  # video_note_post,
                                         reactions_list=reactions_list, reactions_map=reactions_map)

        if _reactions is not None:
            video_note_post.reactions = _reactions
        if tags is not None:
            video_note_post.tags = tags
        if _source is not None:
            video_note_post.source = _source
        if _links is not None:
            video_note_post.links = _links
        if caption is not None:
            video_note_post.caption = caption
        if thumbnail_file_id is not None:
            video_note_post.thumbnail_file_id = thumbnail_file_id
        if thumbnail_size is not None:
            video_note_post.thumbnail_size = thumbnail_size

        if video_note_post.is_valid():
            save = to_async(video_note_post.save)
            await save(full_clean=True)

            global_analytics.added_posts += 1
            global_analytics.save()
            __POST_CACHE[video_note_post.post_id] = video_note_post

        else:
            raise video_note_post.full_clean()

        return video_note_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


async def add_animation_post(user_model: User = None, user_id: int = None,
                             channel_model: Channel = None, channel_id: int = None, *,
                             message_id: int,
                             file_id: str,
                             file_size: int,
                             width: int,
                             height: int,
                             duration: int,
                             file_name: str = None,
                             mime_type: str = None,
                             thumbnail_file_id: str = None,
                             thumbnail_size: int = None,
                             caption: str = None, tags: List[str] = None,
                             source: Link = None,
                             source_map: Dict[str, str] = None,
                             links: LinkList = None,
                             links_map: Union[Dict[str, List[Dict[str, str]]], Dict[str, int]] = None,
                             reactions: Reaction = None,
                             reactions_list: List[str] = None,
                             reactions_map: List[Union[Dict[str, str], Dict[str, int]]] = None) -> AnimationPost:
    """
    Adds an Animation Post to the database.
    :param user_model: Creator of the posts. Should be either it's model, or it's ID
    :param user_id: Creator of the posts. Should be either it's model, or it's ID
    :param channel_model: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param channel_id: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param message_id: The Telegram's message ID to identify a message in a channel
    :param file_id: The identifier of the file in Telegram's Database
    :param file_size: The size of the file
    :param width: The width of the file
    :param height: The height of the file
    :param duration: The duration of the file
    :param file_name: The name of the file, as defined by the sender.
    :param mime_type: The mime type of the file. Defaults to 'video/mp4'
    :param thumbnail_file_id: (Optional) The identifier of the thumbnail in Telegram's Database
    :param thumbnail_size: (Optional) The size of the thumbnail
    :param caption: A caption is a small text, up to 1024 characters, that can be presented with the file
    :param tags: The tags detected within the Post
    :param source: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param source_map: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param links: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param links_map: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param reactions: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a dict
                      mapping the emojis and an initial count
    :param reactions_list: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis,
                           or a dict mapping the emojis and an initial count
    :param reactions_map: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a
                          dict mapping the emojis and an initial count
    :return: [AnimationPost] object referencing the post saved on the database.
    """

    try:
        creator = user_model if user_model is not None else await get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else await get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)

        global_analytics.created_posts += 1
        global_analytics.save()

        _id = id_generator(16, global_analytics.created_posts)

        _source = None
        if source is not None:
            _source = source
        elif source_map is not None:
            _source = _create_link(source_map)

        _links = None
        if links is not None:
            _links = links
        elif links_map is not None:
            _links = _create_link_list(links_map)

        animation_post = AnimationPost(
            _id=_id,
            post_id=_id,
            creator=creator,
            channel=channel,
            message_id=message_id,
            mime_type=mime_type if mime_type is not None else 'video/mp4',
            type='animation',
            created_date=datetime.datetime.utcnow(),
            file_id=file_id,
            file_size=file_size,
            duration=duration,
            file_name=file_name,
            width=width,
            height=height
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = create_reaction(  # animation_post,
                                         reactions_list=reactions_list, reactions_map=reactions_map)

        if _reactions is not None:
            animation_post.reactions = _reactions
        if tags is not None:
            animation_post.tags = tags
        if _source is not None:
            animation_post.source = _source
        if _links is not None:
            animation_post.links = _links
        if caption is not None:
            animation_post.caption = caption
        if thumbnail_file_id is not None:
            animation_post.thumbnail_file_id = thumbnail_file_id
        if thumbnail_size is not None:
            animation_post.thumbnail_size = thumbnail_size

        if animation_post.is_valid():
            save = to_async(animation_post.save)
            await save(full_clean=True)

            global_analytics.added_posts += 1
            global_analytics.save()
            __POST_CACHE[animation_post.post_id] = animation_post

        else:
            raise animation_post.full_clean()

        return animation_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


async def add_voice_post(user_model: User = None, user_id: int = None,
                         channel_model: Channel = None, channel_id: int = None, *,
                         message_id: int,
                         file_id: str,
                         file_size: int,
                         duration: int,
                         mime_type: str = None,
                         caption: str = None, tags: List[str] = None,
                         source: Link = None,
                         source_map: Dict[str, str] = None,
                         links: LinkList = None,
                         links_map: Union[Dict[str, List[Dict[str, str]]], Dict[str, int]] = None,
                         reactions: Reaction = None,
                         reactions_list: List[str] = None,
                         reactions_map: List[Union[Dict[str, str], Dict[str, int]]] = None) -> VoicePost:
    """
    Adds a Voice Post to the database.
    :param user_model: Creator of the posts. Should be either it's model, or it's ID
    :param user_id: Creator of the posts. Should be either it's model, or it's ID
    :param channel_model: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param channel_id: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param message_id: The Telegram's message ID to identify a message in a channel
    :param file_id: The identifier of the file in Telegram's Database
    :param file_size: The size of the file
    :param duration: The duration of the file
    :param mime_type: The mime type of the file. Defaults to 'audio/ogg'
    :param caption: A caption is a small text, up to 1024 characters, that can be presented with the file
    :param tags: The tags detected within the Post
    :param source: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param source_map: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param links: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param links_map: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param reactions: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a dict
                      mapping the emojis and an initial count
    :param reactions_list: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis,
                           or a dict mapping the emojis and an initial count
    :param reactions_map: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a
                          dict mapping the emojis and an initial count
    :return: [VoicePost] object referencing the post saved on the database.
    """

    try:
        creator = user_model if user_model is not None else await get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else await get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)

        global_analytics.created_posts += 1
        global_analytics.save()

        _id = id_generator(16, global_analytics.created_posts)

        _source = None
        if source is not None:
            _source = source
        elif source_map is not None:
            _source = _create_link(source_map)

        _links = None
        if links is not None:
            _links = links
        elif links_map is not None:
            _links = _create_link_list(links_map)

        voice_post = VoicePost(
            _id=_id,
            post_id=_id,
            creator=creator,
            channel=channel,
            message_id=message_id,
            mime_type=mime_type if mime_type is not None else 'audio/ogg',
            type='voice',
            created_date=datetime.datetime.utcnow(),
            file_id=file_id,
            file_size=file_size,
            duration=duration
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = create_reaction(  # voice_post,
                                         reactions_list=reactions_list, reactions_map=reactions_map)

        if _reactions is not None:
            voice_post.reactions = _reactions
        if tags is not None:
            voice_post.tags = tags
        if _source is not None:
            voice_post.source = _source
        if _links is not None:
            voice_post.links = _links
        if caption is not None:
            voice_post.caption = caption

        if voice_post.is_valid():
            save = to_async(voice_post.save)
            await save(full_clean=True)

            global_analytics.added_posts += 1
            global_analytics.save()
            __POST_CACHE[voice_post.post_id] = voice_post

        else:
            raise voice_post.full_clean()

        return voice_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


async def add_audio_post(user_model: User = None, user_id: int = None,
                         channel_model: Channel = None, channel_id: int = None, *,
                         message_id: int,
                         file_id: str,
                         file_size: int,
                         duration: int,
                         performer: str = None,
                         title: str = None,
                         thumbnail_file_id: str = None,
                         thumbnail_size: str = None,
                         mime_type: str = None,
                         caption: str = None, tags: List[str] = None,
                         source: Link = None,
                         source_map: Dict[str, str] = None,
                         links: LinkList = None,
                         links_map: Union[Dict[str, List[Dict[str, str]]], Dict[str, int]] = None,
                         reactions: Reaction = None,
                         reactions_list: List[str] = None,
                         reactions_map: List[Union[Dict[str, str], Dict[str, int]]] = None) -> AudioPost:
    """
    Adds an Audio Post to the database.
    :param user_model: Creator of the posts. Should be either it's model, or it's ID
    :param user_id: Creator of the posts. Should be either it's model, or it's ID
    :param channel_model: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param channel_id: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param message_id: The Telegram's message ID to identify a message in a channel
    :param file_id: The identifier of the file in Telegram's Database
    :param file_size: The size of the file
    :param duration: The duration of the file
    :param performer: (Optional) The artist who made the song
    :param title: (Optional) The title of the song
    :param thumbnail_file_id: (Optional) The identifier of the thumbnail in Telegram's Database
    :param thumbnail_size: (Optional) The size of the thumbnail
    :param mime_type: The mime type of the file. Defaults to 'audio/mp3'
    :param caption: A caption is a small text, up to 1024 characters, that can be presented with the file
    :param tags: The tags detected within the Post
    :param source: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param source_map: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param links: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param links_map: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param reactions: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a dict
                      mapping the emojis and an initial count
    :param reactions_list: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis,
                           or a dict mapping the emojis and an initial count
    :param reactions_map: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a
                          dict mapping the emojis and an initial count
    :return: [AudioPost] object referencing the post saved on the database.
    """

    try:
        creator = user_model if user_model is not None else await get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else await get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)

        global_analytics.created_posts += 1
        global_analytics.save()

        _id = id_generator(16, global_analytics.created_posts)

        _source = None
        if source is not None:
            _source = source
        elif source_map is not None:
            _source = _create_link(source_map)

        _links = None
        if links is not None:
            _links = links
        elif links_map is not None:
            _links = _create_link_list(links_map)

        audio_post = AudioPost(
            _id=_id,
            post_id=_id,
            creator=creator,
            channel=channel,
            message_id=message_id,
            mime_type=mime_type if mime_type is not None else 'audio/mp3',
            type='audio',
            created_date=datetime.datetime.utcnow(),
            file_id=file_id,
            file_size=file_size,
            duration=duration,
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = create_reaction(  # audio_post,
                                         reactions_list=reactions_list, reactions_map=reactions_map)

        if _reactions is not None:
            audio_post.reactions = _reactions
        if tags is not None:
            audio_post.tags = tags
        if _source is not None:
            audio_post.source = _source
        if _links is not None:
            audio_post.links = _links
        if caption is not None:
            audio_post.caption = caption
        if performer is not None:
            audio_post.performer = performer
        if title is not None:
            audio_post.title = title
        if thumbnail_file_id is not None:
            audio_post.thumbnail_file_id = thumbnail_file_id
        if thumbnail_size is not None:
            audio_post.thumbnail_size = thumbnail_size

        if audio_post.is_valid():
            save = to_async(audio_post.save)
            await save(full_clean=True)

            global_analytics.added_posts += 1
            global_analytics.save()
            __POST_CACHE[audio_post.post_id] = audio_post

        else:
            raise audio_post.full_clean()

        return audio_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


async def add_file_post(user_model: User = None, user_id: int = None,
                        channel_model: Channel = None, channel_id: int = None, *,
                        message_id: int,
                        file_id: str,
                        file_size: int,
                        file_name: str = None,
                        mime_type: str = None,
                        thumbnail_file_id: str = None,
                        thumbnail_size: int = None,
                        caption: str = None, tags: List[str] = None,
                        source: Link = None,
                        source_map: Dict[str, str] = None,
                        links: LinkList = None,
                        links_map: Union[Dict[str, List[Dict[str, str]]], Dict[str, int]] = None,
                        reactions: Reaction = None,
                        reactions_list: List[str] = None,
                        reactions_map: List[Union[Dict[str, str], Dict[str, int]]] = None) -> DocumentPost:
    """
    Adds a Document Post to the database.
    :param user_model: Creator of the posts. Should be either it's model, or it's ID
    :param user_id: Creator of the posts. Should be either it's model, or it's ID
    :param channel_model: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param channel_id: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param message_id: The Telegram's message ID to identify a message in a channel
    :param file_id: The identifier of the file in Telegram's Database
    :param file_size: The size of the file
    :param file_name: The name of the file, as defined by the sender
    :param mime_type: The mime type of the file
    :param thumbnail_file_id: (Optional) The identifier of the thumbnail in Telegram's Database
    :param thumbnail_size: (Optional) The size of the thumbnail
    :param caption: A caption is a small text, up to 1024 characters, that can be presented with the file
    :param tags: The tags detected within the Post
    :param source: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param source_map: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param links: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param links_map: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param reactions: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a dict
                      mapping the emojis and an initial count
    :param reactions_list: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis,
                           or a dict mapping the emojis and an initial count
    :param reactions_map: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a
                          dict mapping the emojis and an initial count
    :return: [DocumentPost] object referencing the post saved on the database.
    """

    try:
        creator = user_model if user_model is not None else await get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else await get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)

        global_analytics.created_posts += 1
        global_analytics.save()

        _id = id_generator(16, global_analytics.created_posts)

        _source = None
        if source is not None:
            _source = source
        elif source_map is not None:
            _source = _create_link(source_map)

        _links = None
        if links is not None:
            _links = links
        elif links_map is not None:
            _links = _create_link_list(links_map)

        document_post = DocumentPost(
            _id=_id,
            post_id=_id,
            creator=creator,
            channel=channel,
            message_id=message_id,
            type='document',
            created_date=datetime.datetime.utcnow(),
            file_id=file_id,
            file_size=file_size,
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = create_reaction(  # document_post,
                                         reactions_list=reactions_list, reactions_map=reactions_map)

        if _reactions is not None:
            document_post.reactions = _reactions
        if tags is not None:
            document_post.tags = tags
        if _source is not None:
            document_post.source = _source
        if _links is not None:
            document_post.links = _links
        if caption is not None:
            document_post.caption = caption
        if mime_type is not None:
            document_post.mime_type = mime_type
        if file_name is not None:
            document_post.file_name = file_name
        if thumbnail_file_id is not None:
            document_post.thumbnail_file_id = thumbnail_file_id
        if thumbnail_size is not None:
            document_post.thumbnail_size = thumbnail_size

        if document_post.is_valid():
            save = to_async(document_post.save)
            await save(full_clean=True)

            global_analytics.added_posts += 1
            global_analytics.save()
            __POST_CACHE[document_post.post_id] = document_post

        else:
            raise document_post.full_clean()

        return document_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


async def add_location(user_model: User = None, user_id: int = None,
                       channel_model: Channel = None, channel_id: int = None, *,
                       message_id: int,
                       latitude: str,
                       longitude: int,
                       source: Link = None,
                       source_map: Dict[str, str] = None,
                       links: LinkList = None,
                       links_map: Union[Dict[str, List[Dict[str, str]]], Dict[str, int]] = None,
                       reactions: Reaction = None,
                       reactions_list: List[str] = None,
                       reactions_map: List[Union[Dict[str, str], Dict[str, int]]] = None) -> DocumentPost:
    """
    Adds a Location Post to the database.
    :param user_model: Creator of the posts. Should be either it's model, or it's ID
    :param user_id: Creator of the posts. Should be either it's model, or it's ID
    :param channel_model: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param channel_id: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param message_id: The Telegram's message ID to identify a message in a channel
    :param latitude: The latitude of the location
    :param longitude: The longitude of the location
    :param source: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param source_map: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param links: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param links_map: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param reactions: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a dict
                      mapping the emojis and an initial count
    :param reactions_list: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis,
                           or a dict mapping the emojis and an initial count
    :param reactions_map: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a
                          dict mapping the emojis and an initial count
    :return: [LocationPost] object referencing the post saved on the database.
    """

    try:
        creator = user_model if user_model is not None else await get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else await get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)

        global_analytics.created_posts += 1
        global_analytics.save()

        _id = id_generator(16, global_analytics.created_posts)

        _source = None
        if source is not None:
            _source = source
        elif source_map is not None:
            _source = _create_link(source_map)

        _links = None
        if links is not None:
            _links = links
        elif links_map is not None:
            _links = _create_link_list(links_map)

        location_post = LocationPost(
            _id=_id,
            post_id=_id,
            creator=creator,
            channel=channel,
            message_id=message_id,
            type='location',
            created_date=datetime.datetime.utcnow(),
            latitude=latitude,
            longitude=longitude,
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = create_reaction(  # document_post,
                                         reactions_list=reactions_list, reactions_map=reactions_map)

        if _reactions is not None:
            location_post.reactions = _reactions
        if _source is not None:
            location_post.source = _source
        if _links is not None:
            location_post.links = _links

        if location_post.is_valid():
            save = to_async(location_post.save)
            await save(full_clean=True)

            global_analytics.added_posts += 1
            global_analytics.save()
            __POST_CACHE[location_post.post_id] = location_post

        else:
            raise location_post.full_clean()

        return location_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


async def add_venue(user_model: User = None, user_id: int = None,
                    channel_model: Channel = None, channel_id: int = None, *,
                    message_id: int,
                    latitude: str,
                    longitude: int,
                    title: str,
                    address: str,
                    foursquare_id: str = None,
                    foursquare_type: str = None,
                    source: Link = None,
                    source_map: Dict[str, str] = None,
                    links: LinkList = None,
                    links_map: Union[Dict[str, List[Dict[str, str]]], Dict[str, int]] = None,
                    reactions: Reaction = None,
                    reactions_list: List[str] = None,
                    reactions_map: List[Union[Dict[str, str], Dict[str, int]]] = None) -> DocumentPost:
    """
    Adds a Location Post to the database.
    :param user_model: Creator of the posts. Should be either it's model, or it's ID
    :param user_id: Creator of the posts. Should be either it's model, or it's ID
    :param channel_model: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param channel_id: Channel to where the posts belongs. Should be either it's model, or it's ID
    :param message_id: The Telegram's message ID to identify a message in a channel
    :param latitude: The latitude of the location
    :param longitude: The longitude of the location
    :param title: Title of the Venue
    :param address: Address of the Venue
    :param foursquare_id: FourSquare Unique identifier of the Venue
    :param foursquare_type: FourSquare type of Venue (For example, “arts_entertainment/aquarium” or “food/icecream”)
    :param source: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param source_map: The source of the Post. This is either a [Link] object, or a dict that maps the data for a [Link]
    :param links: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param links_map: The links of the post. This is either a [LinkList] object, or a dict that maps the data for a
                  [LinkList]
    :param reactions: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a dict
                      mapping the emojis and an initial count
    :param reactions_list: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis,
                           or a dict mapping the emojis and an initial count
    :param reactions_map: The reactions of the post. This is either a [Reaction] object, a list of unicode emojis, or a
                          dict mapping the emojis and an initial count
    :return: [LocationPost] object referencing the post saved on the database.
    """

    try:
        creator = user_model if user_model is not None else await get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else await get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)

        global_analytics.created_posts += 1
        global_analytics.save()

        _id = id_generator(16, global_analytics.created_posts)

        _source = None
        if source is not None:
            _source = source
        elif source_map is not None:
            _source = _create_link(source_map)

        _links = None
        if links is not None:
            _links = links
        elif links_map is not None:
            _links = _create_link_list(links_map)

        venue_post = VenuePost(
            _id=_id,
            post_id=_id,
            creator=creator,
            channel=channel,
            message_id=message_id,
            type='location',
            created_date=datetime.datetime.utcnow(),
            latitude=latitude,
            longitude=longitude,
            title=title,
            address=address
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = create_reaction(  # document_post,
                                         reactions_list=reactions_list, reactions_map=reactions_map)

        if _reactions is not None:
            venue_post.reactions = _reactions
        if _source is not None:
            venue_post.source = _source
        if _links is not None:
            venue_post.links = _links
        if foursquare_id is not None:
            venue_post.foursquare_id = foursquare_id
        if foursquare_type is not None:
            venue_post.foursquare_type = foursquare_type

        if venue_post.is_valid():
            save = to_async(venue_post.save)
            await save(full_clean=True)

            global_analytics.added_posts += 1
            global_analytics.save()
            __POST_CACHE[venue_post.post_id] = venue_post

        else:
            raise venue_post.full_clean()

        return venue_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


async def remove_post(post_model: PostModel = None, post_id: str = None)-> bool:
    """
    Remove a post, and all it's associated comments from the database, by setting the deleted flag.
    :param post_model: The model instance of a post on the database
    :param post_id: The identifier of a post on the database. Used only if `post_model` is None
    :return: True if deleted, False if the post was never added, or the Exception raised by the data validation
             (less likely to happen).
    """
    try:
        post = post_model if post_model is not None else await get_posts(post_id=post_id)
        post.is_deleted = True
        post.deleted_date = datetime.datetime.utcnow()
        raw = to_async(Comment.objects.raw)
        _comments = await raw({'postReference': post.post_id})
        if post.is_valid():
            update = to_async(_comments.update)
            await update({'$set': {'deletedDate': datetime.datetime.utcnow(), 'isDeleted': True}})
            save = to_async(post.save)
            await save(full_clean=True)
            del __POST_CACHE[post.post_id]
            return True
        else:
            raise post.full_clean()
    except PostModel.DoesNotExist:
        return False


async def get_posts(post_id: str = None, post_ids: List[str] = None)-> Union[PostModel, Iterable[PostModel], None]:
    """
    Gets a single post, or an iterable array of posts from the database. Required either `post_id` or `post_ids`
    :param post_id: (Optional) The identifier of a post on the database
    :param post_ids: (Optional) A list of identifiers of posts in the database
    :return: a single [PostModel] instance, an iterable of [PostModel] instances, or None, if either the params are
             None, or there are no database matches.
    """
    try:
        get = to_async(PostModel.objects.get)
        raw = to_async(PostModel.objects.raw)
        if post_id is not None:
            posts = __POST_CACHE[post_id]
            if posts is None:
                posts = await get({'postId': post_id, 'isDeleted': False})
        elif post_ids is not None:
            posts = await raw({'postId': {'$in': post_ids}, 'isDeleted': False})
            for post in posts:
                __POST_CACHE[post.post_id] = post
        else:
            raise PostModel.DoesNotExist
        return posts
    except PostModel.DoesNotExist:
        raise


def _create_link(link_map: Dict[str, str]) -> Union[Link, None]:
    """
    Helper to create links
    :param link_map: The dict mapping a source label and url
    :return: [Link] Object of the link
    """
    link = None

    _label = link_map.get('label', None)
    _url = link_map.get('url', None)
    if _label is not None and _url is not None:
        link = Link(
            label=_label,
            url=_url
        )

    return link


def _create_link_list(links_map: Union[Dict[str, List[Dict[str, str]]], Dict[str, int]]) -> Union[LinkList, None]:
    """
    Helper to create a list of links
    :param links_map: Dict that contains a list of links, and how many links should be in a row
    :return: [LinkList] object of the link list
    """
    link_list = None

    listed_link_list = links_map.get('links', None)
    links_per_row = links_map.get('links_per_row', None)

    if listed_link_list is not None and links_per_row is not None:
        link_list = []
        for _link_map in listed_link_list:
            _link = _create_link(_link_map)
            if _link is not None:
                link_list.append(_link)

        return LinkList(
            links=link_list,
            links_per_row=links_per_row
        )

    return link_list
