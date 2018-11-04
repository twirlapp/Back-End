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

from pymodm import fields, MongoModel, EmbeddedMongoModel, connect
from pymongo import write_concern as wc, read_concern as rc, IndexModel, ReadPreference
from .channels_model import Channel
from .user_models import User
from .config import *


connect(f'{MONGO_URI}/posts', alias='Posts', ssl=USE_SSL, username=DB_ADMIN_USERNAME, password=DB_ADMIN_PASSWORD)


class GlobalPostAnalytics(MongoModel):
    _id = fields.IntegerField(required=True, primary_key=True, default=0)
    created_posts = fields.BigIntegerField(required=True, verbose_name='created_posts', mongo_name='createdPosts',
                                           min_value=0, default=0)
    added_posts = fields.BigIntegerField(required=True, verbose_name='added_posts', mongo_name='addedPosts',
                                         min_value=0, default=0)
    edited_posts = fields.BigIntegerField(required=True, verbose_name='edited_posts', mongo_name='editedPosts',
                                          min_value=0, default=0)
    deleted_posts = fields.BigIntegerField(required=True, verbose_name='deleted_posts', mongo_name='deletedPosts',
                                           min_value=0, default=0)
    global_reactions = fields.BigIntegerField(required=True, verbose_name='global_reactions',
                                              mongo_name='globalReactions', min_value=0, default=0)

    class Meta:
        connection_alias = 'Posts'
        collection_name = 'global_analytics'
        cascade = True
        write_concern = wc.WriteConcern(j=True)
        read_preference = ReadPreference.NEAREST
        read_concern = rc.ReadConcern(level='majority')
        ignore_unknown_fields = True


class Link(EmbeddedMongoModel):
    label = fields.CharField(required=True, verbose_name='link_label', mongo_name='label')
    url = fields.URLField(required=True, verbose_name='link_url', mongo_name='url')


class LinkList(EmbeddedMongoModel):
    links = fields.EmbeddedDocumentListField(Link, verbose_name='links_list', mongo_name='links')
    links_per_row = fields.IntegerField(required=True, min_value=1, max_value=4, verbose_name='links_per_row',
                                        mongo_name='linksRow')


class BasePostModel(MongoModel):
    _id = fields.CharField(required=True, primary_key=True)
    post_id = fields.CharField(required=True, verbose_name='post_id', mongo_name='postId')
    creator = fields.ReferenceField(User, on_delete=fields.ReferenceField.CASCADE,
                                    verbose_name='creator', mongo_name='creator')
    channel = fields.ReferenceField(Channel, on_delete=fields.ReferenceField.CASCADE,
                                    verbose_name='post_channel_id', mongo_name='channelId', required=True)


