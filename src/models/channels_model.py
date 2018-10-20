from src.models import fields, MongoModel, EmbeddedMongoModel, connect
from pymongo import write_concern as wc, read_concern as rc, IndexModel, ReadPreference
from re import compile
from .user_model import User

connect('mongodb://localhost:27017/channels', alias='Channels')
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
