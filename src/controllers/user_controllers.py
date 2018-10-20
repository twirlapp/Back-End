from ..models.user_model import User
import datetime
from typing import Union, List, Iterable


def add_user(user_id: int, *, first_name: object = None, last_name: object = None, username: object = None)-> User:
    """
    Adds users to the database. An user is either a channel owner or channel admin; normal Telegram users are not
    Stored.
    :param user_id: Telegram's user ID
    :param first_name: Telegram user's First Name
    :param last_name: Telegram user's Last Name
    :param username: Telegram user's username
    :return: [User] instance from the database
    """

    join_time = datetime.datetime.now()
    user = User(
        _id=user_id,
        uid=user_id,
        first_name=first_name,
        last_name=last_name,
        username=username,
        join_date=join_time
    )
    if user.is_valid():
        user.save(full_clean=True)
        return user
    else:
        raise user.full_clean()


def edit_user_info(user_id: int, *, first_name: str = None, last_name: str = None, username: str = None)-> User:
    """
    Helper to edit User Info in the database.
    :param user_id: Telegram's user ID
    :param first_name: Telegram user's First Name
    :param last_name: Telegram user's Last Name
    :param username: Telegram user's username
    :return: [User] updated instance from the database
    """

    try:
        user = User.objects.get({'userId': user_id})

        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if username is not None:
            user.username = username

        if user.is_valid():
            user.save(full_clean=True)
            return user
        else:
            raise user.full_clean()

    except User.DoesNotExist:
        return add_user(user_id=user_id, first_name=first_name, last_name=last_name, username=username)


def delete_user(user_id: int)-> bool:
    """
    Remove a user from the database, using it's Telegram's ID, by setting the deleted flag.
    :param user_id: Telegram's ID
    :return: True if deleted, False if the user was never added, or the Exception raised by the data validation
             (less likely to happen).
    """

    try:
        user = get_users(user_id=user_id)
        user.is_deleted = True
        user.deleted_date = datetime.datetime.now()

        if user.is_valid():
            user.save(full_clean=True)
            return True
        else:
            raise user.full_clean()

    except User.DoesNotExist:
        return False


def get_users(user_id: int = None, user_ids: List[int] = None)-> Union[User, Iterable[User]]:
    """
    Gets a single user, or an iterable array of users from the database. Required either `user_id` or `user_ids`
    :param user_id: (Optional) the Telegram's ID of a given user
    :param user_ids: (Optional) a list of Telegram IDs of given users
    :return: a single [User] instance, an iterable of [User] instances, or None, if either the params are None, or there
             are no database matches.
    """

    try:
        if user_id is not None:
            user = User.objects.get({'userId': user_id, 'isDeleted': False})
            return user
        elif user_ids is not None:
            users = User.object.search({'userId': {'$in': user_ids}, 'isDeleted': False})
            return users
        else:
            raise User.DoesNotExist
    except User.DoesNotExist:
        raise