class PostModel(BasePostModel):
    from .reactions_model import Reaction
    """
    Generic Post Model, should not be directly used, there are
    fields that needs to be implemented for normal Posts.
    """
    message_id = fields.BigIntegerField(required=True, verbose_name='post_message_id', mongo_name='messageId')
    mime_type = fields.CharField(verbose_name='post_mime_type', mongo_name='mimeType', default=None)
    type = fields.CharField(verbose_name='post_type', mongo_name='type', required=True,
                            choices=('image', 'text', 'video', 'animation', 'document',
                                     'video_note', 'voice', 'audio', 'location', 'venue')
                            )
    group_hash = fields.CharField(verbose_name='group_hash', mongo_name='groupHash', default=None)
    created_date = fields.DateTimeField(required=True, verbose_name='post_created_date', mongo_name='createdDate')
    tags = fields.ListField(field=fields.CharField(), verbose_name='tags', mongo_name='tags', default=None)
    source = fields.EmbeddedDocumentField(Link, verbose_name='source', mongo_name='source', default=None)
    links = fields.EmbeddedDocumentField(LinkList, verbose_name='links', mongo_name='links', default=None)
    reactions = fields.EmbeddedDocumentField(Reaction, verbose_name='reactions', mongo_name='reactions',
                                             default=None)
    is_deleted = fields.BooleanField(verbose_name='post_is_deleted', mongo_name='isDeleted', default=False)
    deleted_date = fields.DateTimeField(verbose_name='post_deleted_date', mongo_name='deletedDate', default=None)

    class Meta:
        connection_alias = 'Posts'
        collection_name = 'posts'
        cascade = True
        write_concern = wc.WriteConcern(j=True)
        read_preference = ReadPreference.NEAREST
        read_concern = rc.ReadConcern(level='majority')
        indexes = [
            IndexModel('creator', name='postCreatorIndex', sparse=True),
            IndexModel('postId', name='postIdIndex', unique=True, sparse=True),
            IndexModel('groupHash', name='postGroupHashIndex', unique=True, sparse=True),
            IndexModel('messageId', name='postMessageIdIndex', sparse=True),
            IndexModel('channelId', name='postChannelIdIndex', sparse=True),
            IndexModel('createdDate', name='postCreatedDateIndex', sparse=True)
        ]
        ignore_unknown_fields = True

    @property
    def dict(self):
        return dict(
            post_id=self.post_id,
            message_id=self.message_id,
            creator=self.creator,
            channel=self.channel,
            type=self.type,
            mime_type=self.mime_type,
            group=self.group_hash,
            created_date=self.created_date,
            tags=self.tags,
            links=dict(
                links_per_row=self.links.links_per_row,
                links=[
                    {'label': i.label, 'url': i.url} for i in self.links.links
                ]
            ),
            source=dict(
                label=self.source.label,
                url=self.source.url
            ),
            reactions=[
                dict(emoji=i.emoji, count=i.count) for i in self.reactions.reactions
            ])


class ImagePost(PostModel):
    file_id = fields.CharField(required=True, verbose_name='file_id', mongo_name='fileId')
    thumbnail_file_id = fields.CharField(verbose_name='thumbnail_file_id', mongo_name='thumbFileId', default=None)
    thumbnail_size = fields.IntegerField(verbose_name='thumbnail_size', mongo_name='thumbSize', default=None)
    file_size = fields.IntegerField(verbose_name='file_size', mongo_name='fileSize', default=None)
    caption = fields.CharField(verbose_name='caption', mongo_name='caption', default=None)
    width = fields.IntegerField(verbose_name='width', mongo_name='width', required=True)
    height = fields.IntegerField(verbose_name='height', mongo_name='height', required=True)

    @property
    def dict(self):
        return dict(
            post_id=self.post_id,
            message_id=self.message_id,
            creator=self.creator,
            channel=self.channel,
            type=self.type,
            mime_type=self.mime_type,
            group=self.group_hash,
            created_date=self.created_date,
            tags=self.tags,
            links=dict(
                links_per_row=self.links.links_per_row,
                links=[
                    {'label': i.label, 'url': i.url} for i in self.links.links
                ]
            ),
            source=dict(
                label=self.source.label,
                url=self.source.url
            ),
            reactions=[
                dict(emoji=i.emoji, count=i.count) for i in self.reactions.reactions
            ],
            image=dict(
                file_id=self.file_id,
                file_size=self.file_size,
                width=self.width,
                height=self.height
            ),
            thumbnail=dict(
                file_id=self.thumbnail_file_id,
                file_size=self.thumbnail_size
            ),
            caption=self.caption
        )


