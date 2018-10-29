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

from ..models.comments_model import Comment, CommentReply, CommentRank, UserGivenCommentRank
from ..models.user_models import User
from ..models.post_models import PostModel
from .user_controllers import get_users
from .post_controllers import get_posts
from ..utils.security import id_generator
from typing import Union
from pymongo import DESCENDING
from math import sqrt
import datetime


def add_comment(user_model: User = None, user_id: int = None, post_model: PostModel = None, post_id: int = None, *,
                comment: str, reply_to_model: Comment = None, reply_to_id: str = None)-> Union[Comment, CommentReply]:
    """
    Adds a comment to the database.
    :param user_model: User reference model to identify the user
    :param user_id: Telegram's user ID. Used only if `user_model` is None
    :param post_model: Post reference model to identify the post in which this comment belongs
    :param post_id: Post identifier on the database. Used only if `post_model` is None
    :param comment: The comment in unicode text
    :param reply_to_model: A [Comment] instance this comment will be replying
    :param reply_to_id: An identifier of a comment this comment will be replying. Used only if `reply_to_model` is None
    :return: A [Comment] or [CommentReply] instance of the comment created.
    """
    try:
        user = user_model if user_model is not None else get_users(user_id=user_id)
        post = post_model if post_model is not None else get_posts(post_id=post_id)
        try:
            if reply_to_model is not None or reply_to_id is not None:
                reply_to = reply_to_model if reply_to_model is not None else get_comments(comment_id=reply_to_id)
            else:
                reply_to = None
        except Comment.DoesNotExist:
            reply_to = None

        _id = post.post_id + id_generator(16, use_hex=True)
        comment_rank = CommentRank(
            rank_up_count=0,
            rank_down_count=0,
        )

        if reply_to is not None:
            _id = reply_to.comment_id + id_generator(12, use_hex=True)
            comment = CommentReply(
                _id=_id,
                comment_id=_id,
                user_id=user,
                created_date=datetime.datetime.utcnow(),
                reply_to=reply_to,
                comment=comment,
                belongs_to=post
            )
        else:
            comment = Comment(
                _id=_id,
                comment_id=_id,
                user_id=user,
                created_date=datetime.datetime.utcnow(),
                rank=comment_rank,
                comment=comment,
                belongs_to=post
            )
        if comment.is_valid():
            comment.save(full_clean=True)
            return comment
        else:
            raise comment.full_clean()

    except User.DoesNotExist:
        raise
    except PostModel.DoesNotExist:
        raise


def edit_comment(comment_model: Union[Comment, CommentReply] = None,
                 comment_id: str = None, *, new_comment: str)-> Union[Comment, CommentReply]:
    """
    Edits a comment in the database.
    :param comment_model: Comment reference model to identify the comment
    :param comment_id: An identifier of the comment. Used only if `comment_model` is None
    :param new_comment: The new unicode text to replace this comment
    :return: A [Comment] or [CommentReply] instance
    """
    try:
        comment = comment_model if comment_model is not None else get_comments(comment_id=comment_id)
        comment.comment = new_comment
        if comment.is_valid():
            comment.save(full_clean=True)
            return comment
        else:
            raise comment.full_clean()
    except Comment.DoesNotExist:
        raise


def delete_comment(comment_model: Comment = None, comment_id: str = None)-> bool:
    """
    Deletes the comment, and all the associated replies and ranking votes, or a reply.
    :param comment_model: Comment reference model to identify the comment
    :param comment_id: An identifier of the comment. Used only if `comment_model` is None
    :return: True if deleted, False if the comment was never added, or the Exception raised by the data validation
             (less likely to happen).
    """
    try:
        comment = comment_model if comment_model is not None else get_comments(comment_id=comment_id)
        if comment.reply_to is None:
            try:
                replies = CommentReply.objects.raw({'replyTo': comment.comment_id, 'isDeleted': False})
                replies.update({'$set': {'deletedDate': datetime.datetime.utcnow(), 'isDeleted': True}})
            except CommentReply.DoesNotExist:
                pass
        comment.is_deleted = True
        comment.deleted_date = datetime.datetime.utcnow()
        if comment.is_valid():
            comment.save(full_clean=True)
            return True
    except Comment.DoesNotExist:
        return False


