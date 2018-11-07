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
import re


class Markdown:
    """
    Class with operations to parse Markdown strings to verify validity, or escape strings for special entities,
    such as @user_name, #hash_tag or http://www.my_link.com/

    This markdown complies with Telegram's markdown style, which can be seen at
    https://core.telegram.org/bots/api#formatting-options
    """
    MARKDOWN_CHARS = ('*', '_', '`', '```', '[', ']', '(', ')', )
    USERNAME_ENTITY_REGEX = re.compile('(^@[\w_]{5,})')
    HASHTAG_ENTITY_REGEX = re.compile('(^#[\S_]+)')
    LINK_ENTITY_REGEX = re.compile('(([a-z]+:(//)?)?[\w._\-]+(@?)[.\w]{3,}(/?[^\s]+))')

    @staticmethod
    def parser(string: str)-> str:
        """
        Parses an unicode string to verify the validity of the markdown.
        The parser ignores all the markdown elements when there is an element on the top-level.
        For example: *This is ```completely``` bold*
        The above string will ignore the '```' block characters and only parse if another '*' is found.
        :param string: The unicode string to be verified.
        :return: The string parsed, removing invalid markdown, or raises KeyError containing the index of an invalid
                 markdown element.
        """
        last_markdown = None
        last_markdown_index: int = 0
        text: str = ''

        index: int = 0
        while index < len(string):
            if last_markdown is not None:
                if string[index] in Markdown.MARKDOWN_CHARS:
                    if string[index:index+2] == '```':
                        _c = '```'
                        index += 3
                    else:
                        _c = string[index]
                        index += 1

                    if _c == last_markdown:
                        last_markdown = None

                else:
                    text += string[index]
                    index += 1

                continue

            if string[index] in Markdown.MARKDOWN_CHARS:
                if string[index:index+2] == '```':
                    last_markdown = '```'
                    last_markdown_index = index
                    index += 3
                else:
                    last_markdown = string[index]
                    last_markdown_index = index
                    index += 1

                text += last_markdown
                continue
            else:
                text += string[index]
                index += 1
        if last_markdown is not None:
            raise KeyError('Invalid markdown at index %d' % last_markdown_index)

        else:
            return text

    @staticmethod
    def escape(string: str)-> str:
        """
        Escape special entities on a markdown string.
        Special entities are as described below:

        Username: Special link entities that follow the following Regex expression: '@[\w\d_]{5,}'
        :param string: The string to be escaped
        :return: A new string with the escaped characters.
        """
        text = string.split()

        for i in range(len(string)):
            word = text[i]

            if Markdown.USERNAME_ENTITY_REGEX.match(word) is not None:
                text[i] = word.replace('_', '\_')

            elif Markdown.HASHTAG_ENTITY_REGEX.match(word) is not None:
                text[i] = word.replace('_', '\_')

            elif Markdown.LINK_ENTITY_REGEX.match(word) is not None:
                text[i] = word.replace('_', '\_').replace('*', '\*').replace('`', '\`')

            else:
                pass

        return ' '.join(text)
