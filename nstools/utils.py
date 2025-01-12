import html.parser
import yaml
import string
import html
import pkgutil


data = pkgutil.get_data(__name__, "census_names.yaml")
census_id_to_name = yaml.safe_load(data)
census_ids, census_names = zip(*census_id_to_name.items())
census_name_to_id = {name: id for id, name in census_id_to_name.items()}


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
    # copied from https://www.ou.edu/research/electron/internet/special.shtml 
    # copyright (©) 1998, Scott Russell, University of Oklahoma
    entities = {
        '&Agrave;': 'À', '&Aacute;': 'Á', '&Acirc;': 'Â', '&Atilde;': 'Ã', '&Auml;': 'Ä', '&Aring;': 'Å',
        '&agrave;': 'à', '&aacute;': 'á', '&acirc;': 'â', '&atilde;': 'ã', '&auml;': 'ä', '&aring;': 'å',
        '&AElig;': 'Æ', '&aelig;': 'æ', '&szlig;': 'ß', '&Ccedil;': 'Ç', '&ccedil;': 'ç', '&Egrave;': 'È',
        '&Eacute;': 'É', '&Ecirc;': 'Ê', '&Euml;': 'Ë', '&egrave;': 'è', '&eacute;': 'é', '&ecirc;': 'ê',
        '&euml;': 'ë', '&#131;': 'ƒ', '&Igrave;': 'Ì', '&Iacute;': 'Í', '&Icirc;': 'Î', '&Iuml;': 'Ï',
        '&igrave;': 'ì', '&iacute;': 'í', '&icirc;': 'î', '&iuml;': 'ï', '&Ntilde;': 'Ñ', '&ntilde;': 'ñ',
        '&Ograve;': 'Ò', '&Oacute;': 'Ó', '&Ocirc;': 'Ô', '&Otilde;': 'Õ', '&Ouml;': 'Ö', '&ograve;': 'ò',
        '&oacute;': 'ó', '&ocirc;': 'ô', '&otilde;': 'õ', '&ouml;': 'ö', '&Oslash;': 'Ø', '&oslash;': 'ø',
        '&#140;': 'Œ', '&#156;': 'œ', '&#138;': 'Š', '&#154;': 'š', '&Ugrave;': 'Ù', '&Uacute;': 'Ú',
        '&Ucirc;': 'Û', '&Uuml;': 'Ü', '&ugrave;': 'ù', '&uacute;': 'ú', '&ucirc;': 'û', '&uuml;': 'ü',
        '&#181;': 'µ', '&#215;': '×', '&Yacute;': 'Ý', '&#159;': 'Ÿ', '&yacute;': 'ý', '&yuml;': 'ÿ',
        '&#176;': '°', '&#134;': '†', '&#135;': '‡', '&lt;': '<', '&gt;': '>', '&#177;': '±', '&#171;': '«',
        '&#187;': '»', '&#191;': '¿', '&#161;': '¡', '&#183;': '·', '&#149;': '•', '&#153;': '™',
        '&copy;': '©', '&reg;': '®', '&#167;': '§', '&#182;': '¶'
    }
    
    for entity, char in entities.items():
        text = text.replace(entity, char)
    
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