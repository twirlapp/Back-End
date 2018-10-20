from src.models import fields, MongoModel, connect
from pymongo import write_concern as wc, read_concern as rc, IndexModel, ReadPreference
from re import compile

connect('mongodb://localhost:27017/users', alias='Users')
username_pattern = compile('[\w\d_]+')


def validate_username(username: str)-> None:
    if not username_pattern.match(username):
        raise ValueError('username is Invalid!')


class User(MongoModel):
    _id = fields.BigIntegerField(required=True, primary_key=True)
    uid = fields.BigIntegerField(required=True, verbose_name='user_id', mongo_name='userId')
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
