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
from src.controllers import user_controllers
from .api_utils import app_auth_required, json_content_type_required, error_response, request_limit, user_auth_required
from src.utils.json_handlers import api_request, api_response, SuperDict
from src.utils.security import hash_generator
import traceback
import bcrypt
import config

users_api = Blueprint('users', __name__, static_folder='./static', static_url_path='/static/files',
                      template_folder='./templates', subdomain='api')


def verify_user(request_data: SuperDict)-> bool:
    """
    Verifies the validity of a user object to be added to the database
    :param request_data:
    :return: True if valid, False otherwise
    """
    user_id = request_data.user_id
    first_name = request_data.first_name
    profile_photo = request_data.profile_photo
    pw_hash = request_data.hash
    valid = False
    if user_id is not None and first_name is not None and profile_photo is not None and \
            isinstance(profile_photo, SuperDict) and pw_hash is not None:
        valid = True
    return valid


def verify_bot(request_data: SuperDict)-> bool:
    """
    Verifies the validity of a user object to be added to the database
    :param request_data:
    :return: True if valid, False otherwise
    """
    bot_id = request_data.user_id
    bot_name = request_data.bot_name
    profile_photo = request_data.profile_photo
    owner_info = request_data.owner_info
    valid = False
    if bot_id is not None and bot_name is not None and profile_photo is not None and \
            isinstance(profile_photo, SuperDict) and isinstance(owner_info, SuperDict) and \
            owner_info.user_id is not None and owner_info.hash is not None:
        valid = True
    return valid


