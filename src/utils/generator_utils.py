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

import random
from string import ascii_letters, digits, hexdigits
from hashlib import sha256, sha512, md5


def id_generator(size: int, start_num: int = None, *, use_hex=False)-> str:
    """
    Generates an ID, with `size` characters, randomly picked. An additional `start_num` can be used to be the first
    characters on the result string. The return string will never be bigger than `size`, so if `start_num` has already
    `size` characters, `start_num` is returned in a random state.
    :param size: The size of the ID to be generated
    :param start_num: (Optional) An integer number to be the first characters in the result string
    :param use_hex: If True, will use hex digits instead of ascii letters + digits
    :return: `size`-sized string
    """
    _str = ''
    if start_num is not None:
        _start_num = str(start_num)
        if len(_start_num) >= size:
            _str += _str.join(random.sample(_start_num, k=size)[:size])
            return _str
        else:
            _str += _start_num

    population = ascii_letters + digits
    if use_hex:
        population = hexdigits

    _str_size = len(_str)
    return _str + ''.join(random.choices(population, k=(size - _str_size)))


def hash_generator(string: str, hash_type: str = 'sha256')-> str:
    """
    Small helper to generate Hashes. Supported hashes are sha256, sha512 and md5
    :param string: String to be hashed
    :param hash_type: Type of the hash algorithm to be adopted. Defaults to 'sha256'
    :return: hex of the hash
    """

    if hash_type == 'md5':
        hashed = md5(string.encode('utf-8'))
    elif hash_type == 'sha512':
        hashed = sha512(string.encode('utf-8'))
    else:
        hashed = sha256(string.encode('utf-8'))

    return hashed.hexdigest()
