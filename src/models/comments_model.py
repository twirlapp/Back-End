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
from .user_model import User
from .post_models import PostModel
from .config import *

connect(f'{MONGO_URI}/comments', alias='Comments', ssl=USE_SSL, username=DB_ADMIN_USERNAME, password=DB_ADMIN_PASSWORD)


class CommentRank(EmbeddedMongoModel):
    rank_up_count = fields.IntegerField(verbose_name='rank_up_count', mongo_name='upCount', min_value=0,
                                        default=0)
    rank_down_count = fields.IntegerField(verbose_name='rank_down_count', mongo_name='downCount', min_value=0,
                                          default=0)


class Comment(MongoModel):
    _id = fields.CharField(required=True, primary_key=True)
    user_id = fields.ReferenceField(User, on_delete=fields.ReferenceField.CASCADE,
                                    verbose_name='user_id', mongo_name='userId', required=True)
    belongs_to = fields.ReferenceField(PostModel, on_delete=fields.ReferenceField.CASCADE,
                                       verbose_name='belongs_to_post', mongo_name='postReference', required=True)
    comment = fields.CharField(verbose_name='comment', mongo_name='comment', required=True, max_length=140)
    comment_id = fields.CharField(verbose_name='comment_id', mongo_name='commentId', required=True)
    created_date = fields.DateTimeField(required=True, verbose_name='comment_created_date', mongo_name='createdDate')
    is_deleted = fields.BooleanField(verbose_name='is_deleted', mongo_name='isDeleted', default=False)
    deleted_date = fields.DateTimeField(verbose_name='comment_deleted_date', mongo_name='deletedDate', default=None)
    reply_to = fields.CharField(verbose_name='reply_to', mongo_name='replyTo', default=None)
    rank = fields.EmbeddedDocumentField(CommentRank, verbose_name='rank', mongo_name='rank', required=True)
    rank_position = fields.FloatField(verbose_name='rank_position', mongo_name='rankPosition', default=0.0)

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
                                     verbose_name='reply_to', mongo_name='replyTo', required=True)


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
