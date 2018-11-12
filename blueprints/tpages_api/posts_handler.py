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

from quart import Blueprint, request, Response
from src.controllers import user_controllers, post_controllers, channel_controllers
from .api_utils import app_auth_required, json_content_type_required, error_response, request_limit, user_auth_required
from src.utils.json_handlers import api_request, api_response, SuperDict
from src.utils.markdown import Markdown
from typing import Union, Tuple
import traceback

posts_api = Blueprint('posts', __name__, static_folder='./static', static_url_path='/static/files',
                      template_folder='./templates', subdomain='api')


def validate_posts(posts_data: SuperDict)-> Union[bool, Tuple[bool, Tuple[int]]]:
    """
    Validates the list of posts. if there's one or more invalid post, the posts are not valid at all.
    :param posts_data: List of posts to be validated

    :return: True if valid, (False, (ind0, ind1, ...)) Tuple containing the false result and the invalid indexes of the
             `post_data`
    """
    is_valid = True
    invalid_indexes = []
    if posts_data.creator is None or not isinstance(posts_data.creator, int) or posts_data.channel is None \
            or not isinstance(posts_data.channel, int) or posts_data.posts is None:
        return False, tuple(range(len(posts_data.posts))) if posts_data.posts is not None else 0
    for index in range(len(posts_data.posts)):
        post = posts_data.posts[index]
        if not isinstance(post, SuperDict):
            is_valid = False
            invalid_indexes.append(index)
            continue

        if post.message_id is None or post.type is None or not isinstance(post.message_id, int) \
                or not isinstance(post.type, str):
            is_valid = False
            invalid_indexes.append(index)
            continue

        if post.type == 'text':
            if post.text is None:
                is_valid = False
                invalid_indexes.append(index)
                continue
            try:
                post.text = Markdown.parser(post.text)
            except KeyError:
                is_valid = False
                invalid_indexes.append(index)
                continue
        elif post.type == 'image':
            if post.image is None or post.image.file_id is None or post.image.file_size is None \
                    or post.image.width is None or post.image.height is None:
                is_valid = False
                invalid_indexes.append(index)
                continue
            if post.image.caption is not None:
                try:
                    post.image.caption = Markdown.parser(post.image.caption)
                except KeyError:
                    is_valid = False
                    invalid_indexes.append(index)
                    continue
        elif post.type == 'video':
            if post.video is None or post.video.file_id is None or post.video.file_size is None \
                    or post.video.width is None or post.video.height is None or post.video.duration is None:
                is_valid = False
                invalid_indexes.append(index)
                continue
            if post.video.caption is not None:
                try:
                    post.video.caption = Markdown.parser(post.video.caption)
                except KeyError:
                    is_valid = False
                    invalid_indexes.append(index)
                    continue
        elif post.type == 'animation':
            if post.animation is None or post.animation.file_id is None or post.animation.file_size is None \
                    or post.animation.width is None or post.animation.height is None or post.animation.duration is None:
                is_valid = False
                invalid_indexes.append(index)
                continue
            if post.animation.caption is not None:
                try:
                    post.animation.caption = Markdown.parser(post.animation.caption)
                except KeyError:
                    is_valid = False
                    invalid_indexes.append(index)
                    continue
        elif post.type == 'video_note':
            if post.video_note is None or post.video_note.file_id is None or post.video_note.file_size is None \
                    or post.video_note.length or post.video_note.duration is None:
                is_valid = False
                invalid_indexes.append(index)
                continue
            if post.video_note.caption is not None:
                try:
                    post.video_note.caption = Markdown.parser(post.video_note.caption)
                except KeyError:
                    is_valid = False
                    invalid_indexes.append(index)
                    continue
        elif post.type == 'voice':
            if post.voice is None or post.voice.file_id is None or post.voice.file_size is None \
                    or post.voice.duration is None:
                is_valid = False
                invalid_indexes.append(index)
                continue
            if post.voice.caption is not None:
                try:
                    post.voice.caption = Markdown.parser(post.voice.caption)
                except KeyError:
                    is_valid = False
                    invalid_indexes.append(index)
                    continue
        elif post.type == 'audio':
            if post.audio is None or post.audio.file_id is None or post.audio.file_size is None \
                    or post.audio.duration is None:
                is_valid = False
                invalid_indexes.append(index)
                continue
            if post.audio.caption is not None:
                try:
                    post.audio.caption = Markdown.parser(post.audio.caption)
                except KeyError:
                    is_valid = False
                    invalid_indexes.append(index)
                    continue
        elif post.type == 'document':
            if post.document is None or post.document.file_id is None or post.document.file_size is None \
                    or post.document.file_name is None:
                is_valid = False
                invalid_indexes.append(index)
                continue
            if post.document.caption is not None:
                try:
                    post.document.caption = Markdown.parser(post.document.caption)
                except KeyError:
                    is_valid = False
                    invalid_indexes.append(index)
                    continue
        elif post.type == 'location':
            if post.location is None or post.location.latitude is None or post.location.longitude is None:
                is_valid = False
                invalid_indexes.append(index)
                continue
        elif post.type == 'venue':
            if post.venue is None or post.venue.latitude is None or post.venue.longitude is None \
                    or post.venue.title is None or post.venue.address is None:
                is_valid = False
                invalid_indexes.append(index)
                continue
        else:
            is_valid = False
            invalid_indexes.append(index)
            continue

    if is_valid:
        return True
    else:
        return False, tuple(invalid_indexes)


