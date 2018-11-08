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
from src.controllers import channel_controllers, user_controllers
from .api_utils import app_auth_required, json_content_type_required, error_response, request_limit, user_auth_required
from src.utils.json_handlers import api_request, api_response, SuperDict
# from src.utils.security import hash_generator
import traceback
import bcrypt
# import config

channels_api = Blueprint('channels', __name__, static_folder='./static', static_url_path='/static/files',
                         template_folder='./templates', subdomain='api')


def verify_channel_data(request_data: SuperDict)-> bool:
    """
    Verifies the validity of a channel object to be added on the database.
    :param request_data:
    :return: True if valid, False otherwise
    """
    channel_id = request_data.channel_id
    title = request_data.title
    owner_info = request_data.owner_info

    valid = False

    if channel_id is not None and title is not None and isinstance(owner_info, SuperDict) and \
            owner_info.user_id is not None and owner_info.hash is not None:
        valid = True
    return valid


@channels_api.route('/channels/add/', methods=('POST',))
@app_auth_required
@json_content_type_required
@user_auth_required
async def add_channels()-> Response:
    """
    Adds channels to the application. A channel can belong only to one user, but can be administrated by multiple users.

    The JSON formats to be passed by the call is at it follows:
    {
        "channel_id": int,
        "title": str,
        "description": str,
        "username": str,
        "private_link": str,
        "owner_info": {
            "user_id": int,
            "hash": `sha256 of "user_id" + unicode password, case sensitive`
        },
        "profile_photo": str (Unique identifier of the photo),
    }

    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "add_channels",
                 "msg": "Channel successfully added."
             }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "add_channels",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "add_channels",
                 "msg": "Unauthorized Application"
             }

             403 - Forbidden
             {
                 "success": False,
                 "op": "add_channels",
                 "msg": "{reason}"
             }

             404 - Not Found (User)
             {
                "success": False,
                "op": "add_channels",
                "msg": "Channel Owner not registered."
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "add_channels",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    data = await api_request(await request.data)
    if not verify_channel_data(data):
        return_data = await api_response(success=False, op=add_channels.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )

    # noinspection PyBroadException
    try:
        user = await user_controllers.get_users(user_id=int(data.owner_info.user_id))
        if not bcrypt.checkpw(data.owner_info.hash.lower().encode(), user.user_secure):
            return_data = await api_response(False, op=add_channels.__name__, msg='User not Authenticated.',
                                             error='#USER_NOT_AUTHENTICATED')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

        await channel_controllers.add_channel(channel_id=int(data.channel_id), user_model=user, title=data.title,
                                              description=data.descrpition, username=data.username,
                                              private_link=data.private_link, photo_id=data.profile_photo)

        return_data = await api_response(success=True, op=add_channels.__name__, msg='Channel successfully added.')
        return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )

    except channel_controllers.ChannelAlreadyAdded:
            return_data = await api_response(False, op=add_channels.__name__, msg='Channel already added.',
                                             error='#CHANNEL_ALREADY_REGISTERED')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )
    except user_controllers.User.DoesNotExist:
        return_data = await api_response(False, op=add_channels.__name__, msg='Channel owner not registered.',
                                         error='#USER_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(add_channels.__name__, traceback.format_exc())


@channels_api.route('/channels/get/<int:channel_id>/', methods=('GET', ))
@channels_api.route('/channels/get/', methods=('GET',), defaults={'channel_id': None})
@app_auth_required
@json_content_type_required
@user_auth_required
@request_limit(max_requests=200)
async def get_channel(channel_id: int)-> Response:
    """
    Gets some basic info about a given channel
    :param channel_id: The channel unique identifier on the database.
    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "get_channel",
                 "channel": {
                            "channel_id": int,
                            "channel_title": str,
                            "username": str,
                            "profile_photo": str
                        }
             }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "get_channel",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "get_channel",
                 "msg": "Unauthorized Application"
             }

             403 - Forbidden
             {
                 "success": False,
                 "op": "get_channel",
                 "msg": "User not Authenticated."
             }

             404 - User not Found:
             {
                "success": False,
                "op": "get_channel",
                "msg": "Channel does not exist."
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "get_channel",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    if channel_id is None:
        return_data = await api_response(success=False, op=get_channel.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    # noinspection PyBroadException
    try:
        channel = await channel_controllers.get_channels(channel_id=int(channel_id))
        data = {
            'channel_id': channel.chid,
            'title': channel.title,
            'description': channel.description,
            'profile_photo': channel.photo_id
        }
        return_data = await api_response(success=True, op=get_channel.__name__, msg=None, channel=data)
        return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )
    except channel_controllers.Channel.DoesNotExist:
        return_data = await api_response(success=False, op=get_channel.__name__, msg="Channel does not exist.",
                                         error='#CHANNEL_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(get_channel.__name__, traceback.format_exc())


@channels_api.route('/channels/edit/<int:channel_id>/', methods=('POST', 'PATCH',))
@channels_api.route('/channels/edit/', methods=('POST', 'PATCH',), defaults={'channel_id': None})
@app_auth_required
@json_content_type_required
@user_auth_required
@request_limit(max_requests=20, ttl=60)
async def edit_channel(channel_id: int)-> Response:
    """
    Edits the channel info on the database.
    :param channel_id: The channel unique identifier

    The JSON formats to be passed by the call is at it follows:
    {
        "title": str,
        "description": str,
        "username": str,
        "private_link": str,
        "owner_info": {
            "user_id": int,
            "hash": `sha256 of "user_id" + unicode password, case sensitive`
        }
        "profile_photo": str (Unique identifier of the photo),
    }


    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "edit_channel",
                 "msg": "Channel successfully edited."
             }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "edit_channel",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "edit_channel",
                 "msg": "Unauthorized Application"
             }

             403 - Forbidden
             {
                 "success": False,
                 "op": "edit_channel",
                 "msg": "User not Authenticated."
             }

             404 - Channel not Found:
             {
                "success": False,
                "op": "edit_channel",
                "msg": "Channel does not exist."
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "edit_channel",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    data = await api_request(await request.data)
    data.channel_id = channel_id
    if not verify_channel_data(data):
        return_data = await api_response(success=False, op=edit_channel.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )

    # noinspection PyBroadException
    try:
        channel = await channel_controllers.get_channels(channel_id=int(data.channel_id))
        user = await user_controllers.get_users(user_id=int(data.user_info.user_id))

        if channel.creator != user.uid:
            can_edit = False
            for admin in channel.authorized_admins:
                if admin.uid == user.uid:
                    if admin.can_update_channel_info:
                        can_edit = True
                    break
            if not can_edit:
                return_data = await api_response(False, op=edit_channel.__name__,
                                                 msg='User not authorized to edit channel.',
                                                 error='#USER_CANT_PERFORM')
                return Response(return_data, status=403, mimetype='application/json', content_type='application/json')

        if not bcrypt.checkpw(data.owner_info.hash.lower().encode(), user.user_secure):
            return_data = await api_response(False, op=edit_channel.__name__, msg='User not Authenticated.',
                                             error='#USER_NOT_AUTHENTICATED')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

        await channel_controllers.edit_channel_info(channel_model=channel, title=data.title,
                                                    description=data.description, username=data.username,
                                                    private_link=data.private_link, photo_id=data.profile_photo)

        return_data = await api_response(success=True, op=edit_channel.__name__,
                                         msg="Channel successfully edited.")
        return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )

    except channel_controllers.Channel.DoesNotExist:
        return_data = await api_response(success=True, op=edit_channel.__name__, msg='Channel does not exist.',
                                         error='#CHANNEL_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except user_controllers.User.DoesNotExist:
        return_data = await api_response(success=True, op=edit_channel.__name__, msg='Channel owner does not exist.',
                                         error='#USER_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(edit_channel.__name__, traceback.format_exc())


@channels_api.route('/channels/edit_bot/<int:channel_id>/', methods=('POST', 'PATCH',))
@channels_api.route('/channels/edit_bot/', methods=('POST', 'PATCH',), defaults={'channel_id': None})
@app_auth_required
@json_content_type_required
@user_auth_required
@request_limit(5, ttl=60)
async def edit_channel_bot(channel_id: int)-> Response:
    """

    Edits the channel bot of the channel on the database.
    :param channel_id: The channel unique identifier

    The JSON formats to be passed by the call is at it follows:
    {
        "bot_id": int,
        "owner_info": {
            "user_id": int,
            "hash": `sha256 of "user_id" + unicode password, case sensitive`
        }
    }


    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "edit_channel_bot",
                 "msg": "Channel bot successfully edited."
             }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "edit_channel_bot",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "edit_channel_bot",
                 "msg": "Unauthorized Application"
             }

             403 - Forbidden
             {
                 "success": False,
                 "op": "edit_channel_bot",
                 "msg": "User not Authenticated."
             }

             404 - Channel not Found:
             {
                "success": False,
                "op": "edit_channel_bot",
                "msg": "Channel does not exist."
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "edit_channel_bot",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    if channel_id is None:
        return_data = await api_response(success=False, op=edit_channel_bot.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    data = await api_request(await request.data)
    # noinspection PyBroadException
    try:
        channel = await channel_controllers.get_channels(channel_id=int(channel_id))
        user = await user_controllers.get_users(user_id=int(data.user_info.user_id))
        if channel.creator != user.uid:
            return_data = await api_response(False, op=edit_channel_bot.__name__,
                                             msg='User not authorized to edit channel bot.',
                                             error='#USER_CANT_PERFORM')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

        if not bcrypt.checkpw(data.owner_info.hash.lower().encode(), user.user_secure):
            return_data = await api_response(False, op=edit_channel_bot.__name__, msg='User not Authenticated.',
                                             error='#USER_NOT_AUTHENTICATED')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

        bot_added = await channel_controllers.edit_channel_bot(user_model=user, channel_model=channel,
                                                               bot_id=int(data.bot_id))

        if bot_added:
            return_data = await api_response(success=True, op=edit_channel_bot.__name__,
                                             msg="Channel bot successfully edited.")
            return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )
        else:
            return_data = await api_response(False, op=edit_channel_bot.__name__,
                                             msg='User not authorized to edit channel.',
                                             error='#USER_CANT_PERFORM')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

    except user_controllers.User.DoesNotExist:
        return_data = await api_response(success=True, op=edit_channel_bot.__name__,
                                         msg='Channel owner does not exist.',
                                         error='#USER_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except user_controllers.Bot.DoesNotExist:
        return_data = await api_response(success=True, op=edit_channel_bot.__name__, msg='Bot does not exist.',
                                         error='#BOT_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except channel_controllers.Channel.DoesNotExist:
        return_data = await api_response(success=True, op=edit_channel_bot.__name__, msg='Channel does not exist.',
                                         error='#CHANNEL_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(edit_channel_bot.__name__, traceback.format_exc())


@channels_api.route('/channels/add_admins/<int:channel_id>/', methods=('POST', 'PATCH',))
@channels_api.route('/channels/add_admins/', methods=('POST', 'PATCH',), defaults={'channel_id': None})
@app_auth_required
@json_content_type_required
@user_auth_required
@request_limit(10, ttl=60)
async def add_admins(channel_id: int)-> Response:
    """

    Adds an admin to a channel on the database.
    :param channel_id: The channel unique identifier

    The JSON formats to be passed by the call is at it follows:
    {
        "new_admin": int,
        "owner_info": {
            "user_id": int,
            "hash": `sha256 of "user_id" + unicode password, case sensitive`
        }
    }


    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "add_admins",
                 "msg": "Admin successfully added."
             }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "add_admins",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "add_admins",
                 "msg": "Unauthorized Application"
             }

             403 - Forbidden
             {
                 "success": False,
                 "op": "add_admins",
                 "msg": "User not Authenticated."
             }

             404 - Channel not Found:
             {
                "success": False,
                "op": "add_admins",
                "msg": "Channel does not exist."
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "add_admins",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    if channel_id is None:
        return_data = await api_response(success=False, op=add_admins.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    data = await api_request(await request.data)
    # noinspection PyBroadException
    try:

        channel = await channel_controllers.get_channels(channel_id=int(channel_id))
        user = await user_controllers.get_users(user_id=int(data.user_info.user_id))
        if channel.creator != user.uid:
            return_data = await api_response(False, op=add_admins.__name__,
                                             msg='User not authorized to edit channel.',
                                             error='#USER_CANT_PERFORM')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

        if not bcrypt.checkpw(data.owner_info.hash.lower().encode(), user.user_secure):
            return_data = await api_response(False, op=add_admins.__name__, msg='User not Authenticated.',
                                             error='#USER_NOT_AUTHENTICATED')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

        try:
            new_admin = await user_controllers.get_users(user_id=data.new_admin)
        except user_controllers.User.DoesNotExist:
            return_data = await api_response(success=True, op=add_admins.__name__, msg='User does not exist.',
                                             error='#ADMIN_NOT_FOUND')
            return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )

        admin_added = await channel_controllers.add_admins(channel_model=channel, user_model=user,
                                                           admin_model=new_admin)

        if admin_added:
            return_data = await api_response(success=True, op=add_admins.__name__,
                                             msg="Admin successfully added.")
            return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )
        else:
            return_data = await api_response(False, op=add_admins.__name__,
                                             msg='User not authorized to add admins.', error='#USER_CANT_PERFORM')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

    except user_controllers.User.DoesNotExist:
        return_data = await api_response(success=True, op=add_admins.__name__,
                                         msg='Channel owner does not exist.', error='#USER_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except channel_controllers.Channel.DoesNotExist:
        return_data = await api_response(success=True, op=add_admins.__name__, msg='Channel does not exist.',
                                         error='#CHANNEL_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(add_admins.__name__, traceback.format_exc())


@channels_api.route('/channels/edit_admin/<int:channel_id>/<int:admin_id>/', methods=('POST', 'PATCH',))
@channels_api.route('/channels/edit_admin/<int:channel_id>/', methods=('POST', 'PATCH',), defaults={'admin_id': None})
@channels_api.route('/channels/edit_admin/', methods=('POST', 'PATCH',),
                    defaults={'channel_id': None, 'admin_id': None})
@app_auth_required
@json_content_type_required
@user_auth_required
@request_limit(5, ttl=60*2)
async def edit_admin(channel_id: int, admin_id: int)-> Response:
    """
    Edits the admin permissions in the database.
    :param channel_id: The channel unique identifier
    :param admin_id: The admin unique identifier


    The JSON formats to be passed by the call is at it follows:
    {
        "admin_properties": {
                "can_edit_others": bool,
                "can_delete_others": bool,
                "can_edit_channel_info": bool
            }
        "owner_info": {
            "user_id": int,
            "hash": `sha256 of "user_id" + unicode password, case sensitive`
        }
    }

    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "edit_admin",
                 "msg": "Admin successfully edited."
             }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "edit_admin",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "edit_admin",
                 "msg": "Unauthorized Application"
             }

             403 - Forbidden
             {
                 "success": False,
                 "op": "edit_admin",
                 "msg": "User not Authenticated."
             }

             404 - Channel / User not Found:
             {
                "success": False,
                "op": "edit_admin",
                "msg": "{channel / user} does not exist."
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "edit_admin",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    if channel_id is None or admin_id is None:
        return_data = await api_response(success=False, op=edit_admin.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    data = await api_request(await request.data)
    # noinspection PyBroadException
    try:

        channel = await channel_controllers.get_channels(channel_id=int(channel_id))
        user = await user_controllers.get_users(user_id=int(data.user_info.user_id))
        if channel.creator != user.uid:
            return_data = await api_response(False, op=edit_admin.__name__,
                                             msg='User not authorized to edit channel.',
                                             error='#USER_CANT_PERFORM')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

        if not bcrypt.checkpw(data.owner_info.hash.lower().encode(), user.user_secure):
            return_data = await api_response(False, op=edit_admin.__name__, msg='User not Authenticated.',
                                             error='#USER_NOT_AUTHENTICATED')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

        index = 0
        admin_exists = False
        for admin in channel.authorized_admins:
            if admin.uid != int(admin_id):
                index += 1
                continue

            admin_exists = True
            if data.admin_properties.can_edit_others is not None:
                channel.authorized_admins[index].can_edit_others = data.admin_properties.can_edit_others
            if data.admin_properties.can_delete_others is not None:
                channel.authorized_admins[index].can_delete_others = data.admin_properties.can_delete_others
            if data.admin_properties.can_edit_channel_info is not None:
                channel.authorized_admins[index].can_edit_channel_info = data.admin_properties.can_edit_channel_info
            break

        if admin_exists:
            return_data = await api_response(success=True, op=edit_admin.__name__,
                                             msg="Admin successfully edited.")
            return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )
        else:
            return_data = await api_response(success=True, op=edit_admin.__name__, msg='User does not exist.',
                                             error='#ADMIN_NOT_FOUND')
            return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )

    except user_controllers.User.DoesNotExist:
        return_data = await api_response(success=True, op=edit_admin.__name__,
                                         msg='Channel owner does not exist.', error='#USER_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except channel_controllers.Channel.DoesNotExist:
        return_data = await api_response(success=True, op=edit_admin.__name__, msg='Channel does not exist.',
                                         error='#CHANNEL_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(edit_admin.__name__, traceback.format_exc())


@channels_api.route('/channels/remove_admin/<int:channel_id>/<int:admin_id>/', methods=('DELETE', ))
@channels_api.route('/channels/remove_admin/<int:channel_id>/', methods=('POST', 'PATCH',), defaults={'admin_id': None})
@channels_api.route('/channels/remove_admin/', methods=('POST', 'PATCH'),
                    defaults={'channel_id': None, 'admin_id': None})
@app_auth_required
@json_content_type_required
@user_auth_required
@request_limit(10, ttl=60)
async def remove_admin(channel_id: int, admin_id: int)-> Response:
    """
    Removes the authorization of an admin from a channel.
    :param channel_id: The channel unique identifier
    :param admin_id: The admin unique identifier

    The JSON formats to be passed by the call is at it follows:
    {
        "owner_info": {
            "user_id": int,
            "hash": `sha256 of "user_id" + unicode password, case sensitive`
        }
    }
    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "remove_admin",
                 "msg": "Admin successfully edited."
             }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "remove_admin",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "remove_admin",
                 "msg": "Unauthorized Application"
             }

             403 - Forbidden
             {
                 "success": False,
                 "op": "remove_admin",
                 "msg": "User not Authenticated."
             }

             404 - Channel / User not Found:
             {
                "success": False,
                "op": "remove_admin",
                "msg": "{channel / user} does not exist."
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "remove_admin",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    if channel_id is None or admin_id is None:
        return_data = await api_response(success=False, op=remove_admin.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    data = await api_request(await request.data)
    # noinspection PyBroadException
    try:

        channel = await channel_controllers.get_channels(channel_id=int(channel_id))
        user = await user_controllers.get_users(user_id=int(data.user_info.user_id))
        if channel.creator != user.uid:
            return_data = await api_response(False, op=remove_admin.__name__,
                                             msg='User not authorized to edit channel.',
                                             error='#USER_CANT_PERFORM')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

        if not bcrypt.checkpw(data.owner_info.hash.lower().encode(), user.user_secure):
            return_data = await api_response(False, op=remove_admin.__name__, msg='User not Authenticated.',
                                             error='#USER_NOT_AUTHENTICATED')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

        index = 0
        admin_exists = False
        for admin in channel.authorized_admins:
            if admin.uid != int(admin_id):
                index += 1
                continue

            admin_exists = True
            break

        if admin_exists:
            channel.authorized_admins.pop(index)
            return_data = await api_response(success=True, op=remove_admin.__name__,
                                             msg="Admin successfully removed.")
            return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )
        else:
            return_data = await api_response(success=True, op=remove_admin.__name__, msg='User does not exist.',
                                             error='#ADMIN_NOT_FOUND')
            return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )

    except user_controllers.User.DoesNotExist:
        return_data = await api_response(success=True, op=remove_admin.__name__,
                                         msg='Channel owner does not exist.', error='#USER_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except channel_controllers.Channel.DoesNotExist:
        return_data = await api_response(success=True, op=remove_admin.__name__, msg='Channel does not exist.',
                                         error='#CHANNEL_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(remove_admin.__name__, traceback.format_exc())


@channels_api.route('/channels/remove/<int:channel_id>', methods=('DELETE', ))
@channels_api.route('/channels/remove/', methods=('DELETE',), defaults={'channel_id': None})
@app_auth_required
@json_content_type_required
@user_auth_required
@request_limit(20, 60)
async def remove_channel(channel_id: int)-> Response:
    """
    Removes a channel from the database, and all the posts associated with it.
    :param channel_id: The channel unique identifier

    The JSON formats to be passed by the call is at it follows:
    {
        "owner_info": {
            "user_id": int,
            "hash": `sha256 of "user_id" + unicode password, case sensitive`
        }
    }
    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "remove_channel",
                 "msg": "Channel and all it's associated data successfully removed."
             }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "remove_channel",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "remove_channel",
                 "msg": "Unauthorized Application"
             }

             403 - Forbidden
             {
                 "success": False,
                 "op": "remove_channel",
                 "msg": "{reason}"
             }

             404 - Channel / User not Found:
             {
                "success": False,
                "op": "remove_channel",
                "msg": "{channel / user} does not exist."
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "remove_channel",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    if channel_id is None:
        return_data = await api_response(success=False, op=remove_admin.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    data = await api_request(await request.data)
    # noinspection PyBroadException
    try:
        channel = await channel_controllers.get_channels(channel_id=int(channel_id))
        user = await user_controllers.get_users(user_id=int(data.user_info.user_id))

        if channel.creator != user.uid:
            return_data = await api_response(False, op=remove_channel.__name__,
                                             msg='User not authorized to remove channel.',
                                             error='#USER_CANT_PERFORM')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json')

        if not bcrypt.checkpw(data.owner_info.hash.lower().encode(), user.user_secure):
            return_data = await api_response(False, op=remove_channel.__name__, msg='User not Authenticated.',
                                             error='#USER_NOT_AUTHENTICATED')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

        channel_deleted = await channel_controllers.delete_channel(channel)

        if channel_deleted:
            return_data = await api_response(success=True, op=remove_channel.__name__,
                                             msg="Channel and all it's associated data successfully removed.")
            return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )
        else:
            raise channel_controllers.Channel.DoesNotExist('')

    except channel_controllers.Channel.DoesNotExist:
        return_data = await api_response(success=True, op=remove_channel.__name__, msg='Channel does not exist.',
                                         error='#CHANNEL_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except user_controllers.User.DoesNotExist:
        return_data = await api_response(success=True, op=remove_channel.__name__, msg='Channel owner does not exist.',
                                         error='#USER_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(remove_channel.__name__, traceback.format_exc())
