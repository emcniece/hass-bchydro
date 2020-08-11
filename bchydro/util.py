import re


def parse_bchydro_timestamp(timestamp):
    return re.sub(r"(-[0-9]{2}\:[0-9]{2}$)", "", timestamp)
