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

# from ..models.post_models import PostModel
from ..models.user_models import User
from ..models.reactions_model import Reaction, ReactionObj, UserReaction
from typing import List, Union, Dict
# from ..utils.generator_utils import id_generator
import datetime


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


def remove_reaction(reaction_id: str = None, post_id: str = None)-> bool:
    """
    Remove a reaction from the database.
    :param reaction_id: The reaction identifier
    :param post_id: The post in which this reaction belongs. Only used if `reaction_id` is None
    :return: True if deleted, False if the user was never added, or the Exception raised by the data validation
             (less likely to happen).
    """
    try:
        if reaction_id is not None:
            reaction = get_reaction(reaction_id=reaction_id)
        elif post_id is not None:
            reaction = get_reaction(post_id=post_id)
        else:
            return False
        reaction.is_deleted = True
        reaction.deleted_date = datetime.datetime.utcnow()
        if reaction.is_valid():
            reaction.save(full_clean=True)
        else:
            raise reaction.full_clean()
    except Reaction.DoesNotExist:
        return False


def get_reaction(reaction_id: str = None, post_id: str = None)-> Union[Reaction, None]:
    """
    Gets a reaction from the database.
    :param reaction_id: The reaction identifier
    :param post_id: The post in which this reaction belongs. Only used if `reaction_id` is None
    :return: A [Reaction] instance, or None, if the reaction doesn't exist.
    """
    try:
        if reaction_id is not None:
            reaction = Reaction.objects.get({'reactionId': reaction_id, 'isDeleted': False})
        elif post_id is not None:
            reaction = Reaction.objects.get({'postId': post_id, 'isDeleted': False})
        else:
            reaction = None

        return reaction
    except Reaction.DoesNotExist:
        return None


def user_reaction(user_model: User = None, user_id: int = None, *, reaction_id: str, index: int)-> UserReaction:
    """
    Adds or edits a user reaction in the database.
    :param user_model: user reference model to identify the reaction.
    :param user_id: Telegram's user ID. Used only if `user_model` is None
    :param reaction_id: The identifier of the reaction
    :param index: The index of the reaction emoji the user reacted.
    :return: [UserReaction] instance proving the success of the transaction
    """
    try:
        user = user_model.uid if user_model is not None else user_id
        reaction = get_reaction(reaction_id=reaction_id)
        now = datetime.datetime.utcnow()

        try:
            _usr_reaction = UserReaction.objects.get({'userId': user, 'reactionId': reaction_id})
            _old_index = _usr_reaction.reaction_index
            _usr_reaction.reaction_index = index
            _usr_reaction.reaction_date = now
            reaction.reactions[_old_index] -= 1
            reaction.total_count -= 1
        except UserReaction.DoesNotExist:
            _usr_reaction = UserReaction(
                user_id=user,
                reaction_id=reaction,
                reaction_index=index,
                reaction_date=now
            )
        if _usr_reaction.is_valid():
            _usr_reaction.save(full_clean=True)
            reaction.reactions[index] += 1
            reaction.total_count += 1
            reaction.save()
            return _usr_reaction
        else:
            raise _usr_reaction.full_clean()

    except Reaction.DoesNotExist:
        raise


def remove_user_reaction(user_model: User = None, user_id: int = None, *, reaction_id: str)-> bool:
    """
    Removes a reaction given by an user.
    :param user_model: user reference model to identify the reaction.
    :param user_id: Telegram's user ID. Used only if `user_model` is None
    :param reaction_id: The identifier of the reaction
    :return: True if deleted, False if the user was never added, or the Exception raised by the data validation
             (less likely to happen).
    """
    try:
        user = user_model.uid if user_model is not None else user_id
        reaction = get_reaction(reaction_id=reaction_id)
        _usr_reaction = UserReaction.objects.get({'userId': user, 'reactionId': reaction_id})
        reaction.reactions[_usr_reaction.reaction_index] -= 1
        reaction.total_count -= 1
        reaction.save()
        _usr_reaction.delete()
        return True
    except UserReaction.DoesNotExist:
        return False