@posts_api.route('posts/add/', methods=('POST', ))
@app_auth_required
@json_content_type_required
@user_auth_required
@request_limit(max_requests=30, 60)
async def add_posts()-> Response:
    """
    Adds the posts on the database.

    The JSON format to be passed by the call is at it follows:
    {
        "creator": int,
        "channel": int,
        "posts": [
            {
                "mime_type": str,
                "type": str,
                "tags": List[str],
                "source": {
                    "label": str,
                    "url": str
                },
                "links": {
                    "links": [
                        {
                            "label": str,
                            "url": str,
                        },
                        {
                            "label": str,
                            "url": str,
                        },
                        ...
                    ],
                    "links_per_row": int(1-4)
                },
                "reactions": List[str],
                PostType: PostData
            },
            {
                "mime_type": str,
                "type": str,
                "tags": List[str],
                "source": {
                    "label": str,
                    "url": str
                },
                "links": {
                    "links": [
                        {
                            "label": str,
                            "url": str,
                        },
                        {
                            "label": str,
                            "url": str,
                        },
                        ...
                    ],
                    "links_per_row": int(1-4)
                },
                "reactions": List[str],
                PostType: PostData
            },
            ...
        ]
    }

    The Post types and their respective data is as it follows:
    "text": str,
    "image": {
        "file_id": str,
        "file_size": int,
        "width": int,
        "height": int,
        "thumbnail": {
            "file_id": str,
            "file_size": int
        },
        "caption": str
    },
    "video": {
        "file_id": str,
        "file_size": int,
        "width": int,
        "height": int,
        "duration": int,
        "thumbnail": {
            "file_id": str,
            "file_size": int
        },
        "caption": str
    },
    "video_note": {
        "file_id": str,
        "file_size": int,
        "length": int,
        "duration": int,
        "thumbnail": {
            "file_id": str,
            "file_size": int
        },
        "caption": str
    },
    "animation": {
        "file_id": str,
        "file_size": int,
        "width": int,
        "height": int,
        "duration": int,
        "file_name": str,
        "thumbnail": {
            "file_id": str,
            "file_size": int
        },
        "caption": str
    },
    "voice": {
        "file_id": str,
        "file_size": int,
        "duration": int,
        "caption": str
    },
    "audio": {
        "file_id": str,
        "file_size": int,
        "duration": int,
        "title": str,
        "performer": str,
        "thumbnail": {
            "file_id": str,
            "file_size": int
        },
        "caption": str
    },
    "document": {
        "file_id": str,
        "file_size": int,
        "file_name": str,
        "thumbnail": {
            "file_id": str,
            "file_size": int
        },
        "caption": str
    },
    "location": {
        "latitude": float,
        "longitude": float
    },
    "venue": {
        "location": {
            "latitude": float,
            "longitude": float,
        },
        "title": str,
        "address": str,
        "foursquare_id": str,
        "foursquare_type": str
    }
    :return: JSON serialized Response

             Possible Responses:
             201 - OK, with response:
             {
                 "success": True,
                 "op": "add_posts",
                 "msg": "Posts successfully added."
                 "qty": numberOfAdditions int,
                 "group_hash": str(the hash of all post IDs inserted),
                 "posts": List[str]
             }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "add_posts",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "add_posts",
                 "msg": "{reason}"
             }

             403 - Forbidden:
             {
                "success": False,
                "op": "add_posts",
                "msg": "User not authorized to post in this channel."
             }

             404 - Not Found:
             {
                "success": False,
                "op": "add_posts",
                "msg": "{reason}"
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "add_posts",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    data = await api_request(await request.data)

    # noinspection PyBroadException
    try:
        valid_data = validate_posts(data)
        if valid_data:
            posts = []
            creator = await user_controllers.get_users(user_id=data.creator)
            channel = await channel_controllers.get_channels(channel_id=data.channel)

            # If the user identifier header is different from the creator identifier, blocks the permission.
            uid = request.headers.get('User-Id', None)
            if int(uid) != int(creator.uid):
                return_data = await api_response(success=False, op=add_posts.__name__,
                                                 msg='User not authorized to post in this channel.',
                                                 error='#USER_CANT_PERFORM')
                return Response(return_data, status=403, mimetype='application/json',
                                content_type='application/json')

            if channel.creator != creator.uid:
                is_admin = False
                for admin in channel.authorized_admins:
                    if admin.uid == creator.uid:
                        is_admin = True
                        break
                if not is_admin:
                    return_data = await api_response(success=False, op=add_posts.__name__,
                                                     msg='User not authorized to post in this channel.',
                                                     error='#USER_CANT_PERFORM')
                    return Response(return_data, status=403, mimetype='application/json',
                                    content_type='application/json')
            for post in data.posts:
                ap = None

                if post.type == 'text':
                    ap = await post_controllers.add_text_post(user_model=creator, channel_model=channel,
                                                              message_id=post.message_id, text=post.text,
                                                              tags=post.tags, source_map=post.source,
                                                              links_map=post.links, reactions_list=post.reactions)
                if post.type == 'image':
                    if post.image.thumbnail is not None:
                        thumb_id = post.image.thumbnail.file_id
                        thumb_size = post.image.thumbnail.file_size
                    else:
                        thumb_id = None
                        thumb_size = None
                    ap = await post_controllers.add_image_post(user_model=creator, channel_model=channel,
                                                               message_id=post.message_id, file_id=post.image.file_id,
                                                               file_size=post.image.file_size,
                                                               width=post.image.width, height=post.image.height,
                                                               thumbnail_file_id=thumb_id, thumbnail_size=thumb_size,
                                                               caption=post.image.caption, tags=post.tags,
                                                               source_map=post.source, links_map=post.links,
                                                               reactions_list=post.reactions)
                if post.type == 'video':
                    if post.video.thumbnail is not None:
                        thumb_id = post.image.thumbnail.file_id
                        thumb_size = post.image.thumbnail.file_size
                    else:
                        thumb_id = None
                        thumb_size = None
                    ap = await post_controllers.add_video_post(user_model=creator, channel_model=channel,
                                                               message_id=post.message_id, file_id=post.video.file_id,
                                                               file_size=post.video.file_size, width=post.video.width,
                                                               height=post.video.height, duration=post.video.duration,
                                                               mime_type=post.mime_type, thumbnail_file_id=thumb_id,
                                                               thumbnail_size=thumb_size, caption=post.video.caption,
                                                               tags=post.tags, source_map=post.source,
                                                               links_map=post.links, reactions_list=post.reactions)
                if post.type == 'animation':
                    if post.image.thumbnail is not None:
                        thumb_id = post.image.thumbnail.file_id
                        thumb_size = post.image.thumbnail.file_size
                    else:
                        thumb_id = None
                        thumb_size = None
                    ap = await post_controllers.add_animation_post(user_model=creator, channel_model=channel,
                                                                   message_id=post.message_id,
                                                                   file_id=post.animation.file_id,
                                                                   file_size=post.animation.file_size,
                                                                   width=post.animation.width,
                                                                   height=post.animation.height,
                                                                   duration=post.animation.duration,
                                                                   file_name=post.animation.file_name,
                                                                   mime_type=post.mime_type, thumbnail_file_id=thumb_id,
                                                                   thumbnail_size=thumb_size,
                                                                   caption=post.animation.caption, tags=post.tags,
                                                                   source_map=post.source, links_map=post.links,
                                                                   reactions_list=post.reactions)
                if post.type == 'video_note':
                    if post.image.thumbnail is not None:
                        thumb_id = post.image.thumbnail.file_id
                        thumb_size = post.image.thumbnail.file_size
                    else:
                        thumb_id = None
                        thumb_size = None
                    ap = await post_controllers.add_video_note_post(user_model=creator, channel_model=channel,
                                                                    message_id=post.message_id,
                                                                    file_id=post.video_note.file_id,
                                                                    file_size=post.video_note.file_size,
                                                                    length=post.video_note.length,
                                                                    duration=post.video_note.duration,
                                                                    mime_type=post.mime_type,
                                                                    thumbnail_file_id=thumb_id,
                                                                    thumbnail_size=thumb_size,
                                                                    caption=post.video_note.caption, tags=post.tags,
                                                                    source_map=post.source, links_map=post.links,
                                                                    reactions_list=post.reactions)
                if post.type == 'voice':
                    ap = await post_controllers.add_voice_post(user_model=creator, channel_model=channel,
                                                               message_id=post.message_id, file_id=post.voice.file_id,
                                                               file_size=post.voice.file_size,
                                                               duration=post.voice.duration, mime_type=post.mime_type,
                                                               caption=post.voice.caption, tags=post.tags,
                                                               source_map=post.source, links_map=post.links,
                                                               reactions_list=post.reactions)
                if post.type == 'audio':
                    if post.image.thumbnail is not None:
                        thumb_id = post.image.thumbnail.file_id
                        thumb_size = post.image.thumbnail.file_size
                    else:
                        thumb_id = None
                        thumb_size = None
                    ap = await post_controllers.add_audio_post(user_model=creator, channel_model=channel,
                                                               message_id=post.message_id, file_id=post.audio.file_id,
                                                               file_size=post.audio.file_size,
                                                               duration=post.audio.duration,
                                                               performer=post.audio.performer, title=post.audio.title,
                                                               thumbnail_file_id=thumb_id, thumbnail_size=thumb_size,
                                                               mime_type=post.mime_type, caption=post.caption,
                                                               tags=post.tags, source_map=post.source,
                                                               links_map=post.links, reactions_list=post.reactions)
                if post.type == 'document':
                    if post.image.thumbnail is not None:
                        thumb_id = post.image.thumbnail.file_id
                        thumb_size = post.image.thumbnail.file_size
                    else:
                        thumb_id = None
                        thumb_size = None
                    ap = await post_controllers.add_file_post(user_model=creator, channel_model=channel,
                                                              message_id=post.message_id, file_id=post.document.file_id,
                                                              file_size=post.document.file_size,
                                                              file_name=post.document.file_name,
                                                              mime_type=post.mime_type,
                                                              thumbnail_file_id=thumb_id, thumbnail_size=thumb_size,
                                                              caption=post.document.caption, tags=post.tags,
                                                              source_map=post.source, links_map=post.links,
                                                              reactions_list=post.reactions)
                if post.type == 'location':
                    ap = await post_controllers.add_location(user_model=creator, channel_model=channel,
                                                             message_id=post.message_id,
                                                             latitude=post.location.latitude,
                                                             longitude=post.location.longitude,
                                                             source_map=post.source, links_map=post.links,
                                                             reactions_list=post.reactions)
                if post.type == 'venue':
                    ap = await post_controllers.add_venue(user_model=creator, channel_model=channel,
                                                          message_id=post.message_id,
                                                          latitude=post.venue.location.latitude,
                                                          longitude=post.venue.location.longitude,
                                                          title=post.venue.title, address=post.venue.address,
                                                          foursquare_id=post.venue.foursquare_id,
                                                          foursquare_type=post.venue.foursquare_type,
                                                          source_map=post.source, links_map=post.links,
                                                          reactions_list=post.reactions)
                if ap is not None:
                    posts.append(ap)

            if len(posts) > 0:
                posts_group = await post_controllers.add_post_group(posts=posts, user_model=creator,
                                                                    channel_model=channel)
                posts_list = [i.dict for i in posts]
                return_data = await api_response(success=True, op=add_posts.__name__, msg='Posts successfully added.',
                                                 qty=len(posts), group_hash=posts_group.posts_hash, posts=posts_list)
                return Response(return_data, status=201, mimetype='application/json', content_type='application/json', )

        else:
            return_data = await api_response(success=False, op=add_posts.__name__,
                                             msg='Invalid posts.',
                                             invalid_indexes=valid_data[1],
                                             error='#MALFORMED_REQUEST')
            return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    except user_controllers.User.DoesNotExist:
        return_data = await api_response(success=True, op=add_posts.__name__, msg='Channel admin does not exist.',
                                         error='#USER_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except channel_controllers.Channel.DoesNotExist:
        return_data = await api_response(success=True, op=add_posts.__name__, msg='Channel does not exist.',
                                         error='#CHANNEL_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(add_posts.__name__, traceback.format_exc())


@posts_api.route('/posts/get/<str:post_id>/', methods=('GET',))
@posts_api.route('/posts/get/', methods=('GET',), defaults={'post_id': None})
@app_auth_required
@user_auth_required
@request_limit(100, 10)
async def get_post(post_id: str)-> Response:
    """
    Gets a post from the database
    :param post_id: The post unique identifier to retrieve from the database
    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "get_post",
                 "post": {
                    "creator": int,
                    "channel": int,
                    "mime_type": str,
                    "type": str,
                    "tags": List[str],
                    "source": {
                        "label": str,
                        "url": str
                    },
                    "links": {
                        "links": [
                            {
                                "label": str,
                                "url": str,
                            },
                            {
                                "label": str,
                                "url": str,
                            },
                            ...
                        ],
                        "links_per_row": int(1-4)
                    },
                    "reactions": List[str],
                    PostType: PostData
                 }
             }
            The Post types and their respective data is as it follows:
            "text": str,
            "image": {
                "file_id": str,
                "file_size": int,
                "width": int,
                "height": int,
                "thumbnail": {
                    "file_id": str,
                    "file_size": int
                },
                "caption": str
            },
            "video": {
                "file_id": str,
                "file_size": int,
                "width": int,
                "height": int,
                "duration": int,
                "thumbnail": {
                    "file_id": str,
                    "file_size": int
                },
                "caption": str
            },
            "video_note": {
                "file_id": str,
                "file_size": int,
                "length": int,
                "duration": int,
                "thumbnail": {
                    "file_id": str,
                    "file_size": int
                },
                "caption": str
            },
            "animation": {
                "file_id": str,
                "file_size": int,
                "width": int,
                "height": int,
                "duration": int,
                "file_name": str,
                "thumbnail": {
                    "file_id": str,
                    "file_size": int
                },
                "caption": str
            },
            "voice": {
                "file_id": str,
                "file_size": int,
                "duration": int,
                "caption": str
            },
            "audio": {
                "file_id": str,
                "file_size": int,
                "duration": int,
                "title": str,
                "performer": str,
                "thumbnail": {
                    "file_id": str,
                    "file_size": int
                },
                "caption": str
            },
            "document": {
                "file_id": str,
                "file_size": int,
                "file_name": str,
                "thumbnail": {
                    "file_id": str,
                    "file_size": int
                },
                "caption": str
            },
            "location": {
                "latitude": float,
                "longitude": float
            },
            "venue": {
                "location": {
                    "latitude": float,
                    "longitude": float,
                },
                "title": str,
                "address": str,
                "foursquare_id": str,
                "foursquare_type": str
            }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "get_post",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "get_post",
                 "msg": "{reason}"
             }

             404 - Not Found:
             {
                "success": False,
                "op": "get_post",
                "msg": "{reason}"
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "get_post",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    if post_id is None:
        return_data = await api_response(success=False, op=get_post.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )

    # noinspection PyBroadException
    try:
        post = await post_controllers.get_posts(post_id=str(post_id))
        data = post.dict
        return_data = await api_response(success=True, op=get_post.__name__, msg=None, post=data)
        return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )
    except post_controllers.PostModel.DoesNotExist:
        return_data = await api_response(success=False, op=get_post.__name__, msg="Post doesn't exist.",
                                         error='#POST_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(get_post.__name__, traceback.format_exc())


@posts_api.route('/posts/get_group/<str:group_hash>/', methods=('GET', ))
@posts_api.route('/posts/get_group/', methods=('GET',), defaults={'group_hash': None})
@app_auth_required
@user_auth_required
@request_limit(50, 10)
async def get_posts_group(group_hash: str)-> Response:
    """

    Gets a post from the database
    :param group_hash: The group unique identifier to retrieve from the database

    The request can also contain  additional arguments, `limit` and `skip`.
    |arg limit: Limits the quantity of posts to be retrieved. Defaults to 30, maximum is 100
    |arg skip: Skips n posts. Best used to limit a quantity of posts to be retrieved, and skip the first n posts.
               defaults to 0.

    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "get_posts_group",
                 "posts": [
                     {
                        "creator": int,
                        "channel": int,
                        "mime_type": str,
                        "type": str,
                        "tags": List[str],
                        "source": {
                            "label": str,
                            "url": str
                        },
                        "links": {
                            "links": [
                                {
                                    "label": str,
                                    "url": str,
                                },
                                {
                                    "label": str,
                                    "url": str,
                                },
                                ...
                            ],
                            "links_per_row": int(1-4)
                        },
                        "reactions": List[str],
                        PostType: PostData
                     },
                     {
                        "creator": int,
                        "channel": int,
                        "mime_type": str,
                        "type": str,
                        "tags": List[str],
                        "source": {
                            "label": str,
                            "url": str
                        },
                        "links": {
                            "links": [
                                {
                                    "label": str,
                                    "url": str,
                                },
                                {
                                    "label": str,
                                    "url": str,
                                },
                                ...
                            ],
                            "links_per_row": int(1-4)
                        },
                        "reactions": List[str],
                        PostType: PostData
                     },
                    ...
                 ]
             }
            The Post types and their respective data is as it follows:
            "text": str,
            "image": {
                "file_id": str,
                "file_size": int,
                "width": int,
                "height": int,
                "thumbnail": {
                    "file_id": str,
                    "file_size": int
                },
                "caption": str
            },
            "video": {
                "file_id": str,
                "file_size": int,
                "width": int,
                "height": int,
                "duration": int,
                "thumbnail": {
                    "file_id": str,
                    "file_size": int
                },
                "caption": str
            },
            "video_note": {
                "file_id": str,
                "file_size": int,
                "length": int,
                "duration": int,
                "thumbnail": {
                    "file_id": str,
                    "file_size": int
                },
                "caption": str
            },
            "animation": {
                "file_id": str,
                "file_size": int,
                "width": int,
                "height": int,
                "duration": int,
                "file_name": str,
                "thumbnail": {
                    "file_id": str,
                    "file_size": int
                },
                "caption": str
            },
            "voice": {
                "file_id": str,
                "file_size": int,
                "duration": int,
                "caption": str
            },
            "audio": {
                "file_id": str,
                "file_size": int,
                "duration": int,
                "title": str,
                "performer": str,
                "thumbnail": {
                    "file_id": str,
                    "file_size": int
                },
                "caption": str
            },
            "document": {
                "file_id": str,
                "file_size": int,
                "file_name": str,
                "thumbnail": {
                    "file_id": str,
                    "file_size": int
                },
                "caption": str
            },
            "location": {
                "latitude": float,
                "longitude": float
            },
            "venue": {
                "location": {
                    "latitude": float,
                    "longitude": float,
                },
                "title": str,
                "address": str,
                "foursquare_id": str,
                "foursquare_type": str
            }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "get_posts_group",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "get_posts_group",
                 "msg": "{reason}"
             }

             404 - Not Found:
             {
                "success": False,
                "op": "get_posts_group",
                "msg": "{reason}"
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "get_posts_group",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    if group_hash is None:
        return_data = await api_response(success=False, op=get_posts_group.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )

    # noinspection PyBroadException
    try:
        skip = request.args.get('skip', 0)
        limit = request.args.get('limit', 30)
        if limit > 100:
            limit = 100
        group = await post_controllers.get_post_group(group_hash=str(group_hash))
        posts = await post_controllers.get_posts(post_ids=group.posts)
        posts = posts.skip(skip).limit(limit)
        data = [i.dict for i in posts]
        if len(data) > 0:
            return_data = await api_response(success=True, op=get_posts_group.__name__, msg=None, posts=data,
                                             qty=len(data), skipped=skip)
            return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )
        else:
            await post_controllers.remove_post_group(group_model=group)
            raise post_controllers.Posts.DoesNotExist('')
    except post_controllers.Posts.DoesNotExist:
        return_data = await api_response(success=False, op=get_posts_group.__name__, msg="Post group doesn't exist.",
                                         error='#GROUP_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(get_posts_group.__name__, traceback.format_exc())


@posts_api.route('/posts/edit/<str:post_id>/', methods=('POST', 'PATCH',))
@posts_api.route('/posts/edit/', methods=('POST', 'PATCH',), defaults={'post_id': None})
@app_auth_required
@user_auth_required
@json_content_type_required
@request_limit(60, 30)
async def edit_post(post_id: str)-> Response:
    """
    Edits a post in the database
    :param post_id: The post unique identifier on the database

    The JSON format to be passed by the call is at it follows:
    {
        "mime_type": str,
        "tags": List[str],
        "source": {
            "label": str,
            "url": str
        },
        "links": {
            "links": [
                {
                    "label": str,
                    "url": str,
                },
                {
                    "label": str,
                    "url": str,
                },
                ...
            ],
            "links_per_row": int(1-4)
        },
        "reactions": List[str],
        PostType: PostData
    }

    The Post types and their respective data is as it follows:
    "text": str,
    "image": {
        "file_id": str,
        "file_size": int,
        "width": int,
        "height": int,
        "thumbnail": {
            "file_id": str,
            "file_size": int
        },
        "caption": str
    },
    "video": {
        "file_id": str,
        "file_size": int,
        "width": int,
        "height": int,
        "duration": int,
        "thumbnail": {
            "file_id": str,
            "file_size": int
        },
        "caption": str
    },
    "video_note": {
        "file_id": str,
        "file_size": int,
        "length": int,
        "duration": int,
        "thumbnail": {
            "file_id": str,
            "file_size": int
        },
        "caption": str
    },
    "animation": {
        "file_id": str,
        "file_size": int,
        "width": int,
        "height": int,
        "duration": int,
        "file_name": str,
        "thumbnail": {
            "file_id": str,
            "file_size": int
        },
        "caption": str
    },
    "voice": {
        "file_id": str,
        "file_size": int,
        "duration": int,
        "caption": str
    },
    "audio": {
        "file_id": str,
        "file_size": int,
        "duration": int,
        "title": str,
        "performer": str,
        "thumbnail": {
            "file_id": str,
            "file_size": int
        },
        "caption": str
    },
    "document": {
        "file_id": str,
        "file_size": int,
        "file_name": str,
        "thumbnail": {
            "file_id": str,
            "file_size": int
        },
        "caption": str
    },
    "location": {
        "latitude": float,
        "longitude": float
    },
    "venue": {
        "location": {
            "latitude": float,
            "longitude": float,
        },
        "title": str,
        "address": str,
        "foursquare_id": str,
        "foursquare_type": str
    }
    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "edit_post",
                 "msg": "Post successfully edited."
             }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "edit_post",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "edit_post",
                 "msg": "{reason}"
             }

             403 - Forbidden:
             {
                "success": False,
                "op": "edit_post",
                "msg": "User not authorized to edit posts in this channel."
             }

             404 - Not Found:
             {
                "success": False,
                "op": "edit_post",
                "msg": "{reason}"
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "edit_post",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    if post_id is None:
        return_data = await api_response(success=False, op=edit_post.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )

    data = await api_request(await request.data)

    # noinspection PyBroadException
    try:
        post = await post_controllers.get_posts(post_id=post_id)
        channel = await channel_controllers.get_channels(channel_id=post.channel)

        to_validate = SuperDict({
            'creator': post.creator,
            'channel': channel.chid,
            'posts': [data]
        })
        valid_data = validate_posts(to_validate)
        if valid_data:
            # If the user identifier header is different from the creator identifier, blocks the permission.
            uid = request.headers.get('User-Id', None)
            if int(uid) != data.creator:
                is_admin = False
                admin_index = 0
                for admin in channel.authorized_admins:
                    if admin.uid == int(uid):
                        is_admin = True
                        break
                    admin_index += 1
                if not is_admin or not channel.authorized_admins[admin_index].can_edit_others:
                    return_data = await api_response(success=False, op=edit_post.__name__,
                                                     msg='User not authorized to edit posts in this channel.',
                                                     error='#USER_CANT_PERFORM')
                    return Response(return_data, status=403, mimetype='application/json',
                                    content_type='application/json')

            if data.mime_type is not None:
                post.mime_type = data.mime_type

            if data.tags is not None and isinstance(data.tags, list):
                post.tags = data.tags

            if data.source is not None and isinstance(data.source, SuperDict):
                # noinspection PyProtectedMember
                _source = post_controllers._create_link(data.source)
                post.source = _source

            if data.links is not None and isinstance(data.links, SuperDict):
                # noinspection PyProtectedMember
                _links = post_controllers._create_link_list(data.links)
                post.links = _links

            if data.reactions is not None and isinstance(data.reactions, list):
                _reactions = post_controllers.create_reaction(reactions_list=data.reactions)
                post.reactions = _reactions

            if isinstance(post, post_controllers.TextPost):
                post.text = data.text
            elif isinstance(post, post_controllers.ImagePost):
                if data.image.file_id is not None:
                    post.file_id = data.image.file_id
                    post.file_size = data.image.file_size
                    post.width = data.image.width
                    post.height = data.image.height
                if data.image.caption is not None:
                    post.caption = data.image.caption
                if data.image.thumbnail is not None:
                    if data.image.thumbnail.file_id is not None:
                        post.thumbnail_file_id = data.image.thumbnail.file_id
                    if data.image.thumbnail.file_size is not None:
                        post.thumbnail_size = data.image.thumbnail.file_size
            elif isinstance(post, post_controllers.VideoPost):
                if data.video.file_id is not None:
                    post.file_id = data.video.file_id
                    post.file_size = data.video.file_size
                    post.width = data.video.width
                    post.height = data.video.height
                    post.duration = data.video.duration
                if data.video.caption is not None:
                    post.caption = data.video.caption
                if data.video.thumbnail is not None:
                    if data.video.thumbnail.file_id is not None:
                        post.thumbnail_file_id = data.video.thumbnail.file_id
                    if data.video.thumbnail.file_size is not None:
                        post.thumbnail_size = data.video.thumbnail.file_size
            elif isinstance(post, post_controllers.VideoNotePost):
                if data.video_note.file_id is not None:
                    post.file_id = data.video_note.file_id
                    post.file_size = data.video_note.file_size
                    post.length = data.video_note.length
                    post.duration = data.video_note.duration
                if data.video_note.caption is not None:
                    post.caption = data.video.caption
                if data.video_note.thumbnail is not None:
                    if data.video_note.thumbnail.file_id is not None:
                        post.thumbnail_file_id = data.video_note.thumbnail.file_id
                    if data.video_note.thumbnail.file_size is not None:
                        post.thumbnail_size = data.video_note.thumbnail.file_size
            elif isinstance(post, post_controllers.AnimationPost):
                if data.animation.file_id is not None:
                    post.file_id = data.animation.file_id
                    post.file_size = data.animation.file_size
                    post.width = data.animation.width
                    post.height = data.animation.height
                    post.duration = data.animation.duration
                if data.animation.file_name is not None:
                    post.file_name = data.animation.file_name
                if data.animation.caption is not None:
                    post.caption = data.animation.caption
                if data.animation.thumbnail is not None:
                    if data.animation.thumbnail.file_id is not None:
                        post.thumbnail_file_id = data.animation.thumbnail.file_id
                    if data.animation.thumbnail.file_size is not None:
                        post.thumbnail_size = data.animation.thumbnail.file_size
            elif isinstance(post, post_controllers.DocumentPost):
                if data.file.file_id is not None:
                    post.file_id = data.file.file_id
                    post.file_size = data.file.file_size
                if data.file.file_name is not None:
                    post.file_name = data.file.file_name
                if data.file.caption is not None:
                    post.caption = data.file.caption
                if data.file.thumbnail is not None:
                    if data.file.thumbnail.file_id is not None:
                        post.thumbnail_file_id = data.file.thumbnail.file_id
                    if data.file.thumbnail.file_size is not None:
                        post.thumbnail_size = data.file.thumbnail.file_size
            elif isinstance(post, post_controllers.VoicePost):
                if data.voice.file_id is not None:
                    post.file_id = data.voice.file_id
                    post.file_size = data.voice.file_size
                    post.duration = data.voice.duration
                if data.file.caption is not None:
                    post.caption = data.file.caption
            elif isinstance(post, post_controllers.AudioPost):
                if data.audio.file_id is not None:
                    post.file_id = data.audio.file_id
                    post.file_size = data.audio.file_size
                if data.audio.title is not None:
                    post.title = data.audio.title
                if data.audio.performer is not None:
                    post.performer = data.audio.performer
                if data.audio.caption is not None:
                    post.caption = data.audio.caption
                if data.audio.thumbnail is not None:
                    if data.audio.thumbnail.file_id is not None:
                        post.thumbnail_file_id = data.audio.thumbnail.file_id
                    if data.audio.thumbnail.file_size is not None:
                        post.thumbnail_size = data.audio.thumbnail.file_size
            elif isinstance(post, post_controllers.LocationPost):
                if data.location.latitude is not None:
                    post.latitude = data.location.latitude
                if data.location.longitude is not None:
                    post.longitude = data.location.longitude
            elif isinstance(post, post_controllers.VenuePost):
                if data.venue.location is not None:
                    if data.venue.location.latitude is not None:
                        post.latitude = data.venue.location.latitude
                    if data.venue.location.longitude is not None:
                        post.longitude = data.venue.location.longitude
                if data.venue.title is not None:
                    post.title = data.venue.title
                if data.venue.address is not None:
                    post.address = data.venue.address
                if data.venue.foursquare_id is not None:
                    post.foursquare_id = data.venue.foursquare_id
                if data.venue.foursquare_type is not None:
                    post.foursquare_type = data.venue.foursquare_type

            post.save()

            return_data = await api_response(success=True, op=edit_post.__name__, msg='Post successfully edited.')
            return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )

        else:
            return_data = await api_response(success=False, op=edit_post.__name__,
                                             msg='Invalid post.',
                                             error='#MALFORMED_REQUEST')
            return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    except post_controllers.PostModel.DoesNotExist:
        return_data = await api_response(success=False, op=edit_post.__name__, msg="Post doesn't exist.",
                                         error='#POST_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(edit_post.__name__, traceback.format_exc())


@posts_api.route('/posts/delete/<str:post_id>/', methods=('DELETE',))
@posts_api.route('/posts/delete/', methods=('DELETE',), defaults={'post_id': None})
@app_auth_required
@user_auth_required
@request_limit(60, 30)
async def delete_post(post_id: str)-> Response:
    """
    Deletes a post in the database.
    :param post_id: The post unique identifier on the database
    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "delete_post",
                 "msg": "Post successfully deleted."
             }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "delete_post",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "delete_post",
                 "msg": "{reason}"
             }

             403 - Forbidden:
             {
                "success": False,
                "op": "delete_post",
                "msg": "User not authorized to delete posts in this channel."
             }

             404 - Not Found:
             {
                "success": False,
                "op": "delete_post",
                "msg": "{reason}"
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "delete_post",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    if post_id is None:
        return_data = await api_response(success=False, op=delete_post.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    # noinspection PyBroadException
    try:
        post = await post_controllers.get_posts(post_id=post_id)
        channel = await channel_controllers.get_channels(channel_id=post.channel)
        uid = request.headers.get('User-Id', None)
        if int(uid) != post.creator:
            is_admin = False
            admin_index = 0
            for admin in channel.authorized_admins:
                if admin.uid == int(uid):
                    is_admin = True
                    break
                admin_index += 1
            if not is_admin or not channel.authorized_admins[admin_index].can_delete_others:
                return_data = await api_response(success=False, op=delete_post.__name__,
                                                 msg='User not authorized to delete posts in this channel.',
                                                 error='#USER_CANT_PERFORM')
                return Response(return_data, status=403, mimetype='application/json',
                                content_type='application/json')

        deleted = await post_controllers.remove_post(post_model=post)
        if deleted:
            return_data = await api_response(success=True, op=delete_post.__name__, msg='Post successfully deleted.')
            return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )
        else:
            raise post_controllers.PostModel.DoesNotExist('')

    except post_controllers.PostModel.DoesNotExist:
        return_data = await api_response(success=False, op=delete_post.__name__, msg="Post doesn't exist.",
                                         error='#POST_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(delete_post.__name__, traceback.format_exc())


@posts_api.route('/posts/delete_group/<str:group_hash>/', methods=('DELETE', ))
@posts_api.route('/posts/delete_group/', methods=('DELETE', ), defaults={'group_hash': None})
@app_auth_required
@user_auth_required
@request_limit(60, 30)
async def delete_posts_group(group_hash: str)-> Response:
    """
    Deletes a post in the database.
    :param group_hash: The post group unique identifier on the database
    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "delete_posts_group",
                 "msg": "All posts in the group successfully deleted."
             }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "delete_posts_group",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "delete_posts_group",
                 "msg": "{reason}"
             }

             403 - Forbidden:
             {
                "success": False,
                "op": "delete_posts_group",
                "msg": "User not authorized to delete posts in this channel."
             }

             404 - Not Found:
             {
                "success": False,
                "op": "delete_posts_group",
                "msg": "{reason}"
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "delete_posts_group",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    if group_hash is None:
        return_data = await api_response(success=False, op=delete_posts_group.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    # noinspection PyBroadException
    try:
        post_group = await post_controllers.get_post_group(group_hash=group_hash)
        channel = await channel_controllers.get_channels(channel_id=post_group.channel)

        uid = request.headers.get('User-Id', None)
        if int(uid) != post_group.creator:
            is_admin = False
            admin_index = 0
            for admin in channel.authorized_admins:
                if admin.uid == int(uid):
                    is_admin = True
                    break
                admin_index += 1
            if not is_admin or not channel.authorized_admins[admin_index].can_delete_others:
                return_data = await api_response(success=False, op=delete_posts_group.__name__,
                                                 msg='User not authorized to delete posts in this channel.',
                                                 error='#USER_CANT_PERFORM')
                return Response(return_data, status=403, mimetype='application/json',
                                content_type='application/json')

        deleted = await post_controllers.remove_post_group(group_model=post_group)
        if deleted:
            return_data = await api_response(success=True, op=delete_post.__name__,
                                             msg='All posts in the group successfully deleted.')
            return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )
        else:
            raise post_controllers.Posts.DoesNotExist('')

    except post_controllers.Posts.DoesNotExist:
        return_data = await api_response(success=False, op=delete_post.__name__, msg="Post group doesn't exist.",
                                         error='#GROUP_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(delete_post.__name__, traceback.format_exc())
