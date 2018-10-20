from src.models import fields, MongoModel, EmbeddedMongoModel, connect
from pymongo import write_concern as wc, read_concern as rc, IndexModel, ReadPreference
from .post_models import _PostModel
from .user_model import User

connect('mongodb://localhost:27017/reactions', alias='Reactions')


class ReactionObj(EmbeddedMongoModel):
    emoji = fields.CharField(required=True, verbose_name='emoji', mongo_name='emoji')
    count = fields.IntegerField(required=True, verbose_name='reaction_count', mongo_name='count', min_value=0,
                                default=0)


class Reaction(MongoModel):
    """

    """
    _id = fields.CharField(required=True, primary_key=True)
    reaction_id = fields.CharField(required=True, verbose_name='reaction_id', mongo_name='reactionId')
    reactions = fields.EmbeddedDocumentListField(ReactionObj, verbose_name='reactions_list', mongo_name='reactions')
    post = fields.ReferenceField(_PostModel, on_delete=fields.ReferenceField.CASCADE,
                                 verbose_name='post_id', mongo_name='postId')
    total_count = fields.IntegerField(required=True, verbose_name='total_count', mongo_name='totalCount', min_value=0,
                                      default=0)
    created_date = fields.DateTimeField(required=True, verbose_name='reaction_created_date', mongo_name='createdDate')
    is_deleted = fields.BooleanField(verbose_name='post_is_deleted', mongo_name='isDeleted', default=False)
    deleted_date = fields.DateTimeField(verbose_name='post_deleted_date', mongo_name='deletedDate', default=None)

    class Meta:
        connection_alias = 'Reactions'
        collection_name = 'reactions'
        cascade = True
        write_concern = wc.WriteConcern(j=True)
        read_preference = ReadPreference.NEAREST
        read_concern = rc.ReadConcern(level='majority')
        indexes = [
            IndexModel('reactionId', name='reactionIdIndex', unique=True, sparse=True),
            IndexModel('postId', name='reactionPostIdIndex', unique=True, sparse=True)
        ]
        ignore_unknown_fields = True


class UserReaction(MongoModel):
    """

    """
    user_id = fields.ReferenceField(User, on_delete=fields.ReferenceField.DO_NOTHING, verbose_name='user_id',
                                    mongo_name='userId', required=True)
    reaction_id = fields.ReferenceField(Reaction, on_delete=fields.ReferenceField.CASCADE,
                                        verbose_name='reaction_id', mongo_name='reactionId', required=True)
    reaction_index = fields.IntegerField(required=True, verbose_name='reaction_index', mongo_name='reactionIndex',
                                         min_value=0, max_value=3)
    reaction_date = fields.DateTimeField(required=True, verbose_name='reaction_date', mongo_name='reactionDate')

    class Meta:
        connection_alias = 'Reactions'
        collection_name = 'user_reactions'
        cascade = True
        write_concern = wc.WriteConcern(j=True)
        read_preference = ReadPreference.NEAREST
        read_concern = rc.ReadConcern(level='majority')
        indexes = [
            IndexModel('userId', name='userReactionUserIdIndex', unique=True, sparse=True),
            IndexModel('reactionId', name='userReactionReactionIdIndex', unique=True, sparse=True),
            IndexModel('reactionIndex', name='userReactionReactionIndexIndex', unique=True, sparse=True)
        ]
        ignore_unknown_fields = True
