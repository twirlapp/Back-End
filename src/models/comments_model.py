from src.models import fields, MongoModel, EmbeddedMongoModel, connect
from pymongo import write_concern as wc, read_concern as rc, IndexModel, ReadPreference
from .user_model import User

connect('mongodb://localhost:27017/comments', alias='Comments')


class CommentRank(EmbeddedMongoModel):
    rank_up_count = fields.IntegerField(verbose_name='rank_up_count', mongo_name='upCount', min_value=0,
                                        default=0)
    rank_down_count = fields.IntegerField(verbose_name='rank_down_count', mongo_name='downCount', min_value=0,
                                          default=0)


class Comment(MongoModel):
    _id = fields.CharField(required=True, primary_key=True)
    user_id = fields.ReferenceField(User, on_delete=fields.ReferenceField.CASCADE,
                                    verbose_name='user_id', mongo_name='userId', required=True)
    comment = fields.CharField(verbose_name='comment', mongo_name='comment', required=True, max_length=140)
    comment_id = fields.CharField(verbose_name='comment_id', mongo_name='commentId', required=True)
    created_date = fields.DateTimeField(required=True, verbose_name='comment_created_date', mongo_name='createdDate')
    is_deleted = fields.BooleanField(verbose_name='is_deleted', mongo_name='isDeleted', default=False)
    deleted_date = fields.DateTimeField(verbose_name='comment_deleted_date', mongo_name='deletedDate', default=None)
    reply_to = fields.CharField(verbose_name='reply_to', mongo_name='replyTo', default=None)
    rank = fields.EmbeddedDocumentField(CommentRank, verbose_name='rank', mongo_name='rank', required=True)

    class Meta:
        connection_alias = 'Comments'
        collection_name = 'comments'
        cascade = True
        write_concern = wc.WriteConcern(j=True)
        read_preference = ReadPreference.NEAREST
        read_concern = rc.ReadConcern(level='majority')
        indexes = [
            IndexModel('userId', name='commentUserIdIndex', unique=True, sparse=True),
            IndexModel('commentId', name='commentIdIndex', unique=True, sparse=True)
        ]
        ignore_unknown_fields = True


class CommentReply(Comment):
    reply_to = fields.ReferenceField(Comment, on_delete=fields.ReferenceField.CASCADE,
                                     verbose_name='reply_to', mongo_name='replyTo')


class UserGivenCommentRank(MongoModel):
    user_id = fields.ReferenceField(User, on_delete=fields.ReferenceField.DO_NOTHING, required=True,
                                    verbose_name='user_id', mongo_name='userId')
    comment_ranked = fields.ReferenceField(Comment, on_delete=fields.ReferenceField.CASCADE, required=True,
                                           verbose_name='comment_ranked_id', mongo_name='commentId')
    rank_type = fields.CharField(required=True, choices=('up', 'down'), default='up',
                                 verbose_name='rank_type', mongo_name='rankType')
    rank_date = fields.DateTimeField(required=True, verbose_name='rank_date', mongo_name='rankDate')

    class Meta:
        connection_alias = 'Comments'
        collection_name = 'comment_ranks'
        cascade = True
        write_concern = wc.WriteConcern(j=True)
        read_preference = ReadPreference.NEAREST
        read_concern = rc.ReadConcern(level='majority')
        indexes = [
            IndexModel('userId', name='rankUserIdIndex', unique=True, sparse=True),
            IndexModel('commentId', name='rankCommentIdIndex', unique=True, sparse=True),
            IndexModel('rankType', name='rankTypeIndex', unique=True, sparse=True)
        ]
        ignore_unknown_fields = True
