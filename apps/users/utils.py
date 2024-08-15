import string

VALID_NAME_CHARLIST = list(string.ascii_lowercase + string.digits + '_' + '-')

def sanitize_nsid(nsid: str) -> str:
    nsid = nsid.lower().replace(' ', '-')
    return ''.join(ch for ch in nsid if ch in VALID_NAME_CHARLIST)