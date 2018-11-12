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
from src.controllers.user_controllers import get_users
from src.utils.json_handlers import api_response, SuperDict, decode
from functools import wraps
from quart import Response, request
from itsdangerous import URLSafeTimedSerializer, BadTimeSignature, SignatureExpired
from typing import Callable
from threading import Thread
import time
import config


def app_auth_required(func: Callable):
    """
    Decorator to Require app authentication.
    """
    @wraps(func)
    async def decorator(*args, **kwargs):
        headers = request.headers
        _auth = headers.get('Authorization', None)
        auth: str = _auth if _auth is not None else request.authorization
        if auth is None or (len(auth.split(' ')) < 2) or not await is_app_authorized(auth.split(' ')[1]):
            return_data = await api_response(success=False, op=func.__name__, msg="Unauthorized Application.",
                                             error='#APP_NOT_AUTHORIZED')
            return Response(return_data, status=401, mimetype='application/json', content_type='application/json', )
        else:
            return await func(*args, **kwargs)
    return decorator


def user_auth_required(func: Callable):
    """
    Decorator to require user authentication.
    """
    @wraps(func)
    async def decorator(*args, **kwargs):
        headers = request.headers
        auth_hash = headers.get('Auth-Hash', None)
        user_id = headers.get('User-Id', None)
        if (user_id is None and auth_hash is None) or (user_id is None or auth_hash is None):
            return_data = await api_response(success=False, op=func.__name__, msg='Missing Authentication Headers.')
            return Response(return_data, status=406, mimetype='application/json', content_type='application/json', )
        try:
            serializer = URLSafeTimedSerializer(secret_key=config.APP_TEMP_SECRET_KEY)
            age = config.LAST_UPDATE - (time.time() + 120)
            deserialized = await decode(serializer.loads(auth_hash, max_age=age, salt=str(user_id)))
            # noinspection PyBroadException
            try:
                user = await get_users(user_id=deserialized['user_id'])
            except Exception:
                user = None
            if user is None or str(deserialized['user_id']) != str(user_id) or \
                    str(deserialized['SSID']) != str(config.APP_SECRET_KEY):
                raise BadTimeSignature('')
        except (SignatureExpired, BadTimeSignature):
            return_data = await api_response(False, op=func.__name__, msg='User access not authenticated.',
                                             error='#USER_ACCESS_NOT_AUTHENTICATED')
            return Response(return_data, status=401, mimetype='application/json', content_type='application/json', )

        return await func(*args, **kwargs)
    return decorator


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
            return Response(return_data, status=415, mimetype='application/json', content_type='application/json', )
        else:
            return await func(*args, **kwargs)
    return decorator


async def error_response(op: str, stack_trace: str)-> Response:
    """
    Utility function to return an API response containing the error that happened
    :param op: The operation that failed
    :param stack_trace: The stack trace of the exception
    :return: Response with http status 500 and additional JSON data
    """
    return_data = await api_response(success=False, op=op, msg="Internal Server Error",
                                     stack_trace=stack_trace)
    return Response(return_data, status=500, mimetype='application/json', content_type='application/json', )


class request_limit:
    """
    Object made to limit the requests per time to live
    """

    def __init__(self, max_requests, ttl=60*5):
        self._data = SuperDict({})
        self.max_requests = max_requests
        self.ttl = ttl
        thread = Thread(target=self.__collector, daemon=True)
        thread.start()

    def __call__(self, func):
        @wraps(func)
        async def decorator(*args, **kwargs):
            headers = request.headers
            auth_hash = headers.get('Auth-Hash', None)
            user_id = headers.get('User-Id', None)
            if (user_id is None and auth_hash is None) or (user_id is None or auth_hash is None):
                return_data = await api_response(success=False, op=func.__name__, msg='Missing Authentication Headers.')
                return Response(return_data, status=406, mimetype='application/json', content_type='application/json', )

            try:
                serializer = URLSafeTimedSerializer(secret_key=config.APP_TEMP_SECRET_KEY)
                age = config.LAST_UPDATE - (time.time() + 120)
                deserialized = await decode(serializer.loads(auth_hash, max_age=age, salt=str(user_id)))
                # noinspection PyBroadException
                try:
                    user = await get_users(user_id=deserialized['user_id'])
                except Exception:
                    user = None
                if user is None or str(deserialized['user_id']) != str(user_id) or \
                        str(deserialized['SSID']) != str(config.APP_SECRET_KEY):
                    raise BadTimeSignature('')
            except (SignatureExpired, BadTimeSignature):
                return_data = await api_response(False, op=func.__name__, msg='User access not authenticated.',
                                                 error='#USER_ACCESS_NOT_AUTHENTICATED')
                return Response(return_data, status=401, mimetype='application/json', content_type='application/json', )
            else:
                now = time.time()
                if auth_hash not in self._data:
                    u = {
                        'start': now,
                        'ttl': self.ttl,
                        'request_quantity': 1
                    }
                    self._data[auth_hash] = SuperDict(u)
                cached_request = self._data[auth_hash]
                if cached_request.request_quantity > self.max_requests and \
                        now < (cached_request.start + cached_request.ttl):
                    return_data = await api_response(False, op=func.__name__, msg='Request limit reached.',
                                                     wait=int((cached_request.start + cached_request.ttl) - now))
                    return Response(return_data, status=429, mimetype='application/json',
                                    content_type='application/json', )
                else:
                    if now > (cached_request.start + cached_request.ttl):
                        cached_request.start = now
                        cached_request.request_quantity = 0

                    cached_request.request_quantity += 1

                    return await func(*args, **kwargs)
        return decorator

    def __collector(self):
        """
        A collector that cleans the cached data every 30 minutes
        """
        while True:
            del_keys = []
            for k, v in self._data.items():
                now = time.time()
                if now > v.start + v.ttl:
                    del_keys.append(k)

            for key in del_keys:
                del self._data[key]
            time.sleep((60*30))
