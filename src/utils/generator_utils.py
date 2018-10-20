import random
from string import ascii_letters, digits, hexdigits


def id_generator(size: int, start_num: int = None, *, use_hex=False)-> str:
    """
    Generates an ID, with `size` characters, randomly picked. An additional `start_num` can be used to be the first
    characters on the result string. The return string will never be bigger than `size`, so if `start_num` has already
    `size` characters, `start_num` is returned in a random state.
    :param size: The size of the ID to be generated
    :param start_num: (Optional) An integer number to be the first characters in the result string
    :param use_hex: If True, will use hex digits instead of ascii letters + digits
    :return: `size`-sized string
    """
    _str = ''
    if start_num is not None:
        _start_num = str(start_num)
        if len(_start_num) >= size:
            _str += _str.join(random.sample(_start_num, k=size)[:size])
            return _str
        else:
            _str += _start_num

    population = ascii_letters + digits
    if use_hex:
        population = hexdigits

    _str_size = len(_str)
    return _str + ''.join(random.choices(population, k=(size - _str_size)))