@users_api.route('/users/auth', methods=('POST', ))
@app_auth_required
@json_content_type_required
async def auth_user()-> Response:
    """
    Gets the information of a user and authenticates using the temporary app secret key. The temporary app secret key
    resets every four hours, so every four hours the client must re-auth.

    The JSON formats to be passed by the call is at it follows:
    {
        "user_id": int,
        "hash": `sha256 of "user_id" + unicode password, case sensitive`
    }

    NOTE: From the authorization on, the client MUST provide the headers
          'Auth-Hash' with the temporary auth key, and 'User-Id' containing the unique identifier of the authenticated
          user on every request. When the authorization fails, the client MUST authenticate the user again.

    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "auth_user",
                 "msg": "User is now authenticated."
             }
             Headers: 'Use-Auth-Hash': True
                      'Auth-Hash': `newly generated auth hash`

             400 - Bad Request:
             {
                 "success": False,
                 "op": "auth_user",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "auth_user",
                 "msg": "Unauthorized Application"
             }

             403 - Forbidden:
             {
                "success": False,
                "op": "auth_user",
                "msg": "User authentication failed."
             }

             404 - User not Found:
             {
                "success": False,
                "op": "auth_user",
                "msg": "User does not exist."
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "auth_user",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    data = await api_request(await request.data)
    if data.user_id is None or data.hash is None:
        return_data = await api_response(success=False, op=auth_user.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    # noinspection PyBroadException
    try:
        user = await user_controllers.get_users(user_id=int(data.user_id))
        if not bcrypt.checkpw(data.hash.lower().encode(), user.user_secure):
            return_data = await api_response(success=False, op=auth_user.__name__, msg='User not Authenticated.',
                                             error='#USER_NOT_AUTHENTICATED')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )
        else:
            new_hash = hash_generator((str(user.uid) + config.APP_TEMP_SECRET_KEY), hash_type='sha256')
            return_data = await api_response(success=True, op=auth_user.__name__, msg='User is now authenticated.')
            res = Response(return_data, status=200, mimetype='application/json', content_type='application/json', )
            res.headers.add('Use-Auth-Hash', True)
            res.headers.add('Auth-Hash', new_hash)
            return res

    except user_controllers.User.DoesNotExist:
        return_data = await api_response(success=True, op=auth_user.__name__, msg='User does not exist.',
                                         error='#USER_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(add_users.__name__, traceback.format_exc())


@users_api.route('/users/add', methods=('POST', ), )
@app_auth_required
@json_content_type_required
async def add_users()-> Response:  # Returns 'application/json'
    """
    Adds users to the application. Users can be channel creators, channel admins, or normal users.
    - Normal users can comment in posts. It is not needed to be registered on the database to be able to react to posts
      or to share posts, they are tracked simply by their user ID.
    - Channel Admins can do all above, plus post to channels they are admins, review and moderate content
      (when authorized), review and moderate comments, and edit some info of the channel (when authorized)
    - Channel Owners can do all the above, without authorization, plus add / remove channel admins, add, edit and delete
      channels, add, edit or remove registered bots to make custom posts in the channels.

    The JSON formats to be passed by the call is at it follows:
    {
        "user_id": int,
        "first_name": str,
        "last_name": str,
        "username": str,
        "profile_photo": {
            "photo": str (Unique identifier of the photo),
            "thumbnail": str (Unique identifier of the photo)
        },
        "hash": `sha256 of "user_id" + unicode password, case sensitive`
    }

    [
        {
            "user_id": int,
            "first_name": str,
            "last_name": str,
            "username": str,
            "profile_photo": {
                "photo": str (Unique identifier of the photo),
                "thumbnail": str (Unique identifier of the photo)
            },
            "hash": `sha256 of "user_id" + unicode password, case sensitive`
        },
        {
            "user_id": int,
            "first_name": str,
            "last_name": str,
            "username": str,
            "profile_photo": {
                "photo": str (Unique identifier of the photo),
                "thumbnail": str (Unique identifier of the photo)
            },
            "hash": `sha256 of "user_id" + unicode password, case sensitive`
        }, ...
    ]
    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "add_users",
                 "msg": "User(s) successfully added",
                 "qty": numberOfAdditions int
             }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "add_users",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "add_users",
                 "msg": "Unauthorized Application"
             }

             403 - Forbidden (User already added)
             {
                 "success": False,
                 "op": "add_users",
                 "msg": "User(s) already added."
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "get_user",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }

    """
    data = await api_request(await request.data)
    if not verify_user(data):
        return_data = await api_response(success=False, op=add_users.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    # noinspection PyBroadException
    try:
        count = 0
        if isinstance(data, list):
            for user in data:
                await user_controllers.add_user(int(user.user_id), password_hash=user.hash, first_name=user.first_name,
                                                last_name=user.last_name, username=user.username,
                                                profile_photo=user.profile_photo.photo,
                                                profile_thumb=user.profile_photo.thumbnail)
                count += 1
        else:
            await user_controllers.add_user(int(data.user_id), password_hash=data.hash, first_name=data.first_name,
                                            last_name=data.last_name, username=data.username,
                                            profile_photo=data.profile_photo.photo,
                                            profile_thumb=data.profile_photo.thumbnail)
            count += 1

        return_data = await api_response(success=True, op=add_users.__name__,
                                         msg="User(s) successfully added.", qty=count)
        return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )
    except user_controllers.UserAlreadyAdded:
        return_data = await api_response(success=False, op=add_users.__name__,
                                         msg="User is already registered.", error='#USER_ALREADY_REGISTERED')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(add_users.__name__, traceback.format_exc())


@users_api.route('/users/get/<int:user_id>', methods=('GET', ))
@app_auth_required
@user_auth_required
@request_limit(max_requests=200)
async def get_user(user_id: int)-> Response:  # Returns 'application/json'
    """
    Gets some basic user info from the database.
    :param user_id: The user unique identifier on the database.
    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "get_user",
                 "user": {
                            "user_id": int,
                            "first_name": str,
                            "last_name": str,
                            "username": str,
                            "profile_photo": {
                                "photo": str (Unique identifier of the photo),
                                "thumbnail": str (Unique identifier of the photo)
                            }
                        }
             }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "get_user",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "get_user",
                 "msg": "Unauthorized Application"
             }

             404 - User not Found:
             {
                "success": False,
                "op": "get_user",
                "msg": "User does not exist."
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "get_user",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    # noinspection PyBroadException
    try:
        user = await user_controllers.get_users(user_id=int(user_id))
        data = {
            "user_id": user.uid,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "user_name": user.username,
            "profile_photo": {
                "photo": user.profile_photo,
                "thumbnail": user.profile_thumbnail
            }
        }
        return_data = await api_response(success=True, op=get_user.__name__, msg=None, user=data)
        return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )
    except user_controllers.User.DoesNotExist:
        return_data = await api_response(success=True, op=get_user.__name__, msg='User does not exist.',
                                         error='#USER_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(get_user.__name__, traceback.format_exc())


@users_api.route('/users/edit/<int:user_id>', methods=('POST', ))
@app_auth_required
@user_auth_required
@request_limit(max_requests=20, ttl=60)
@json_content_type_required
async def edit_user(user_id: int)-> Response:  # Returns 'application/json'
    """
    Edits the user info on the database.

    The JSON formats to be passed by the call is at it follows:
    {
        "first_name": str,
        "last_name": str,
        "username": str,
        "profile_photo": {
            "photo": str (Unique identifier of the photo),
            "thumbnail": str (Unique identifier of the photo)
        },
        "hash": `sha256 of "user_id" + unicode password, case sensitive`
        "new_hash": `sha256 of "user_id" + a new unicode password, case sensitive, must be different from hash.`
    }

    :param user_id: The user unique identifier on the database.
    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "edit_user",
                 "msg": "User successfully edited."
             }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "edit_user",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "edit_user",
                 "msg": "Unauthorized Application."
             }

             403 - Forbidden:
             {
                 "success": False,
                 "op": "edit_user",
                 "msg": "User not Authenticated."
             }

             404 - User not Found:
             {
                "success": False,
                "op": "edit_user",
                "msg": "User does not exist."
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "edit_user",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """

    data = await api_request(await request.data)
    data.user_id = user_id
    if not verify_user(data):
        return_data = await api_response(success=False, op=edit_user.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    # noinspection PyBroadException
    try:
        user = await user_controllers.get_users(user_id=int(data.user_id))

        if data.hash is None or not bcrypt.checkpw(data.hash.lower().encode(), user.user_secure):
            return_data = await api_response(False, op=edit_user.__name__, msg='User not Authenticated.',
                                             error='#USER_NOT_AUTHENTICATED')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

        if data.hash == data.new_hash:
            data.new_hash = None

        await user_controllers.edit_user_info(user_model=user, new_password_hash=data.new_hash,
                                              first_name=data.first_name,
                                              last_name=data.last_name, username=data.username,
                                              profile_photo=data.profile_photo.photo,
                                              profile_thumb=data.profile_photo.thumbnail)

        return_data = await api_response(success=True, op=edit_user.__name__,
                                         msg="User successfully edited.")
        return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )

    except user_controllers.User.DoesNotExist:
        return_data = await api_response(success=True, op=edit_user.__name__, msg='User does not exist.',
                                         error='#USER_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(edit_user.__name__, traceback.format_exc())


@users_api.route('/users/remove/<int:user_id>', methods=('DELETE', ))
@app_auth_required
@user_auth_required
@request_limit(max_requests=1, ttl=60*60)
@json_content_type_required
async def remove_user(user_id: int)-> Response:  # Returns 'application/json'
    """
    Removes an user from the database, by setting the deleted flag.

    The JSON formats to be passed by the call is at it follows:
    {
        "user_id": int,
        "hash": `sha256 of "user_id" + password`
    }

    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "remove_user",
                 "msg": "User and everything associated with was successfully removed."
             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "remove_user",
                 "msg": "Unauthorized Application"
             }

             403 - Forbidden:
             {
                 "success": False,
                 "op": "remove_user",
                 "msg": "User not Authenticated."
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "remove_user",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    data = await api_request(await request.data)
    if data.user_id is None or data.hash is None:
        return_data = await api_response(success=False, op=remove_user.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    # noinspection PyBroadException
    try:
        user = await user_controllers.get_users(user_id=int(user_id))
        if not bcrypt.checkpw(data.hash.lower().encode(), user.user_secure):
            return_data = await api_response(success=False, op=remove_user.__name__, msg='User not Authenticated.',
                                             error='#USER_NOT_AUTHENTICATED')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )
        else:
            await user_controllers.delete_user(user_model=user)
            return_data = await api_response(success=True, op=remove_user.__name__,
                                             msg='User and everything associated with was successfully removed.')
            return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )
    except user_controllers.User.DoesNotExist:
        return_data = await api_response(success=True, op=remove_user.__name__, msg='User does not exist.',
                                         error='#USER_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(remove_user.__name__, traceback.format_exc())


@users_api.route('/bots/add', methods=('POST', ))
@app_auth_required
@user_auth_required
@request_limit(max_requests=20, ttl=60*60)
async def add_bots()-> Response:  # Returns 'application/json'
    """
        Adds bots to the application. Bots are channel administrators to create and send custom posts.
        - Post bots can post, edit and delete own posts (posts sent through them)

        The JSON formats to be passed by the call is at it follows:
        {
            "bot_id": int,
            "bot_name": str,
            "bot_token": str,
            "username": str,
            "profile_photo": {
                "photo": str (Unique identifier of the photo),
                "thumbnail": str (Unique identifier of the photo)
            },
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
                     "op": "add_bots",
                     "msg": "Bot successfully added"
                 }

                 400 - Bad Request:
                 {
                     "success": False,
                     "op": "add_bots",
                     "msg": "{reason}"

                 }

                 401 - Unauthorized:
                 {
                     "success": False,
                     "op": "add_bots",
                     "msg": "Unauthorized Application"
                 }

                 403 - Forbidden
                 {
                     "success": False,
                     "op": "add_bots",
                     "msg": "User not authenticated."
                 }

                 500 - Server Error:
                 {
                     "success": False,
                     "op": "get_user",
                     "msg": "Internal Server Error",
                     "stack_trace": str (Python stacktrace)
                 }

        """
    data = await api_request(await request.data)
    if not verify_bot(data):
        return_data = await api_response(success=False, op=add_bots.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    # noinspection PyBroadException
    try:
        user = await user_controllers.get_users(user_id=int(data.owner_info.user_id))
        if not bcrypt.checkpw(data.owner_info.hash.lower().encode(), user.user_secure):
            return_data = await api_response(False, op=add_bots.__name__, msg='User not Authenticated.',
                                             error='#USER_NOT_AUTHENTICATED')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

        await user_controllers.add_bot(bot_id=data.bot_id, bot_token=data.bot_token, user_model=user,
                                       bot_name=data.bot_name,
                                       username=data.username, profile_photo=data.profile_photo.photo,
                                       profile_thumb=data.profile_photo.thumbnail)

        return_data = await api_response(success=True, op=add_bots.__name__,
                                         msg="Bot(s) successfully added.")
        return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )
    except user_controllers.BotAlreadyAdded:
        return_data = await api_response(success=False, op=add_bots.__name__,
                                         msg="Bot is already registered.", error='#BOT_ALREADY_REGISTERED')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    except user_controllers.User.DoesNotExist:
        return_data = await api_response(success=True, op=add_bots.__name__, msg='Bot owner does not exist.',
                                         error='#USER_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(add_bots.__name__, traceback.format_exc())


@users_api.route('/bots/get/<int:bot_id>', methods=('GET', ))
@app_auth_required
@user_auth_required
async def get_bot(bot_id: int)-> Response:  # Returns 'application/json'
    """
        Gets some basic bot info from the database.
        :param bot_id: The bot unique identifier on the database.
        :return: JSON serialized Response

                 Possible Responses:
                 200 - OK, with response:
                 {
                     "success": True,
                     "op": "get_bot",
                     "bot": {
                                "bot_id": int,
                                "bot_name": str,
                                "username": str,
                                "profile_photo": {
                                    "photo": str (Unique identifier of the photo),
                                    "thumbnail": str (Unique identifier of the photo)
                                }
                            }
                 }

                 400 - Bad Request:
                 {
                     "success": False,
                     "op": "get_bot",
                     "msg": "{reason}"

                 }

                 401 - Unauthorized:
                 {
                     "success": False,
                     "op": "get_bot",
                     "msg": "Unauthorized Application"
                 }

                 404 - User not Found:
                 {
                    "success": False,
                    "op": "get_bot",
                    "msg": "Bot does not exist."
                 }

                 500 - Server Error:
                 {
                     "success": False,
                     "op": "get_bot",
                     "msg": "Internal Server Error",
                     "stack_trace": str (Python stacktrace)
                 }
        """
    # noinspection PyBroadException
    try:
        bot = await user_controllers.get_bots(bot_id=bot_id)
        data = {
            "bot_id": bot.bot_id,
            "bot_name": bot.name,
            "user_name": bot.username,
            "profile_photo": {
                "photo": bot.profile_photo,
                "thumbnail": bot.profile_thumbnail
            }
        }
        return_data = await api_response(success=True, op=get_bot.__name__, msg=None, bot=data)
        return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )
    except user_controllers.Bot.DoesNotExist:
        return_data = await api_response(success=True, op=get_bot.__name__, msg='Bot does not exist.',
                                         error='#BOT_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(get_bot.__name__, traceback.format_exc())


@users_api.route('/bots/edit/<int:bot_id>', methods=('POST', ))
@app_auth_required
@user_auth_required
@request_limit(max_requests=5, ttl=60)
@json_content_type_required
async def edit_bot(bot_id: int)-> Response:  # Returns 'application/json'
    """
        Edits the user info on the database.

        The JSON formats to be passed by the call is at it follows:
        {
            "bot_name": str,
            "bot_token": str,
            "username": str,
            "profile_photo": {
                "photo": str (Unique identifier of the photo),
                "thumbnail": str (Unique identifier of the photo)
            },
            "owner_info": {
                "user_id": int,
                "hash": `sha256 of "user_id" + unicode password, case sensitive`
            }
        }

        :param bot_id: The bot unique identifier on the database.
        :return: JSON serialized Response

                 Possible Responses:
                 200 - OK, with response:
                 {
                     "success": True,
                     "op": "edit_bot",
                     "msg": "Bot successfully edited."
                 }

                 400 - Bad Request:
                 {
                     "success": False,
                     "op": "edit_bot",
                     "msg": "{reason}"

                 }

                 401 - Unauthorized:
                 {
                     "success": False,
                     "op": "edit_bot",
                     "msg": "Unauthorized Application."
                 }

                 403 - Forbidden:
                 {
                     "success": False,
                     "op": "edit_bot",
                     "msg": "User not Authenticated."
                 }

                 404 - User not Found:
                 {
                    "success": False,
                    "op": "edit_bot",
                    "msg": "User does not exist."
                 }

                 500 - Server Error:
                 {
                     "success": False,
                     "op": "edit_bot",
                     "msg": "Internal Server Error",
                     "stack_trace": str (Python stacktrace)
                 }
        """

    data = await api_request(await request.data)
    data.bot_id = bot_id
    if not verify_bot(data):
        return_data = await api_response(success=False, op=edit_bot.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    # noinspection PyBroadException
    try:
        user = await user_controllers.get_users(user_id=int(data.owner_info.user_id))
        bot = user_controllers.get_bots(bot_id=bot_id)

        if bot.owner != user.uid:
            return_data = await api_response(False, op=edit_bot.__name__, msg='User can not edit bot.',
                                             error='#USER_CANT_PERFORM')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

        if not bcrypt.checkpw(data.owner_info.hash.lower().encode(), user.user_secure):
            return_data = await api_response(False, op=edit_bot.__name__, msg='User not Authenticated.',
                                             error='#USER_NOT_AUTHENTICATED')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

        await user_controllers.edit_bot_info(bot_model=bot, bot_token=data.bot_token, bot_name=data.bot_name,
                                             username=data.username, profile_photo=data.profile_photo.photo,
                                             profile_thumb=data.profile_photo.thumbnail)

        return_data = await api_response(success=True, op=edit_bot.__name__,
                                         msg="Bot successfully edited.")
        return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )

    except user_controllers.Bot.DoesNotExist:
        return_data = await api_response(success=True, op=edit_bot.__name__, msg='Bot does not exist.',
                                         error='#BOT_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except user_controllers.User.DoesNotExist:
        return_data = await api_response(success=True, op=edit_bot.__name__, msg='Bot owner does not exist.',
                                         error='#USER_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(edit_bot.__name__, traceback.format_exc())


@users_api.route('/bots/remove/<int:bot_id>', methods=('DELETE', ))
@app_auth_required
@user_auth_required
@request_limit(max_requests=50, ttl=60*60)
@json_content_type_required
async def remove_bot(bot_id: int)-> Response:  # Returns 'application/json'
    """
        Removes a bot from the database, by setting the deleted flag.

        The JSON formats to be passed by the call is at it follows:
        {
            "bot_id": int,
            "bot_token": str,
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
                     "op": "remove_bot",
                     "msg": "Bot disassociated from all channels and removed."
                 }

                 401 - Unauthorized:
                 {
                     "success": False,
                     "op": "remove_bot",
                     "msg": "Unauthorized Application"
                 }

                 403 - Forbidden:
                 {
                     "success": False,
                     "op": "remove_bot",
                     "msg": "User not Authenticated."
                 }

                 500 - Server Error:
                 {
                     "success": False,
                     "op": "remove_bot",
                     "msg": "Internal Server Error",
                     "stack_trace": str (Python stacktrace)
                 }
        """
    data = await api_request(await request.data)
    if data.bot_id is None or data.bot_token is None or data.owner_info is None \
            or not isinstance(data.owner_info, SuperDict) or \
            (data.owner_info.user_id is None or data.owner_info.hash is None):
        return_data = await api_response(success=False, op=remove_bot.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
    # noinspection PyBroadException
    try:
        user = await user_controllers.get_users(user_id=int(data.owner_info.user_id))
        bot = user_controllers.get_bots(bot_id=bot_id)

        if bot.owner != user.uid:
            return_data = await api_response(False, op=remove_bot.__name__, msg='User can not edit bot.',
                                             error='#USER_CANT_PERFORM')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )

        if not bcrypt.checkpw(data.owner_info.hash.lower().encode(), user.user_secure):
            return_data = await api_response(False, op=remove_bot.__name__, msg='User not Authenticated.',
                                             error='#USER_NOT_AUTHENTICATED')
            return Response(return_data, status=403, mimetype='application/json', content_type='application/json', )
        await user_controllers.delete_bot(bot_model=bot)
        return_data = await api_response(success=True, op=remove_bot.__name__,
                                         msg='Bot disassociated from all channels and removed.')
        return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )
    except user_controllers.User.DoesNotExist:
        return_data = await api_response(success=True, op=remove_bot.__name__, msg='Bot does not exist.',
                                         error='#BOT_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(remove_bot.__name__, traceback.format_exc())
