import datetime


def get_key(d, key):
    try:
        return d[key]
    except KeyError:
        raise Exception('Key {} does not exist'.format(key))


def get_required_str(d, key):
    value = get_key(d, key)
    if not value:
        raise Exception('Missing required key {}'.format(key))
    return value


def get_int(d, key, valid_choices=None):
    try:
        value = int(get_key(d, key))
    except ValueError:
        raise Exception('Malformed {}'.format(key))
    if valid_choices and value not in valid_choices:
        raise Exception('Invalid {}'.format(key))
    return value


def get_int_list(d, key):
    try:
        value = get_key(d, key)
        if value:
            value = [int(v) for v in value.split(',')]
        else:
            value = -1
    except ValueError:
        raise Exception('Malformed {}'.format(key))
    return value

def get_time(d, key):
    try:
        value = get_key(d, key)
        if ':' not in value:
            # assume we're dealing with minutes
            value = int(value)
            if value < 60:
                value = '00:' + str(value)
            else:
                hours = int(value / 60)
                minutes = value % 60
                value = str(hours) + ':' + str(minutes)
        value = [int(t) for t in value.split(':')]
        value = datetime.time(*value)
        value.replace(tzinfo=datetime.timezone.utc)
        return value
    except ValueError:
        raise Exception('Malformed {}'.format(key))
    except TypeError:
        raise Exception('Malformed {}'.format(key), d)
    except:
        raise Exception('Unknown problem with {}'.format(key))


def get_timedelta(d, key):
    try:
        value = get_key(d, key)
        if ':' not in value:
            # assume we're dealing with minutes
            value = int(value)
            if value < 60:
                hours = 0
                minutes = str(value)
            else:
                hours = int(value / 60)
                minutes = value % 60
            return datetime.timedelta(hours=hours, minutes=minutes)
        else:
            value = [int(t) for t in value.split(':')]
            return datetime.timedelta(hours=value[0], minutes=value[1])
    except ValueError:
        raise Exception('Malformed {}'.format(key))
    except TypeError:
        raise Exception('Malformed {}'.format(key))
    except:
        raise Exception('Unknown problem with {}'.format(key))


class Format:
    def __init__(self, bmlt_object):
        self.id = get_int(bmlt_object, 'id')
        self.key = get_required_str(bmlt_object, 'key_string')
        self.name = get_required_str(bmlt_object, 'name_string')
        self.description = bmlt_object.get('description')


class Meeting:
    def __init__(self, bmlt_object):
        self.name = get_required_str(bmlt_object, 'meeting_name')
        self.start_time = get_time(bmlt_object, 'start_time')
        self.duration = get_timedelta(bmlt_object, 'duration_time')
        self.weekday = get_int(bmlt_object, 'weekday_tinyint', valid_choices=[1, 2, 3, 4, 5, 6, 7])
        self.facility = bmlt_object.get('location_text')
        self.street = bmlt_object.get('location_street')
        self.city = bmlt_object.get('location_municipality')
        self.province = bmlt_object.get('location_province')
        self.postal_code = bmlt_object.get('location_postal_code_1')
        self.nation = bmlt_object.get('nation')
        self.formats = bmlt_object.get('formats', '')
        self.format_ids = get_int_list(bmlt_object, 'format_shared_id_list')

    @property
    def location(self):
        ret = ''
        if self.facility:
            ret += self.facility
        if self.street:
            ret = ret + ', ' if ret else ret
            ret += self.street
        if self.city:
            ret = ret + ', ' if ret else ret
            ret += self.city
        if self.province:
            ret = ret + ', ' if ret else ret
            ret += self.province
        if self.postal_code:
            ret = ret + ', ' if ret else ret
            ret += self.postal_code
        return ret
