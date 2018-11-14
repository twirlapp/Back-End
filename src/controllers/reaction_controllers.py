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

from ..models.user_models import User
from ..models.post_models import PostModel
from ..utils.function_handlers import to_async, temp_lru_cache
from ..models.reactions_model import Reaction, ReactionObj, UserReaction
from typing import List, Union, Dict
import datetime
from functools import lru_cache


__CACHE = temp_lru_cache(max_size=4096)


@lru_cache(maxsize=2048)
def create_reaction(reactions_list: List[str] = None,
                    reactions_map: List[Union[Dict[str, str], Dict[str, int]]] = None) -> Union[Reaction, None]:
    """
    Creates a reaction Model.
    :param reactions_list: A list of emojis to create a reaction model
    :param reactions_map: A dict of emojis and starter counts to create a reaction model
    :return:
    """
    _reactions = None
    if reactions_list is not None:
        _reactions = []
        for emoji in reactions_list:
            _reaction_obj = ReactionObj(
                emoji=emoji,
                count=0
            )
            _reactions.append(_reaction_obj)
    elif reactions_map is not None:
        _reactions = []
        for _reaction_dict in reactions_map:
            emoji = _reaction_dict.get('emoji', None)
            count = _reaction_dict.get('count', 0)
            if emoji is not None:
                _reaction_obj = ReactionObj(
                    emoji=emoji,
                    count=count
                )
                _reactions.append(_reaction_obj)

    if _reactions is not None:
        # _id = post.post_id + id_generator(4, use_hex=True)
        reaction_obj = Reaction(
            total_count=0,
            reactions=_reactions
        )
        return reaction_obj
    return _reactions


async def user_reaction(user_model: User = None, user_id: int = None, *,
                        post_id: str, index: int)-> Union[UserReaction, None]:
    """
    Adds or edits a user reaction in the database.
    :param user_model: user reference model to identify the reaction.
    :param user_id: Telegram's user ID. Used only if `user_model` is None
    :param post_id: The identifier of the post
    :param index: The index of the reaction emoji the user reacted.
    :return: [UserReaction] instance or None proving the success of the transaction. If None, it means the reaction
             was simply removed.
    """
    from .post_controllers import get_posts, __POST_CACHE
    try:
        user = user_model.uid if user_model is not None else user_id
        post = await get_posts(post_id=post_id)
        if post.reactions is None:
            raise IndexError('')
        now = datetime.datetime.utcnow()
        get = to_async(UserReaction.objects.get)
        try:
            _usr_reaction = await get({'userId': user, 'postId': post.post_id})
            _old_index = _usr_reaction.reaction_index
            _usr_reaction.reaction_index = index
            _usr_reaction.reaction_date = now
            post.reactions.reactions[_old_index] -= 1
            post.reactions.total_count -= 1
            if index == _old_index:
                await remove_user_reaction(user_id=_usr_reaction.user_id, post_id=_usr_reaction.post)
                return None
        except UserReaction.DoesNotExist:
            _usr_reaction = UserReaction(
                user_id=user,
                post=post,
                reaction_index=index,
                reaction_date=now
            )
        except IndexError:
            raise
        if _usr_reaction.is_valid():
            try:
                post.reactions.reactions[index] += 1
                post.reactions.total_count += 1
                reaction_save = to_async(_usr_reaction.save)
                await reaction_save(full_clean=True)
                save_post = to_async(post.save)
                await save_post()
                __POST_CACHE[post.post_id] = post
                return _usr_reaction
            except IndexError:
                raise
        else:
            raise _usr_reaction.full_clean()

    except PostModel.DoesNotExist:
        raise
    except IndexError:
        raise


async def remove_user_reaction(user_model: User = None, user_id: int = None, *, post_id: str)-> bool:
    """
    Removes a reaction given by an user.
    :param user_model: user reference model to identify the reaction.
    :param user_id: Telegram's user ID. Used only if `user_model` is None
    :param post_id: The identifier of the post
    :return: True if deleted, False if the user was never added, or the Exception raised by the data validation
             (less likely to happen).
    """
    from .post_controllers import get_posts
    try:
        user = user_model.uid if user_model is not None else user_id
        post = await get_posts(post_id=post_id)
        save = to_async(post.save)
        _usr_reaction = UserReaction.objects.get({'userId': user, 'postId': post_id})
        delete = to_async(_usr_reaction.delete)
        post.reactions.reactions[_usr_reaction.reaction_index] -= 1
        post.reactions.total_count -= 1
        await save()
        await delete()
        return True
    except UserReaction.DoesNotExist:
        return False
