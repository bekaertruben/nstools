import yaml
from html.parser import HTMLParser
import pkgutil


def shard_key(shard):
    """ Map a shard name to the response key """
    shard = shard.upper()
    if shard == "WA":
        return "UNSTATUS"
    return shard


data = pkgutil.get_data(__name__, "census_names.yaml")
census_id_to_name = yaml.safe_load(data)
census_ids, census_names = zip(*census_id_to_name.items())
census_name_to_id = {name: id for id, name in census_id_to_name.items()}


def format_for_query(object):
    """ Convert an object to a string for use in API query, separated by '+' """
    if not hasattr(object, "__iter__"):
        return str(object)
    elif isinstance(object, str):
        return object
    else:
        return "+".join(str(o) for o in object)


class HTMLExtractor(HTMLParser):
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