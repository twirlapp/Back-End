from ..models.post_models import ImagePost, TextPost, AnimationPost, AudioPost
from ..models.post_models import VideoPost, VoicePost, VideoNotePost, DocumentPost, _PostModel
from ..models.post_models import Posts, Link, LinkList, GlobalPostAnalytics
from ..models.reactions_model import Reaction, ReactionObj
# from ..models.comments_model import Comment, CommentRank, CommentReply, UserGivenCommentRank
from ..models.user_model import User
from ..models.channels_model import Channel
from .user_controllers import get_users
from .channel_controllers import get_channels
from typing import List, Union, Dict
from ..utils.generator_utils import id_generator
# from pymodm.connection import _get_connection as get_connection
import datetime

# TODO: Methods to remove posts, methods to add and remove comments, add and remove reactions, add and remove ranks.


def add_posts(posts: List[_PostModel],
              user_model: User = None, user_id: int = None,
              channel_model: Channel = None, channel_id: int = None,
              )-> Posts:
    """

    :param posts:
    :param user_model:
    :param user_id:
    :param channel_model:
    :param channel_id:
    :return:
    """
    try:
        post_strings = []
        for post in posts:
            post_strings.append(post.post_id)

        creator = user_model if user_model is not None else get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else get_channels(channel_id=channel_id)

        _posts = Posts(
            creator=creator,
            channel=channel,
            date_created=datetime.datetime.now(),
            posts=post_strings
        )
        if _posts.is_valid():
            _posts.save(full_clean=True)
        else:
            raise _posts.full_clean()

        return _posts
    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


def add_text_post(user_model: User = None, user_id: int = None,
                  channel_model: Channel = None, channel_id: int = None, *,
                  text: str, tags: List[str] = None,
                  source: Link = None,
                  source_map: Dict[str, str] = None,
                  links: LinkList = None,
                  links_map: Union[Dict[str, List[Dict[str, str]]], Dict[str, int]] = None,
                  reactions: Reaction = None,
                  reactions_list: List[str] = None,
                  reactions_map: List[Union[Dict[str, str], Dict[str, int]]] = None) -> TextPost:
    """

    :param user_model:
    :param user_id:
    :param channel_model:
    :param channel_id:
    :param text:
    :param tags:
    :param source:
    :param source_map:
    :param links:
    :param links_map:
    :param reactions:
    :param reactions_list:
    :param reactions_map:
    :return:
    """

    try:
        creator = user_model if user_model is not None else get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)
            global_analytics.save()

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
            mime_type='text/plain',
            type='text',
            created_date=datetime.datetime.now(),
            tags=tags,
            source=_source,
            links=_links,
            text=text,
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = add_reaction(text_post, reactions_list=reactions_list, reactions_map=reactions_map)

        text_post.reactions = _reactions

        if text_post.is_valid():
            text_post.save(full_clean=True)
            if _reactions is not None:
                _reactions.save()

        else:
            raise text_post.full_clean()

        return text_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


def add_image_post(user_model: User = None, user_id: int = None,
                   channel_model: Channel = None, channel_id: int = None, *,
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

    :param user_model:
    :param user_id:
    :param channel_model:
    :param channel_id:
    :param file_id:
    :param file_size:
    :param width:
    :param height:
    :param thumbnail_file_id:
    :param thumbnail_size:
    :param caption:
    :param tags:
    :param source:
    :param source_map:
    :param links:
    :param links_map:
    :param reactions:
    :param reactions_list:
    :param reactions_map:
    :return:
    """

    try:
        creator = user_model if user_model is not None else get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)
            global_analytics.save()

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
            mime_type='image/jpeg',
            type='image',
            created_date=datetime.datetime.now(),
            tags=tags,
            source=_source,
            links=_links,
            caption=caption,
            file_id=file_id,
            file_size=file_size,
            width=width,
            height=height,
            thumbnail_file_id=thumbnail_file_id,
            thumbnail_size=thumbnail_size
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = add_reaction(image_post, reactions_list=reactions_list, reactions_map=reactions_map)

            image_post.reactions = _reactions

        if image_post.is_valid():
            image_post.save(full_clean=True)
            if _reactions is not None:
                _reactions.save()

        else:
            raise image_post.full_clean()

        return image_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


def add_video_post(user_model: User = None, user_id: int = None,
                   channel_model: Channel = None, channel_id: int = None, *,
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

    :param user_model:
    :param user_id:
    :param channel_model:
    :param channel_id:
    :param file_id:
    :param file_size:
    :param width:
    :param height:
    :param duration:
    :param mime_type:
    :param thumbnail_file_id:
    :param thumbnail_size:
    :param caption:
    :param tags:
    :param source:
    :param source_map:
    :param links:
    :param links_map:
    :param reactions:
    :param reactions_list:
    :param reactions_map:
    :return:
    """

    try:
        creator = user_model if user_model is not None else get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)
            global_analytics.save()

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
            mime_type=mime_type if mime_type is not None else 'video/mp4',
            type='video',
            created_date=datetime.datetime.now(),
            tags=tags,
            source=_source,
            links=_links,
            caption=caption,
            file_id=file_id,
            file_size=file_size,
            duration=duration,
            width=width,
            height=height,
            thumbnail_file_id=thumbnail_file_id,
            thumbnail_size=thumbnail_size
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = add_reaction(video_post, reactions_list=reactions_list, reactions_map=reactions_map)

            video_post.reactions = _reactions

        if video_post.is_valid():
            video_post.save(full_clean=True)
            if _reactions is not None:
                _reactions.save()

        else:
            raise video_post.full_clean()

        return video_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


