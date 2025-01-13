import html.parser
import yaml
import re
import html
import pkgutil


_data = pkgutil.get_data(__name__, "data/census_names.yaml")
census_id_to_name = yaml.safe_load(_data)
census_ids, census_names = zip(*census_id_to_name.items())
census_name_to_id = {name: id for id, name in census_id_to_name.items()}
del _data

_data = pkgutil.get_data(__name__, "data/html_escape_characters.yaml")
html_escape_characters = yaml.safe_load(_data)
entities_to_escape = {
    k: v for k, v in html_escape_characters.items()
    if not any(c in v for c in ("&", "<", ">", '"', "'"))
}
del _data


def shard_key(shard):
    """ Map a shard name to the response key """
    shard = shard.upper()
    if shard == "WA":
        return "UNSTATUS"
    # I know there are a couple other, but haven't encountered them yet.
    # So if you do, please submit an issue!
    return shard


def format_for_query(object):
    """ Convert an object to a string for use in API query, separated by '+' """
    if not hasattr(object, "__iter__"):
        return str(object)
    elif isinstance(object, str):
        return object
    else:
        return "+".join(str(o) for o in object)


def unescape(text):
    """ Unescape HTML entities in a string, while leaving valid xml """
    text = re.sub(r"&\w+;", lambda m: entities_to_escape.get(m.group(0), m.group(0)), text)
    return text


class HTMLExtractor(html.parser.HTMLParser):
    """ A class to extract plaintext from HTML """
    def __init__(self):
        super().__init__()
        self.data = ""
    
    def handle_data(self, data):
        self.data += data


def html_to_plaintext(html):
    """ Convert HTML to plaintext """
    parser = HTMLExtractor()
    parser.feed(html)
    return parser.data