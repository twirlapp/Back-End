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

from ..utils.security import id_generator, hash_generator
from pymodm import connect, MongoModel, fields, EmbeddedMongoModel
from pymongo import write_concern as wc, read_concern as rc, IndexModel, ReadPreference
from ..models.config import *
from typing import Union
import datetime
import bcrypt
from functools import lru_cache

connect(f'{MONGO_URI}/app', alias='Application', ssl=USE_SSL, username=DB_ADMIN_USERNAME, password=DB_ADMIN_PASSWORD)


class AppManager(EmbeddedMongoModel):
    first_name = fields.CharField(required=True, verbose_name='manager_first_name', mongo_name='firstName')
    last_name = fields.CharField(required=True, verbose_name='manager_last_name', mongo_name='lastName')
    phone_number = fields.CharField(verbose_name='manager_phone_number', mongo_name='phoneNumber', default='')
    email = fields.EmailField(required=True, verbose_name='manager_email', mongo_name='email')


class Application(MongoModel):
    _id = fields.CharField(required=True, primary_key=True)
    app_id = fields.CharField(required=True, verbose_name='app_id', mongo_name='appId')
    app_hash = fields.CharField(required=True, verbose_name='app_hash', mongo_name='appHash')
    app_secure = fields.BinaryField(required=True, verbose_name='app_secure', mongo_name='appCrypt')
    app_manager = fields.EmbeddedDocumentField(AppManager, required=True, verbose_name='app_manager_info',
                                               mongo_name='appManager')
    created_date = fields.DateTimeField(verbose_name='app_created_date', mongo_name='createdDate', required=True)
    app_is_valid = fields.BooleanField(required=True, verbose_name='app_is_valid', mongo_name='isValid', default=True)
    valid_until = fields.DateTimeField(required=True, verbose_name='app_valid_until', mongo_name='validUntil')
    is_deleted = fields.BooleanField(verbose_name='app_is_deleted', mongo_name='isDeleted', default=False)
    deleted_date = fields.DateTimeField(verbose_name='user_deleted_date', mongo_name='deletedDate', default=None)

    class Meta:
        connection_alias = 'Application'
        collection_name = 'registeredApps'
        cascade = True
        write_concern = wc.WriteConcern(j=True)
        read_preference = ReadPreference.NEAREST
        read_concern = rc.ReadConcern(level='majority')
        indexes = [
            IndexModel('appId', name='appIdIndex', unique=True, sparse=True),
            IndexModel('appHash', name='appHashIndex', unique=True, sparse=True),
            IndexModel('appCrypt', name='appCryptIndex', unique=True, sparse=True),
            IndexModel('createdDate', name='createdDateIndex', sparse=True),
            IndexModel('validUntil', name='validUntilIndex', sparse=True),
            IndexModel('appManager.email', name='managerEmailIndex', sparse=True, unique=True)
        ]
        ignore_unknown_fields = True


class __ApplicationAdministration(MongoModel):
    _id = fields.IntegerField(required=True, primary_key=True, default=0)
    created_apps = fields.BigIntegerField(required=True, verbose_name='created_apps', mongo_name='createdApps',
                                          min_value=0, default=0)

    class Meta:
        connection_alias = 'Application'
        collection_name = 'appsMeta'
        cascade = True
        write_concern = wc.WriteConcern(j=True)
        read_preference = ReadPreference.NEAREST
        read_concern = rc.ReadConcern(level='majority')
        ignore_unknown_fields = True


