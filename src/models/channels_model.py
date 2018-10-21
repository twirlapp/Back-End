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

from src.models import fields, MongoModel, EmbeddedMongoModel, connect
from pymongo import write_concern as wc, read_concern as rc, IndexModel, ReadPreference
from re import compile
from .user_model import User
from .config import *

connect(f'{MONGO_URI}/channels', alias='Channels', ssl=USE_SSL, username=DB_ADMIN_USERNAME, password=DB_ADMIN_PASSWORD)

username_pattern = compile('[\w\d_]+')


def validate_username(username: str)-> None:
    if not username_pattern.match(username):
        raise ValueError('username is Invalid!')


class ChannelAdmin(EmbeddedMongoModel):
    uid = fields.ReferenceField(User, on_delete=fields.ReferenceField.CASCADE, verbose_name='user_id',
                                mongo_name='userId', required=True)
    admin_since = fields.DateTimeField(verbose_name='admin_since', mongo_name='adminJoinDate', required=True)
    can_post = fields.BooleanField(verbose_name='admin_can_post', mongo_name='adminCanPost',
                                   default=True)
    can_edit_others = fields.BooleanField(verbose_name='admin_can_edit_others', mongo_name='adminCanEditOthers',
                                          default=False)
    can_delete_others = fields.BooleanField(verbose_name='admin_can_delete_others', mongo_name='adminCanDeleteOthers',
                                            default=False)
    can_update_channel_info = fields.BooleanField(verbose_name='admin_can_update_channel_info',
                                                  mongo_name='adminCanUpdateChannelInfo', default=False)


class Channel(MongoModel):
    _id = fields.BigIntegerField(required=True, primary_key=True)
    chid = fields.BigIntegerField(required=True, verbose_name='channel_id', mongo_name='channelId')
    title = fields.CharField(verbose_name='channel_title', mongo_name='channelTitle', default='')
    description = fields.CharField(verbose_name='channel_description', mongo_name='channelDescription', default=None)
    username = fields.CharField(verbose_name='channel_username',
                                mongo_name='channelUsername', default=None, validators=[validate_username])
    private_link = fields.CharField(verbose_name='channel_private_link', mongo_name='channelPrivateLink',
                                    default=None)
    photo_id = fields.CharField(verbose_name='channel_photo', mongo_name='channelPhoto', default=None)
    creator = fields.ReferenceField(User, on_delete=fields.ReferenceField.CASCADE,
                                    verbose_name='channel_creator', mongo_name='channelCreator', required=True)
    authorized_admins = fields.EmbeddedDocumentListField(ChannelAdmin,
                                                         verbose_name='authorized_channel_admins',
                                                         mongo_name='channelAdmins')
    is_deleted = fields.BooleanField(verbose_name='channel_is_deleted', mongo_name='isDeleted', default=False)
    added_date = fields.DateTimeField(verbose_name='channel_added_date', mongo_name='joinDate', required=True)
    deleted_date = fields.DateTimeField(verbose_name='user_deleted_date', mongo_name='deletedDate', default=None)

    class Meta:
        connection_alias = 'Channels'
        collection_name = 'channels'
        cascade = True
        write_concern = wc.WriteConcern(j=True)
        read_preference = ReadPreference.NEAREST
        read_concern = rc.ReadConcern(level='majority')
        indexes = [
            IndexModel('channelUsername', name='channelUsernameIndex', unique=True, sparse=True),
            IndexModel('channelId', name='channelIdIndex', unique=True, sparse=True),
            IndexModel('channelCreator', name='channelCreatorIndex', unique=True, sparse=True),
            IndexModel('channelAdmins', name='channelAdminsIndex', unique=True, sparse=True)
        ]
        ignore_unknown_fields = True
