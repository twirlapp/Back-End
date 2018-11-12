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

import ujson
from typing import Awaitable, Union, List
from .function_handlers import to_async


async def encode(*args, **kwargs)-> Union[Awaitable, str]:
    """
    Receives data to be encoded from Python objects to JSON
    :param args:
    :param kwargs:
    :return: An awaitable encoding
    """
    encoder = to_async(ujson.dumps)
    return await encoder(*args, **kwargs)


async def decode(*args, **kwargs)-> Union[Awaitable, dict]:
    """
    Receives data to be decoded from JSON to Python objects
    :param args:
    :param kwargs:
    :return: An awaitable decoding
    """
    decoder = to_async(ujson.loads)
    return await decoder(*args, **kwargs)


class SuperDict(dict):
    """
    A helper class to parse normal Python dicts as an object, so it's keys are obtainable using attributes.
    """
    __dict__ = {}

    def __init__(self, data_dict: dict, rcall=0):
        """
        :param data_dict: Python dict to be used in here.
        """
        super().__init__(data_dict)
        for k, v in data_dict.items():
            if isinstance(v, dict):
                if rcall < 5:
                    v = SuperDict(v, rcall=rcall+1)
            elif isinstance(v, list):
                if rcall < 5:
                    _ = rcall + 1
                    v = [SuperDict(i, _) for i in v]
            self[k] = v

    def __getattr__(self, item):
        return self.get(item, None)

    def __setattr__(self, key, value):
        if isinstance(value, dict):
            value = SuperDict(value, rcall=1)
        self[key] = value

    def __delattr__(self, item):
        if item in self:
            del self[item]


async def api_response(success: bool, op: str, msg: str = None, **kwargs)-> Union[Awaitable, str]:
    """
    Helper to create responses to all the API methods.
    :param success: If the request was successful
    :param op: The operation that happened
    :param msg: An optional message to be passed to the response
    :param kwargs: Other arguments to be passed to the response
    :return: JSON serialized dict object
    """
    result = {
        'success': success,
        'op': op
    }
    if msg is not None:
        result['msg'] = msg
    for k, v in kwargs.items():
        result[k] = v

    return await encode(result)


async def api_request(data: str)-> Union[SuperDict, List[SuperDict]]:
    """
    Helper to parse request JSON strings to a [SuperDict] instance
    :param data: The serialized JSON data
    :return: [SuperDict] instance of the parsed data
    """
    # noinspection PyBroadException
    try:
        deserialized_data = await decode(data)
        return SuperDict(deserialized_data)
    except Exception:
        return SuperDict({})