class VideoNotePost(PostModel):
    file_id = fields.CharField(required=True, verbose_name='file_id', mongo_name='fileId')
    thumbnail_file_id = fields.CharField(verbose_name='thumbnail_file_id', mongo_name='thumbFileId', default=None)
    thumbnail_size = fields.IntegerField(verbose_name='thumbnail_size', mongo_name='thumbSize', default=None)
    file_size = fields.IntegerField(verbose_name='file_size', mongo_name='fileSize', default=None)
    caption = fields.CharField(verbose_name='caption', mongo_name='caption', default=None)
    duration = fields.IntegerField(verbose_name='duration', mongo_name='duration', required=True)
    length = fields.IntegerField(verbose_name='length', mongo_name='length', required=True)

    @property
    def dict(self):
        return dict(
            post_id=self.post_id,
            message_id=self.message_id,
            creator=self.creator,
            channel=self.channel,
            type=self.type,
            mime_type=self.mime_type,
            group=self.group_hash,
            created_date=self.created_date,
            tags=self.tags,
            links=dict(
                links_per_row=self.links.links_per_row,
                links=[
                    {'label': i.label, 'url': i.url} for i in self.links.links
                ]
            ),
            source=dict(
                label=self.source.label,
                url=self.source.url
            ),
            reactions=[
                dict(emoji=i.emoji, count=i.count) for i in self.reactions.reactions
            ],
            video_note=dict(
                file_id=self.file_id,
                file_size=self.file_size,
                length=self.length,
                duration=self.duration
            ),
            thumbnail=dict(
                file_id=self.thumbnail_file_id,
                file_size=self.thumbnail_size
            ),
            caption=self.caption
        )


class VideoPost(ImagePost):
    duration = fields.IntegerField(verbose_name='duration', mongo_name='duration', required=True)

    @property
    def dict(self):
        return dict(
            post_id=self.post_id,
            message_id=self.message_id,
            creator=self.creator,
            channel=self.channel,
            type=self.type,
            mime_type=self.mime_type,
            group=self.group_hash,
            created_date=self.created_date,
            tags=self.tags,
            links=dict(
                links_per_row=self.links.links_per_row,
                links=[
                    {'label': i.label, 'url': i.url} for i in self.links.links
                ]
            ),
            source=dict(
                label=self.source.label,
                url=self.source.url
            ),
            reactions=[
                dict(emoji=i.emoji, count=i.count) for i in self.reactions.reactions
            ],
            video=dict(
                file_id=self.file_id,
                file_size=self.file_size,
                width=self.width,
                height=self.height,
                duration=self.duration
            ),
            thumbnail=dict(
                file_id=self.thumbnail_file_id,
                file_size=self.thumbnail_size
            ),
            caption=self.caption
        )


class AnimationPost(VideoPost):
    file_name = fields.CharField(verbose_name='file_name', mongo_name='fileName', default=None)

    @property
    def dict(self):
        return dict(
            post_id=self.post_id,
            message_id=self.message_id,
            creator=self.creator,
            channel=self.channel,
            type=self.type,
            mime_type=self.mime_type,
            group=self.group_hash,
            created_date=self.created_date,
            tags=self.tags,
            links=dict(
                links_per_row=self.links.links_per_row,
                links=[
                    {'label': i.label, 'url': i.url} for i in self.links.links
                ]
            ),
            source=dict(
                label=self.source.label,
                url=self.source.url
            ),
            reactions=[
                dict(emoji=i.emoji, count=i.count) for i in self.reactions.reactions
            ],
            animation=dict(
                file_id=self.file_id,
                file_size=self.file_size,
                width=self.width,
                height=self.height,
                duration=self.duration,
                file_name=self.file_name
            ),
            thumbnail=dict(
                file_id=self.thumbnail_file_id,
                file_size=self.thumbnail_size
            ),
            caption=self.caption
        )


class VoicePost(PostModel):
    file_id = fields.CharField(required=True, verbose_name='file_id', mongo_name='fileId')
    duration = fields.IntegerField(verbose_name='duration', mongo_name='duration', required=True)
    file_size = fields.IntegerField(verbose_name='file_size', mongo_name='fileSize', default=None)
    caption = fields.CharField(verbose_name='caption', mongo_name='caption', default=None)

    @property
    def dict(self):
        return dict(
            post_id=self.post_id,
            message_id=self.message_id,
            creator=self.creator,
            channel=self.channel,
            type=self.type,
            mime_type=self.mime_type,
            group=self.group_hash,
            created_date=self.created_date,
            tags=self.tags,
            links=dict(
                links_per_row=self.links.links_per_row,
                links=[
                    {'label': i.label, 'url': i.url} for i in self.links.links
                ]
            ),
            source=dict(
                label=self.source.label,
                url=self.source.url
            ),
            reactions=[
                dict(emoji=i.emoji, count=i.count) for i in self.reactions.reactions
            ],
            voice=dict(
                file_id=self.file_id,
                file_size=self.file_size,
                duration=self.duration
            ),
            caption=self.caption
        )


