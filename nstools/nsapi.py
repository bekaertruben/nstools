from nstools.utils import *
import requests
import xmltodict
import logging
import time
import datetime


logger = logging.getLogger("nsapi")

MAX_RETRIES = 3


class NSAPIException(Exception):
    def __init__(self, code, message):
        self.code = int(code)
        self.message = message
        super().__init__(f"[{code}] {message}")


class RateLimitedClient:
    """
    A class to manage the rate limit of the NationStates API client.

    Attributes
    ----------
    client : aiohttp.ClientSession
        The aiohttp session used to make requests
    policy : str
        The rate limit policy of the API, formated as "{requests}w:{seconds}"
    limit : int
        The number of requests allowed over a certain window
    window : int
        The ratelimit time window in seconds
    remaining_requests : int
        The number of requests remaining in the current window
    reset_time : datetime.datetime
        The time at which the ratelimit window will reset

    Methods
    -------
    
    """
    def __init__(self, policy: str = "50;w=30", headers: dict = None):
        self.session = requests.Session()
        self.session.headers.update(headers)

        self.policy = policy
        self.limit, self.window = map(int, policy.split(";w="))

        self.remaining_requests = self.limit
        self.active_requests = 0

        self.reset_time = datetime.datetime.now() # will automatically reset on first request

    def request(self, headers: dict = None, _retry: int = 0, **kwargs):
        """
        Sends a request to the NationStates API with the given parameters
        ["WORLD"]
        Parameters
        ----------
        headers : dict
            The headers to send with the request
        **kwargs : dict
            The query parameters that will be sent as query string to the API
        """

        # if the current time is past the reset time, reset the counter
        if datetime.datetime.now() > self.reset_time:
            self.remaining_requests = self.limit
            self.reset_time = datetime.datetime.now() + datetime.timedelta(seconds=self.window)
        
        # If the rate limit has been exceeded, wait until the reset time
        if self.remaining_requests <= 0:
            waittime = (self.reset_time - datetime.datetime.now()).total_seconds()
            logger.warning(f"⚠️ Rate limit reached. Waiting {round(waittime)} seconds before continuing...")
            time.sleep(waittime)
            self.remaining_requests = self.limit
            self.reset_time = datetime.datetime.now() + datetime.timedelta(seconds=self.window)

        query = "&".join([f"{k}={format_for_query(v)}" for k, v in kwargs.items()])
        url = f"https://www.nationstates.net/cgi-bin/api.cgi?{query}"
        response = self.session.get(url, headers=headers)
        self.remaining_requests -= 1

        # sometimes the API returns HTML entities in the XML response(e.g. &eacute;) which cause errors in XML parsing
        # but we can't use html.unescape, because we need to keep the XML special characters escaped
        text = unescape(response.content.decode('utf-8'))

        if response.status_code == 200: # OK
            # Check headers for rate limit information
            date = response.headers.get("Date")
            policy = response.headers.get("Ratelimit-Policy")
            seconds_until_reset = int(response.headers.get('Ratelimit-Reset'))
            remaining = int(response.headers.get('RateLimit-Remaining'))

            # If the rate limit policy has changed, update the policy
            if policy != self.policy:
                self.policy = policy
                self.limit, self.window = map(int, self.policy.split(";w="))

            # Update the rate limit counters
            response_time = datetime.datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %Z')
            resettime = response_time + datetime.timedelta(seconds=seconds_until_reset + 0.5)
            if resettime > self.reset_time:
                self.reset_time = resettime
        
            if remaining < self.remaining_requests:
                self.remaining_requests = remaining

            response_headers = response.headers
            try:
                response_content = xmltodict.parse(text, dict_constructor=dict)
                return response_headers, response_content
            except Exception as e:
                raise NSAPIException(0, f"Failed to parse XML response:\n{text}")
        
        elif response.status_code == 429: # We were blocked due to the rate limit
            if _retry < MAX_RETRIES:
                waittime = int(response.headers.get("Retry-after"))
                logger.warning(f"⚠️ Rate limit exceeded. Waiting {waittime} seconds before retrying...")

                time.sleep(waittime)
                self.remaining_requests = self.limit
                return self.request(headers = headers, _retry = _retry+1, **kwargs)
            else:
                raise NSAPIException(0, f"Retrying request failed {MAX_RETRIES} times.")
        
        elif response.status_code == 524:
            raise NSAPIException(524, "The server took too long to respond.")

        else:
            message = html_to_plaintext(text).split("Error:")[0].strip()
            raise NSAPIException(response.status_code, message)
        

class NationStatesAPI:
    """
    A class to interact with the official NationStates API

    Attributes
    ----------
    client : RateLimitedClient

    Methods
    -------
    
    """
    def __init__(self, contact_info: str):
        headers = {'User-Agent': contact_info}
        self.client = RateLimitedClient(headers=headers)
    
    def request(self, **kwargs):
        headers, content = self.client.request(**kwargs)
        return headers, content['WORLD']
    
    def shard(self, shard: str, **kwargs):
        headers, content = self.request(q=shard, **kwargs)
        return content[shard_key(shard)]

    def shards(self, shards: list, **kwargs):
        headers, content = self.request(q=format_for_query(shards), **kwargs)
        return [content[shard_key(s)] for s in shards]

    def nation(self, name: str, password: str = None):
        return NationAPI(self.client, name, password)
    
    def region(self, name: str):
        return RegionAPI(self.client, name)


class NationAPI(NationStatesAPI):
    def __init__(self, client: RateLimitedClient, name: str, password: str = None):
        self.client = client
        self.name = name
        self.password = password
        
        self.auth_headers = {'X-Password': password} if password is not None else {}

    def __str__(self):
        if self.password:
            return f"NationAPI(\"{self.name}\", password=...)"
        else:
            return f"NationAPI(\"{self.name}\")"

    def request(self, **kwargs):
        headers, content = self.client.request(nation=self.name, headers=self.auth_headers, **kwargs)

        if self.password is not None:
            if autologin := headers.get('X-Autologin'):
                self.auth_headers['X-Autologin'] = autologin
            if pin := headers.get('X-Pin'):
                self.auth_headers['X-Pin'] = pin

        return headers, content['NATION']

    def command(self, command: str, prepare_and_execute: bool =None, **kwargs):
        kwargs.pop('prepare_and_execute', None)

        if prepare_and_execute is None:
            prepare_and_execute = command not in ("issue",) # all others require two steps

        if not prepare_and_execute:
            headers, content = self.request(c=command, **kwargs)
            return content[shard_key(command)]

        else:
            headers, content = self.request(c=command, **kwargs, mode="prepare")
            if 'ERROR' in content:
                raise NSAPIException(0, content['ERROR'])
            token = content['SUCCESS']
            headers, content = self.request(c=command, **kwargs, mode="execute", token=token)
            if 'ERROR' in content:
                raise NSAPIException(0, content['ERROR'])
            return headers, content['SUCCESS']


class RegionAPI(NationStatesAPI):
    def __init__(self, client: RateLimitedClient, name: str, password: str = None):
        self.client = client
        self.name = name
    
    def __str__(self):
        return f"RegionAPI(\"{self.name}\")"
    
    def request(self, **kwargs):
        headers, content = self.client.request(region=self.name, **kwargs)

        return headers, content['REGION']