def get_comments(comment_id: str = None,
                 post_model: PostModel = None,
                 post_id: str = None,
                 user_model: User = None,
                 user_id: int = None)-> Union[Comment, None]:
    """
    Gets a comment, or the comments from an user.
    :param comment_id: An identifier of the comment
    :param post_model: Post reference model to identify the post in which this comment belongs. Used to match all the
                       comments from a post
    :param post_id: Post identifier on the database. Used only if `post_model` is None
    :param user_model: User reference model to identify the user. Used to match all the comments from a post that
                       belongs to an user. There must be a post to filter by user.
    :param user_id: Telegram's user ID. Used only if `user_model` is None
    :return: [Comment] instance containing a comment, or an iterable of comments, or None
    """
    try:
        if comment_id is not None:
            comments = Comment.objects.get({'commentId': comment_id, 'replyTo': None})
        else:
            post = post_model if post_model is not None else get_posts(post_id=post_id)
            if user_model is not None or user_id is not None:
                user = user_model if user_model is not None else get_users(user_id=user_id)
                comments = Comment.objects.raw({'belongsTo': post.post_id, 'userId': user.uid, 'replyTo': None})
            else:
                comments = Comment.objects.raw({'belongsTo': post.post_id, 'replyTo': None})
        return comments.sort_by([('rankPosition', DESCENDING)])
    except Comment.DoesNotExist:
        return None
    except PostModel.DoesNotExist:
        raise
    except User.DoesNotExist:
        raise


def get_replies(comment_model: Comment = None,
                comment_id: str = None)-> Union[CommentReply, None]:
    """
    Gets the replies to a given comment.
    :param comment_model: A [Comment] model instance of a comment
    :param comment_id: An identifier of a comment. Only used if `comment_model` is None.
    :return: An iterable of [CommentReply] containing all replies to a comment.
    """
    try:
        comment = comment_model if comment_model is not None else get_comments(comment_id=comment_id)
        replies = CommentReply.objects.raw({'replyTo': comment.comment_id})
        return replies.sort([('createdDate', DESCENDING)])
    except Comment.DoesNotExist:
        raise
    except CommentReply.DoesNotExist:
        return None


def rank_comment(user_model: User = None, user_id: int = None, *, rank_type: str = 'up',
                 comment_model: Union[Comment, CommentReply] = None,
                 comment_id: str = None)-> Union[UserGivenCommentRank, None]:
    """
    Gives a rank to a comment. Can give an up or a down. On give a rank, the comment position is re-calculated and
    updated.
    :param user_model: User reference model to identify the user
    :param user_id: Telegram's user ID. Used only if `user_model` is None
    :param rank_type: The type of rank an user is giving. It can be either 'up', 'down' or 'unrank'
    :param comment_model: Comment reference model to identify the comment
    :param comment_id: An identifier of the comment. Used only if `comment_model` is None
    :return: [UserGivenCommentRank] instance of the rank an user gave.
    """
    try:
        user = user_model if user_model is not None else get_users(user_id=user_id)
        comment = comment_model if comment_model is not None else get_comments(comment_id=comment_id)
        try:
            user_rank = UserGivenCommentRank.objects.get({'userId': user.uid, 'commentId': comment.comment_id})
            if user_rank.rank_type != rank_type:
                if rank_type == 'unrank':
                    if user_rank.rank_type == 'up':
                        comment.rank.rank_up_count -= 1
                    elif user_rank.rank_type == 'down':
                        comment.rank.rank_down_count -= 1
                else:
                    if user_rank.rank_type == 'up':
                        if comment.rank.rank_up_count > 0:
                            comment.rank.rank_up_count -= 1
                        comment.rank.rank_down_count += 1
                    elif user_rank.rank_type == 'down':
                        if comment.rank.rank_down_count > 0:
                            comment.rank.rank_down_count -= 1
                        comment.rank.rank_up_count += 1
                    user_rank.rank_type = rank_type
                    user_rank.rank_date = datetime.datetime.utcnow()

        except UserGivenCommentRank.DoesNotExist:
            user_rank = UserGivenCommentRank(
                user_id=user,
                comment_ranked=comment,
                rank_type=rank_type,
                rank_date=datetime.datetime.utcnow()

            )
            if rank_type == 'up':
                comment.rank.rank_up_count += 1
            elif rank_type == 'down':
                comment.rank.rank_down_count += 1

        rank_position = confidence(comment.rank.rank_up_count, comment.rank.rank_down_count)

        comment.rank_position = rank_position
        comment.save()

        if rank_type == 'unrank':
            user_rank.delete()
            return None
        else:
            user_rank.save(full_clean=True)
            return user_rank

    except Comment.DoesNotExist:
        raise
    except User.DoesNotExist:
        raise


# Pure Python Implementation of the Wilson Score Interval, to calculate the ranking of comments.
# The algorithm can be seen implemented on reddit, as followed:
# https://github.com/reddit-archive/reddit/blob/master/r2/r2/lib/db/_sorts.pyx
# The explanation of the Wilson Score Interval can be found here:
# http://www.evanmiller.org/how-not-to-sort-by-average-rating.html


def _confidence(ups, downs):
    n = ups + downs

    if n == 0:
        return 0

    z = 1.281551565545  # 80% confidence
    p = float(ups) / n

    left = p + 1/(2*n)*z*z
    right = z*sqrt(p*(1-p)/n + z*z/(4*n*n))
    under = 1+1/n*z*z

    return (left - right) / under


def confidence(ups, downs):
    if ups + downs == 0:
        return 0
    else:
        return _confidence(ups, downs) * 100