def create_app(manager_first_name: str, manager_last_name: str,
               manager_email: str, password: str,
               manager_phone_number: str = None, new_password: str = None) -> Application:
    """
    Creates an application and adds it to the database.
    :param manager_first_name: The first name of the app manager
    :param manager_last_name: The last name of the app manager
    :param manager_email: The E-mail address of the app manager
    :param manager_phone_number: (Optional) the phone number of the app manager
    :param password: old password to change the app authorization
    :param new_password: New password to change the app authorization
    :return: [Application] instance of the app added to the database.
    """

    manager = AppManager(
        first_name=manager_first_name,
        last_name=manager_last_name,
        email=manager_email
    )
    if manager_phone_number is not None:
        manager.phone_number = manager_phone_number

    _app = get_app(manager_email=manager_email)

    if _app is not None:
        _app.manager = manager

        # Needed to change the Application state
        if not bcrypt.checkpw((password + _app.app_hash).encode(), _app.app_secure):
            raise ValueError('Password doesn\'t match.')

        _app.valid_until = datetime.datetime.utcnow() + datetime.timedelta(days=365)
        _app.app_is_valid = True
        if new_password is not None:
            new_salt = bcrypt.gensalt()
            _app.app_hash = hash_generator(_app.app_hash + new_salt.decode())
            _app.app_secure = bcrypt.hashpw((new_password + _app.app_hash).encode(), new_salt)
            is_app_authorized.cache_clear()
        _app.save()
        return _app
    else:
        try:
            _administration = __ApplicationAdministration.objects.get({'_id': 0})
        except __ApplicationAdministration.DoesNotExist:
            _administration = __ApplicationAdministration(_id=0, created_apps=0)

        _administration.created_apps += 1
        _administration.save()
        salt = bcrypt.gensalt()
        _id = id_generator(16, start_num=_administration.created_apps, use_hex=True)
        _hash = hash_generator(_id + salt.decode())
        _secure_key = bcrypt.hashpw((password + _hash).encode(), salt)
        _now = datetime.datetime.utcnow()
        _app = Application(
            _id=_id,
            app_id=_id,
            app_hash=_hash,
            app_secure=_secure_key,
            app_manager=manager,
            created_date=_now,
            valid_until=_now + datetime.timedelta(days=365)
        )
        if _app.is_valid():
            _app.save(full_clean=True)
            return _app
        else:
            raise _app.full_clean()


def get_app(app_id: int=None, app_hash: str=None, manager_email=None)-> Union[Application, None]:
    """
    Gets the app from the database
    :param app_id: The unique Identifier of the app
    :param app_hash: The unique Hash of the app
    :param manager_email: The email of the manager.
    :return: [Application] instance of the app, or None
    """
    try:
        app = Application.objects.get({'$or': [{'appId': app_id},
                                               {'appHash': app_hash},
                                               {'appManager.email': manager_email}],
                                       'isDeleted': False})
        return app
    except Application.DoesNotExist:
        return None


@lru_cache(maxsize=32)
def is_app_authorized(app_hash: str)-> bool:
    """
    Checks if an app has authorization to use the API. Lazy but actually secure and functional approach.
    :param app_hash: The unique Hash of the app
    :return: True if the app is valid and authorized, False if the app doesn't exist / isn't authorized / isn't valid
    """
    app = get_app(app_hash=app_hash)
    if app is not None and app.app_is_valid:
        return True
    else:
        return False


def remove_app_authorization(app_id: int, app_hash: str)-> bool:
    """
    Removes authorization of an app
    :param app_id: The unique Identifier of the app
    :param app_hash: The unique Hash of the app
    :return: True if the app is no longer authorized, False if the app doesn't exist
    """
    app = get_app(app_id=app_id, app_hash=app_hash)
    if app is not None:
        app.app_is_valid = False
        app.save()
        return True
    else:
        return False


def _remove_app(app_id: int, app_hash: str)-> bool:
    """
    INTERNAL USE ONLY. Removes an app, by setting the deleted flag True.
    :param app_id: The unique Identifier of the app
    :param app_hash: The unique Hash of the app
    :return: True if the app is removed, False if the app never existed
    """
    app = get_app(app_id=app_id, app_hash=app_hash)
    if app is not None:
        app.is_deleted = True
        app.deleted_date = datetime.datetime.utcnow()
        app.save()
        return True
    else:
        return False


def remove_app(app_id: int, app_hash: str, password: str)-> bool:
    """
    Removes an app, with user authorization, by setting the deleted flag True.
    :param app_id: The unique Identifier of the app
    :param app_hash: The unique Hash of the app
    :param password: Password to give authorization for this procedure
    :return: True if the app is removed, False if the app never existed. Raise ValueError if there is no authorization.
    """
    app = get_app(app_id=app_id, app_hash=app_hash)
    if app is not None:
        if bcrypt.checkpw(password, app.app_secure):
            app.is_deleted = True
            app.deleted_date = datetime.datetime.utcnow()
            app.save()
            return True
        else:
            raise ValueError('Password doesn\'t match.')
    else:
        return False
