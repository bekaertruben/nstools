import requests
import lxml.html as lh
import re
from enum import Enum
from nstools.utils import census_name_to_id


base_url = "http://www.mwq.dds.nl/ns/results/{issue_id}.html"

easter_eggs = (77, 78, 80, 215, 223, 256, 266, 375, 408, 430, 471, 622, 1122, 1549)


class TrotterdamIssue:
    """ Contains all info (raw and parsed) obtained from an issue's page on Trotterdam """
    issue_id : int
    title    : str  # the issue's title/name
    status   : int  # status code of http request
    table    : list # raw data in trotterdam table
    outcomes : dict # maps option id (nationstates id is one less than what trotterdam shows) to Outcome object

    def __init__(self, issue_id:int):
        self.issue_id = issue_id
        self.table = list()
        self.outcomes = dict()

        page = requests.get(base_url.format(issue_id = issue_id))
        self.status = page.status_code
        if self.status == 404:
            raise ValueError(f"Issue with ID {issue_id} not found (Trotterdam may be out of date)")

        doc = lh.fromstring(page.content)
        self.title  = doc.findtext('.//title')
        tr_elements = doc.xpath('//tr')
        self.table = [[t.text_content().strip() for t in row] for row in tr_elements]

        for row in self.table[1:]:
            options = [int(i) - 1 for i in row[0].strip().split(".")[0].strip().split("/")]
            effect = row[0].split(".")[1].strip()
            outcome = parse_result(row[1])
            for o in options:
                self.outcomes[o] = outcome
                self.outcomes[o]['output_text'] = effect


class PolicyChange(Enum):
    """ Represents the addition or removal of a policy or notability in issue outcome """
    ADDS = 1
    SOMETIMES_ADDS = 0.5
    MAY_ADD_ORR_REMOVE = 0
    SOMETIMES_REMOVES = -0.5
    REMOVES = -1


def parse_result(result):
    """ Parses issue outcomes from the 'Results' column of Trotterdam's table """
    out = dict()
    out['census_changes'] = dict()
    out['policy_changes'] = dict()
    out['notability_changes'] = dict()
    out['resign_WA'] = False

    lines = [line.strip() for line in result.strip().split("\n")]
    for line in lines:
        if "unknown effect" in line:
            out['unknown_effect'] = True
            continue
        
        if "resigns from the World Assembly" in line:
            out['resign_WA'] = True
            continue
        
        if "leads to" in line:
            # find string of form "leads to #<issue_id>"
            match = re.search(r'leads to #\d+', line)
            if match:
                out['leads_to'] = int(match.group(0).split("#")[1])
        
        if "end chain" in line:
            out['leads_to'] = None

        if "field" in line:
            # find string of form "unlocks @@<field>@@ field"
            match = re.search(r'unlocks @@\w+@@ field', line)
            if match:
                out['unlocks_field'] = match.group(0).split("@@")[1]
            continue

        is_policy = "policy" in line
        is_notability = "notability" in line

        if is_policy or is_notability:
            sometimes = "sometimes" in line
            adds      = "adds" in line
            removes   = "removes" in line

            if (not adds and not removes) or (adds and removes):
                continue
            value = line.split(":")[-1].strip()

            changes = out['policy_changes'] if is_policy else out['notability_changes']
            if value in changes:
                changes[value] = PolicyChange.ADD_ORR_REMOVE
            else:
                changes[value] = PolicyChange((0.5 if sometimes else 1) * (1 if adds else -1))

        else:
            match = re.search(r'[A-Z][\w :-]+', line)
            if match:
                c_name = match.group(0).strip()
                if not c_name in census_name_to_id:
                    continue
            else:
                continue
            
            if "(mean " in line:
                min = line.split("to")[0].strip()
                max = line.split("to")[1].strip().split(" ")[0]
                mean = line.split("(")[-1].lstrip("mean ").rstrip(")")
            else:
                mean = line.split(" ")[0]
                min = mean
                max = mean

            out['census_changes'][c_name] = (float(min), float(mean), float(max))
    
    return out