def add_video_note_post(user_model: User = None, user_id: int = None,
                        channel_model: Channel = None, channel_id: int = None, *,
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

    :param user_model:
    :param user_id:
    :param channel_model:
    :param channel_id:
    :param file_id:
    :param file_size:
    :param length:
    :param duration:
    :param mime_type:
    :param thumbnail_file_id:
    :param thumbnail_size:
    :param caption:
    :param tags:
    :param source:
    :param source_map:
    :param links:
    :param links_map:
    :param reactions:
    :param reactions_list:
    :param reactions_map:
    :return:
    """

    try:
        creator = user_model if user_model is not None else get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)
            global_analytics.save()

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
            mime_type=mime_type if mime_type is not None else 'video/mp4',
            type='video',
            created_date=datetime.datetime.now(),
            tags=tags,
            source=_source,
            links=_links,
            caption=caption,
            file_id=file_id,
            file_size=file_size,
            duration=duration,
            length=length,
            thumbnail_file_id=thumbnail_file_id,
            thumbnail_size=thumbnail_size
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = add_reaction(video_note_post, reactions_list=reactions_list, reactions_map=reactions_map)

            video_note_post.reactions = _reactions

        if video_note_post.is_valid():
            video_note_post.save(full_clean=True)
            if _reactions is not None:
                _reactions.save()

        else:
            raise video_note_post.full_clean()

        return video_note_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


def add_animation_post(user_model: User = None, user_id: int = None,
                       channel_model: Channel = None, channel_id: int = None, *,
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

    :param user_model:
    :param user_id:
    :param channel_model:
    :param channel_id:
    :param file_id:
    :param file_size:
    :param width:
    :param height:
    :param duration:
    :param file_name:
    :param mime_type:
    :param thumbnail_file_id:
    :param thumbnail_size:
    :param caption:
    :param tags:
    :param source:
    :param source_map:
    :param links:
    :param links_map:
    :param reactions:
    :param reactions_list:
    :param reactions_map:
    :return:
    """

    try:
        creator = user_model if user_model is not None else get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)
            global_analytics.save()

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
            mime_type=mime_type if mime_type is not None else 'video/mp4',
            type='video',
            created_date=datetime.datetime.now(),
            tags=tags,
            source=_source,
            links=_links,
            caption=caption,
            file_id=file_id,
            file_size=file_size,
            duration=duration,
            file_name=file_name,
            width=width,
            height=height,
            thumbnail_file_id=thumbnail_file_id,
            thumbnail_size=thumbnail_size
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = add_reaction(animation_post, reactions_list=reactions_list, reactions_map=reactions_map)

            animation_post.reactions = _reactions

        if animation_post.is_valid():
            animation_post.save(full_clean=True)
            if _reactions is not None:
                _reactions.save()

        else:
            raise animation_post.full_clean()

        return animation_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