class AudioPost(VoicePost):
    performer = fields.CharField(verbose_name='performer', mongo_name='performer', default=None)
    title = fields.CharField(verbose_name='title', mongo_name='title', default=None)
    thumbnail_file_id = fields.CharField(verbose_name='thumbnail_file_id', mongo_name='thumbFileId', default=None)
    thumbnail_size = fields.IntegerField(verbose_name='thumbnail_size', mongo_name='thumbSize', default=None)

    @property
    def dict(self):
        return dict(
            post_id=self.post_id,
            message_id=self.message_id,
            creator=self.creator,
            channel=self.channel,
            type=self.type,
            mime_type=self.mime_type,
            group=self.group_hash,
            created_date=self.created_date,
            tags=self.tags,
            links=dict(
                links_per_row=self.links.links_per_row,
                links=[
                    {'label': i.label, 'url': i.url} for i in self.links.links
                ]
            ),
            source=dict(
                label=self.source.label,
                url=self.source.url
            ),
            reactions=[
                dict(emoji=i.emoji, count=i.count) for i in self.reactions.reactions
            ],
            audio=dict(
                file_id=self.file_id,
                file_size=self.file_size,
                performer=self.performer,
                title=self.title
            ),
            thumbnail=dict(
                file_id=self.thumbnail_file_id,
                file_size=self.thumbnail_size
            ),
            caption=self.caption
        )


class DocumentPost(PostModel):
    file_id = fields.CharField(required=True, verbose_name='file_id', mongo_name='fileId')
    thumbnail_file_id = fields.CharField(verbose_name='thumbnail_file_id', mongo_name='thumbFileId', default=None)
    thumbnail_size = fields.IntegerField(verbose_name='thumbnail_size', mongo_name='thumbSize', default=None)
    file_size = fields.IntegerField(verbose_name='file_size', mongo_name='fileSize', default=None)
    caption = fields.CharField(verbose_name='caption', mongo_name='caption', default=None)
    file_name = fields.CharField(verbose_name='file_name', mongo_name='fileName', default=None)

    @property
    def dict(self):
        return dict(
            post_id=self.post_id,
            message_id=self.message_id,
            creator=self.creator,
            channel=self.channel,
            type=self.type,
            mime_type=self.mime_type,
            group=self.group_hash,
            created_date=self.created_date,
            tags=self.tags,
            links=dict(
                links_per_row=self.links.links_per_row,
                links=[
                    {'label': i.label, 'url': i.url} for i in self.links.links
                ]
            ),
            source=dict(
                label=self.source.label,
                url=self.source.url
            ),
            reactions=[
                dict(emoji=i.emoji, count=i.count) for i in self.reactions.reactions
            ],
            file=dict(
                file_id=self.file_id,
                file_size=self.file_size,
                file_name=self.file_name
            ),
            thumbnail=dict(
                file_id=self.thumbnail_file_id,
                file_size=self.thumbnail_size
            ),
            caption=self.caption
        )


class TextPost(PostModel):
    text = fields.CharField(required=True, verbose_name='text', mongo_name='text', default='')

    @property
    def dict(self):
        return dict(
            post_id=self.post_id,
            message_id=self.message_id,
            creator=self.creator,
            channel=self.channel,
            type=self.type,
            mime_type=self.mime_type,
            group=self.group_hash,
            created_date=self.created_date,
            tags=self.tags,
            links=dict(
                links_per_row=self.links.links_per_row,
                links=[
                    {'label': i.label, 'url': i.url} for i in self.links.links
                ]
            ),
            source=dict(
                label=self.source.label,
                url=self.source.url
            ),
            reactions=[
                dict(emoji=i.emoji, count=i.count) for i in self.reactions.reactions
            ],
            text=self.text
        )


