from datetime import datetime


def get_start_date():
    return [int(x) for x in datetime.now().strftime('%Y %m 01').split()]


def num_apartment(val: str | None) -> str:
    # val = val.strip()
    if val:
        if 'кв.' in val:
            return val.replace('кв.', '').strip()
        elif  'кв' in val:
            return val.replace('кв', '').strip()
        else:
            return val
    else:
        return ''


def modify_date(date):
    return '-'.join(reversed([x for x in date.split('.')]))
