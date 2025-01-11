# import nationstates as ns
from nstools import nsapi
from nstools.utils import census_id_to_name, census_ids
import time


class Nation:
    """
    A class to represent a nation in NationStates.

    Attributes:
    -----------
    api: nsapi.NationAPI
        The NationStates API object with which to make requests
    name: str
        The name of the nation
    last_updated: int
        The time at which the data was last updated
    founded: int
        The time at which the nation was founded
    census_data: dict
        A dictionary containing the census data for the nation
    policies: list
        A list of the nation's policies
    sensibilities: list
        A list of the nation's sensibilities
    notables: list
        A list of the nation's notables
    sectors: dict
        A dictionary with the fractions of GDP in each sector
    government: dict
        A dictionary with the government's budget distribution
    deaths: dict
        A dictionary with the causes of death and their fractions
    wa: bool
        Whether the nation is a WA member
    issues: list[Issue]
        A list of the nation's issues
    
    Methods:
    --------
    update()
        Load the nation's information from the API
    """

    def __init__(self, nation_api: nsapi.NationAPI, load: bool = True):
        self.api = nation_api
        self.name = nation_api.name

        if load:
            self.update()
            if self.api.password is None:
                self.issues = []
        else:
            self.last_updated = None
            self.founded = None
            self.census_data = None
            self.policies = None
            self.sensibilities = None
            self.notables = None
            self.sectors = None
            self.government = None
            self.deaths = None
            self.wa = None
            self.issues = []

    def update(self):
        """ Load nation information """
        self.last_updated = int(time.time())

        shards = ["foundedtime", "census", "policies", "sensibilities", "notables", "sectors", "govt", "deaths", "wa"]
        if self.api.password is not None:
            shards.append("issues")
    
        data = self.api.shards(
            shards,
            scale=census_ids, mode="score"
        )
        
        self.founded = int(data[0])

        self.census_data = {
            census_id_to_name[int(scale['@id'])] : float(scale['SCORE'])
            for scale in data[1]['SCALE']
        }

        if isinstance(data[2]['POLICY'], list):#
            self.policies = [pol['NAME'] for pol in data[2]['POLICY']]
        else:
            self.policies = [data[2]['POLICY']['NAME']]
        
        self.sensibilities = [s.strip() for s in data[3].split(",")]

        if isinstance(data[4]['NOTABLE'], list):
            self.notables = data[4]['NOTABLE']
        else:
            self.notables = [data[4]['NOTABLE']]
        
        self.sectors = {k: float(v) for k, v in data[5].items()}
        self.government = {k: float(v) for k, v in data[6].items()}

        if isinstance(data[7]['CAUSE'], list):
            self.deaths = {
                cause['@type'] : float(cause['#text'])
                for cause in data[7]['CAUSE']
            }
        else:
            self.deaths = {
                data[7]['CAUSE']['@type'] : float(data[7]['CAUSE']['#text'])
            }

        self.wa = data[8] in ("WA Member", "WA Delegate")

        if self.api.password is not None:
            if (issues_response := data[9]) is None:
                self.issues = []
            elif isinstance(issues_response['ISSUE'], dict):
                self.issues = [Issue(self, issues_response['ISSUE'])]
            else:
                self.issues = [Issue(self, issue) for issue in issues_response['ISSUE']]


    def dict(self):
        return {
            'name': self.name,
            'last_updated': self.last_updated,
            'founded': self.founded,
            'census_data': self.census_data,
            'policies': self.policies,
            'sensibilities': self.sensibilities,
            'notables': self.notables,
            'sectors': self.sectors,
            'government': self.government,
            'deaths': self.deaths,
            'wa': self.wa,
        }


class Issue:
    """
    A class to represent an issue in NationStates
    """
    
    def __init__(self, nation: Nation, api_response: dict):
        self.nation = nation
        self.id = int(api_response['@id'])
        self.title = api_response['TITLE']
        self.text = api_response['TEXT']
        self.author = api_response['AUTHOR']
        self.editor = api_response['EDITOR'] if 'EDITOR' in api_response else None
        self.pictures = (api_response['PIC1'], api_response['PIC2'])
        self.options = {
            int(option['@id']): option['#text']
            for option in api_response['OPTION']
        }
        self.open = True

    def answer(self, option_id: int):
        """ Answer the issue """
        assert self.open, "Issue is already answered"
        request = self.nation.api.command("issue", issue=self.id, option=option_id)
        self.open = False
        return request

    def dismiss(self):
        """ Dismiss the issue """
        return self.answer(-1)