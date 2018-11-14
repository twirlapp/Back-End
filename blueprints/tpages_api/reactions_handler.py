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
from src.controllers import reaction_controllers, post_controllers
from .api_utils import app_auth_required, json_content_type_required, error_response, request_limit
from src.utils.json_handlers import api_request, api_response
import traceback

reactions_api = Blueprint('reactions', __name__, static_folder='./static', static_url_path='/static/files',
                          template_folder='./templates', subdomain='api')


@reactions_api.route('/reactions/react/<string:post_id>/', methods=('POST',))
@reactions_api.route('/reactions/react/', methods=('POST',), defaults={'post_id': None})
@app_auth_required
@json_content_type_required
@request_limit(60, 30)
async def react(post_id: str)-> Response:
    """
    Changes the state of a reaction by an user on a post.
    :param post_id: The post unique identifier on the database

    The JSON formats to be passed by the call is at it follows:
    {
        "user_id": int,
        "index": int(0-3)
    }

    :return: JSON serialized Response

             Possible Responses:
             200 - OK, with response:
             {
                 "success": True,
                 "op": "react",
                 "msg": "Reaction changed.",
                 "reactions": {
                    "reactions": [
                        {
                            "emoji": str,
                            "count": int,
                        },
                        {
                            "emoji": str,
                            "count": int,
                        },
                        ...
                    ],
                    "total_count": int
                 }
             }

             400 - Bad Request:
             {
                 "success": False,
                 "op": "react",
                 "msg": "{reason}"

             }

             401 - Unauthorized:
             {
                 "success": False,
                 "op": "react",
                 "msg": "Unauthorized Application"
             }

             404 - User not Found:
             {
                "success": False,
                "op": "react",
                "msg": "Post does not exist."
             }

             500 - Server Error:
             {
                 "success": False,
                 "op": "react",
                 "msg": "Internal Server Error",
                 "stack_trace": str (Python stacktrace)
             }
    """
    data = await api_request(await request.data)
    if post_id is None or data.user_id is None:
        return_data = await api_response(success=False, op=react.__name__, msg='Malformed request data.',
                                         error='#MALFORMED_REQUEST')
        return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )

    # noinspection PyBroadException
    try:
        post = await post_controllers.get_posts(post_id=post_id)

        if data.reaction_index is not None and isinstance(data.reaction_index, int):
            try:
                await reaction_controllers.user_reaction(user_id=data.user_id, post_id=post.post_id,
                                                         index=data.reaction_index)
            except IndexError:
                return_data = await api_response(success=False, op=react.__name__, msg="Reaction doesn't exist.",
                                                 error='#REACTION_NOT_FOUND')
                return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
        else:
            await reaction_controllers.remove_user_reaction(user_id=data.user_id, post_id=post.post_id)

        post = await post_controllers.get_posts(post_id=post_id)
        reactions = dict(
            reactions=[dict(emoji=i.emoji, count=i.count) for i in post.reactions.reactions],
            total_count=post.reactions.total_count
        )
        return_data = await api_response(success=True, op=react.__name__, msg='Reaction changed.',
                                         reactions=reactions)
        return Response(return_data, status=200, mimetype='application/json', content_type='application/json', )

    except post_controllers.PostModel.DoesNotExist:
        return_data = await api_response(success=False, op=react.__name__, msg="Post doesn't exist.",
                                         error='#POST_NOT_FOUND')
        return Response(return_data, status=404, mimetype='application/json', content_type='application/json', )
    except Exception:
        return await error_response(op=react.__name__, stack_trace=traceback.format_exc())
