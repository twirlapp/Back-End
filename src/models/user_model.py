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

from src.models import fields, MongoModel, connect
from pymongo import write_concern as wc, read_concern as rc, IndexModel, ReadPreference
from re import compile
from .config import *

connect(f'{MONGO_URI}/users', alias='Users', ssl=USE_SSL, username=DB_ADMIN_USERNAME, password=DB_ADMIN_PASSWORD)
username_pattern = compile('[\w\d_]+')


def validate_username(username: str)-> None:
    if not username_pattern.match(username):
        raise ValueError('username is Invalid!')


class User(MongoModel):
    _id = fields.IntegerField(required=True, primary_key=True)
    uid = fields.IntegerField(required=True, verbose_name='user_id', mongo_name='userId')
    first_name = fields.CharField(verbose_name='user_first_name', mongo_name='firstName', default=None)
    last_name = fields.CharField(verbose_name='user_first_name', mongo_name='lastName', default=None)
    username = fields.CharField(verbose_name='user_username',
                                mongo_name='userUsername', default=None, validators=[validate_username])
    is_deleted = fields.BooleanField(verbose_name='user_is_deleted', mongo_name='isDeleted', default=False)
    join_date = fields.DateTimeField(verbose_name='user_join_date', mongo_name='joinedDate')
    deleted_date = fields.DateTimeField(verbose_name='user_deleted_date', mongo_name='deletedDate', default=None)

    class Meta:
        collection_alias = 'Users'
        collection_name = 'users'
        cascade = True
        write_concern = wc.WriteConcern(j=True)
        read_preference = ReadPreference.NEAREST
        read_concern = rc.ReadConcern(level='majority')
        indexes = [
            IndexModel('userUsername', name='usernameIndex', unique=True, sparse=True),
            IndexModel('userId', name='userIdIndex', unique=True, sparse=True)
        ]
        ignore_unknown_fields = True