class LocationPost(PostModel):
    latitude = fields.FloatField(required=True, verbose_name='location_latitude', mongo_name='latitude')
    longitude = fields.FloatField(required=True, verbose_name='location_longitude', mongo_name='longitude')

    @property
    def dict(self):
        return dict(
            post_id=self.post_id,
            message_id=self.message_id,
            creator=self.creator,
            channel=self.channel,
            type=self.type,
            mime_type=self.mime_type,
            group=self.group_hash,
            created_date=self.created_date,
            tags=self.tags,
            links=dict(
                links_per_row=self.links.links_per_row,
                links=[
                    {'label': i.label, 'url': i.url} for i in self.links.links
                ]
            ),
            source=dict(
                label=self.source.label,
                url=self.source.url
            ),
            reactions=[
                dict(emoji=i.emoji, count=i.count) for i in self.reactions.reactions
            ],
            location=dict(
                latitude=self.latitude,
                longitude=self.longitude
            )
        )


class VenuePost(LocationPost):
    title = fields.CharField(required=True, verbose_name='venue_title', mongo_name='title')
    address = fields.CharField(required=True, verbose_name='venue_address', mongo_name='address')
    foursquare_id = fields.CharField(verbose_name='foursquare_id', mongo_name='foursquareId', default=None)
    foursquare_type = fields.CharField(verbose_name='foursquare_type', mongo_name='foursquareType', default=None)

    @property
    def dict(self):
        return dict(
            post_id=self.post_id,
            message_id=self.message_id,
            creator=self.creator,
            channel=self.channel,
            type=self.type,
            mime_type=self.mime_type,
            group=self.group_hash,
            created_date=self.created_date,
            tags=self.tags,
            links=dict(
                links_per_row=self.links.links_per_row,
                links=[
                    {'label': i.label, 'url': i.url} for i in self.links.links
                ]
            ),
            source=dict(
                label=self.source.label,
                url=self.source.url
            ),
            reactions=[
                dict(emoji=i.emoji, count=i.count) for i in self.reactions.reactions
            ],
            venue=dict(
                location=dict(
                    latitude=self.latitude,
                    longitude=self.longitude
                ),
                title=self.title,
                address=self.address,
                foursquare_id=self.foursquare_id,
                foursquare_type=self.foursquare_type
            )
        )


class Posts(MongoModel):
    _id = fields.CharField(required=True, primary_key=True)
    posts_hash = fields.CharField(required=True, verbose_name='group_hash', mongo_name='groupHash')
    creator = fields.ReferenceField(User, on_delete=fields.ReferenceField.CASCADE,
                                    verbose_name='creator', mongo_name='creator', required=True)
    date_created = fields.DateTimeField(verbose_name='date_created', mongo_name='createdDate', required=True)
    channel = fields.ReferenceField(Channel, on_delete=fields.ReferenceField.CASCADE,
                                    verbose_name='post_channel_id', mongo_name='channelId', required=True)
    posts = fields.ListField(field=fields.CharField(), verbose_name='post_list', mongo_name='posts', required=True,
                             default=[])
    is_deleted = fields.BooleanField(verbose_name='post_is_deleted', mongo_name='isDeleted', default=False)
    deleted_date = fields.DateTimeField(verbose_name='deleted_date', mongo_name='deletedDate', default=None)

    class Meta:
        connection_alias = 'Posts'
        collection_name = 'post_lists'
        cascade = True
        write_concern = wc.WriteConcern(j=True)
        read_preference = ReadPreference.NEAREST
        read_concern = rc.ReadConcern(level='majority')
        indexes = [
            IndexModel('groupHash', name='postListGroupHashIndex', unique=True, sparse=True),
            IndexModel('creator', name='postListCreatorIndex', sparse=True),
            IndexModel('posts', name='postListIndex', sparse=True),
            IndexModel('channelId', name='postListChannelIdIndex', sparse=True),
            IndexModel('creationDate', name='postListCreatedDateIndex', sparse=True)
        ]
        ignore_unknown_fields = True