def add_voice_post(user_model: User = None, user_id: int = None,
                   channel_model: Channel = None, channel_id: int = None, *,
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

    :param user_model:
    :param user_id:
    :param channel_model:
    :param channel_id:
    :param file_id:
    :param file_size:
    :param duration:
    :param mime_type:
    :param caption:
    :param tags:
    :param source:
    :param source_map:
    :param links:
    :param links_map:
    :param reactions:
    :param reactions_list:
    :param reactions_map:
    :return:
    """

    try:
        creator = user_model if user_model is not None else get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)
            global_analytics.save()

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
            mime_type=mime_type if mime_type is not None else 'audio/ogg',
            type='voice',
            created_date=datetime.datetime.now(),
            tags=tags,
            source=_source,
            links=_links,
            caption=caption,
            file_id=file_id,
            file_size=file_size,
            duration=duration
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = add_reaction(voice_post, reactions_list=reactions_list, reactions_map=reactions_map)

            voice_post.reactions = _reactions

        if voice_post.is_valid():
            voice_post.save(full_clean=True)
            if _reactions is not None:
                _reactions.save()

        else:
            raise voice_post.full_clean()

        return voice_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


def add_audio_post(user_model: User = None, user_id: int = None,
                   channel_model: Channel = None, channel_id: int = None, *,
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

    :param user_model:
    :param user_id:
    :param channel_model:
    :param channel_id:
    :param file_id:
    :param file_size:
    :param duration:
    :param performer:
    :param title:
    :param thumbnail_file_id:
    :param thumbnail_size:
    :param mime_type:
    :param caption:
    :param tags:
    :param source:
    :param source_map:
    :param links:
    :param links_map:
    :param reactions:
    :param reactions_list:
    :param reactions_map:
    :return:
    """

    try:
        creator = user_model if user_model is not None else get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)
            global_analytics.save()

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
            mime_type=mime_type if mime_type is not None else 'audio/ogg',
            type='voice',
            created_date=datetime.datetime.now(),
            tags=tags,
            source=_source,
            links=_links,
            caption=caption,
            file_id=file_id,
            file_size=file_size,
            duration=duration,
            performer=performer,
            title=title,
            thumbnail_file_id=thumbnail_file_id,
            thumbnail_size=thumbnail_size
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = add_reaction(audio_post, reactions_list=reactions_list, reactions_map=reactions_map)

            audio_post.reactions = _reactions

        if audio_post.is_valid():
            audio_post.save(full_clean=True)
            if _reactions is not None:
                _reactions.save()

        else:
            raise audio_post.full_clean()

        return audio_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


def add_file_post(user_model: User = None, user_id: int = None,
                  channel_model: Channel = None, channel_id: int = None, *,
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

    :param user_model:
    :param user_id:
    :param channel_model:
    :param channel_id:
    :param file_id:
    :param file_size:
    :param file_name:
    :param mime_type:
    :param thumbnail_file_id:
    :param thumbnail_size:
    :param caption:
    :param tags:
    :param source:
    :param source_map:
    :param links:
    :param links_map:
    :param reactions:
    :param reactions_list:
    :param reactions_map:
    :return:
    """

    try:
        creator = user_model if user_model is not None else get_users(user_id=user_id)
        channel = channel_model if channel_model is not None else get_channels(channel_id=channel_id)

        try:
            global_analytics = GlobalPostAnalytics.objects.get({'_id': 0})
        except GlobalPostAnalytics.DoesNotExist:
            global_analytics = GlobalPostAnalytics(_id=0, created_posts=0)
            global_analytics.save()

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
            mime_type=mime_type if mime_type is not None else 'video/mp4',
            type='video',
            created_date=datetime.datetime.now(),
            tags=tags,
            source=_source,
            links=_links,
            caption=caption,
            file_id=file_id,
            file_size=file_size,
            file_name=file_name,
            thumbnail_file_id=thumbnail_file_id,
            thumbnail_size=thumbnail_size
        )

        _reactions = None
        if reactions is not None:
            _reactions = reactions
        elif reactions_list is not None or reactions_map is not None:
            _reactions = add_reaction(document_post, reactions_list=reactions_list, reactions_map=reactions_map)

            document_post.reactions = _reactions

        if document_post.is_valid():
            document_post.save(full_clean=True)
            if _reactions is not None:
                _reactions.save()

        else:
            raise document_post.full_clean()

        return document_post

    except User.DoesNotExist:
        raise
    except Channel.DoesNotExist:
        raise


def add_reaction(post: _PostModel,
                 reactions_list: List[str] = None,
                 reactions_map: List[Union[Dict[str, str], Dict[str, int]]] = None) -> Reaction:
    """

    :param post:
    :param reactions_list:
    :param reactions_map:
    :return:
    """
    _reactions = None
    if reactions_list is not None:
        _reactions = []
        for emoji in reactions_list:
            _reaction_obj = ReactionObj(
                emoji=emoji,
                count=0
            )
            _reactions.append(_reaction_obj)
    elif reactions_map is not None:
        _reactions = []
        for _reaction_dict in reactions_map:
            emoji = _reaction_dict.get('emoji', None)
            count = _reaction_dict.get('count', 0)
            if emoji is not None:
                _reaction_obj = ReactionObj(
                    emoji=emoji,
                    count=count
                )
                _reactions.append(_reaction_obj)

    if _reactions is not None:
        _id = post.post_id + id_generator(4, use_hex=True)
        reaction_obj = Reaction(
            _id=_id,
            reaction_id=_id,
            post=post,
            created_date=datetime.datetime.now(),
            total_count=0
        )
        return reaction_obj


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
    row_num = links_map.get('row_num', None)

    if listed_link_list is not None and row_num is not None:
        link_list = []
        for _link_map in listed_link_list:
            _link = _create_link(_link_map)
            if _link is not None:
                link_list.append(_link)

        return LinkList(
            links=link_list,
            links_per_row=row_num
        )

    return link_list
