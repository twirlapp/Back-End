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

from src.controllers.app_controllers import is_app_authorized
from src.utils.json_handlers import api_response
from functools import wraps
from quart import request, Response
from typing import Callable


def app_auth_required(func: Callable):
    """
    Decorator to Require app authentication.
    """
    @wraps(func)
    async def decorator(*args, **kwargs):
        headers = request.headers
        _auth = headers.get('Authorization', None)
        auth: str = _auth if _auth is not None else request.authorization
        if auth is None or (len(auth.split(' ')) < 2) or not is_app_authorized(auth.split(' ')[1]):
            return_data = await api_response(success=False, op=func.__name__, msg="Unauthorized Application")
            return Response(return_data, status=401, mimetype='application/json', content_type='application/json', )
        else:
            return await func(*args, **kwargs)
    return decorator


JSON_CONTENT_TYPES = ('application/json', 'Application/Json', )


def json_content_type_required(func: Callable):
    """
    Decorator to require JSON content type header
    """
    @wraps(func)
    async def decorator(*args, **kwargs):
        headers = request.headers
        _ct = headers.get('Content-Type', None)
        content_type = _ct if _ct is not None else request.content_type
        if content_type is None or content_type.lower() != 'application/json':
            return_data = await api_response(success=False, op="add_users", msg="Invalid Content Type")
            return Response(return_data, status=400, mimetype='application/json', content_type='application/json', )
        else:
            return await func(*args, **kwargs)
    return decorator
