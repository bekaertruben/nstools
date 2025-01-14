from nstools.nation import Nation
from nstools.trotterdam import TrotterdamIssue, PolicyChange
from nstools.utils import census_names, census_mean, census_std
from copy import deepcopy


class OutcomePrediction:
    """
    Prediction for the outcome of an issue.

    Attributes:
    - census_changes: dict[str, float]
        A dictionary mapping census names to the predicted change in value.
        Every census name must be present.
    - policies: dict[str, float]
        A dictionary containing the predicted probability of having a policy.
        Must not necessarily contain all policies (those not present are assumed to be 0).
    - notables: dict[str, float]
        A dictionary containing the predicted probability of having a notable.
        Must not necessarily contain all notables (those not present are assumed to be 0).
    - resign_WA: bool
        Whether the nation is predicted to resign from the World Assembly.
    """
    def __init__(self, census_changes, policies, notables, resign_WA):
        self.census_changes = census_changes
        self.policies = policies
        self.notables = notables
        self.resign_WA = resign_WA
    
    @staticmethod
    def calc_actual_change(old_dict, new_dict):
        """ Calculate the actual change in census values between two nation dictionaries. """
        census_changes = {
            census_name: new_dict['census_data'][census_name] - old_dict['census_data'][census_name]
            for census_name in census_names
        }

        policies = {policy: 1 for policy in new_dict['policies']}
        notables = {notable: 1 for notable in new_dict['notables']}
        resign_WA = old_dict['wa'] and not new_dict['wa']

        return OutcomePrediction(census_changes, policies, notables, resign_WA)



class Predictor:
    """
    A class that predicts the outcome of an issue.
    """
    def __init__(self):
        pass
    
    def __call__(self, nation_dict, issue, option_id) -> OutcomePrediction:
        raise NotImplementedError()


class Scorer:
    """
    A class that scores a nation based on its state, or an OutcomePrediction on how much it would increase the score of the nation.
    In principle, `score(nation + outcome) = score(nation) + score(outcome)`, but the CensusMaximizer only uses the outcome score.
    The nation score is meant to be used to track the progress of the nation over time.
    """
    def __init__(self):
        pass
    
    def score_nation(self, nation_dict) -> float:
        raise NotImplementedError()

    def score_prediction(self, nation_dict, prediction: OutcomePrediction) -> float:
        raise NotImplementedError()


class CensusMaximizer:
    def __init__(self, nation: Nation, predictor: Predictor, scorer: Scorer):
        self.nation = nation
        self.scorer = scorer
        self.predictor = predictor

        if self.nation.last_updated is None:
            self.nation.update()
    
    def run(self):
        while len(issues := self.nation.issues) > 0:
            issue = issues.pop()

            initial_dict = self.nation.dict()

            option_scores = {}
            for option_id, option_text in issue.options.items():
                prediction = self.predictor(deepcopy(initial_dict), issue, option_id)
                score = self.scorer.score_prediction(deepcopy(initial_dict), prediction)
                option_scores[option_id] = score
            
            best_option = max(option_scores, key=option_scores.get)

            choice = best_option if option_scores[best_option] > 0 else -1
            issue.answer(choice)

            if choice != -1:
                self.nation.update()
                new_dict = self.nation.dict()
            else:
                new_dict = initial_dict

            yield issue, choice, initial_dict, new_dict, option_scores


class TrotterdamPredictor(Predictor):

    def __init__(self):
        super().__init__()
        self.issue_memo = {}

    def get_trotterdam_issue(self, issue_id):
        if issue_id not in self.issue_memo:
            self.issue_memo[issue_id] = TrotterdamIssue(issue_id)
        
        return self.issue_memo[issue_id]
    
    def __call__(self, nation_dict, issue, option_id):
        trotterdam_issue = self.get_trotterdam_issue(issue.id)
        trotterdam_outcome = trotterdam_issue.outcomes[option_id]

        census_change = {census_name: 0 for census_name in census_names}

        for census_name, value in trotterdam_outcome['census_changes'].items():
            census_change[census_name] += value[1] # assume mean outcomes

        policies = {
            policy: 1 for policy in nation_dict['policies']
        }
        for policy, change in trotterdam_outcome['policy_changes'].items():
            if policy in policies:
                if change == PolicyChange.REMOVES:
                    del policies[policy] 
                if change in (PolicyChange.SOMETIMES_REMOVES, PolicyChange.MAY_ADD_ORR_REMOVE):
                    policies[policy] = 0.5
            else:
                if change == PolicyChange.ADDS:
                    policies[policy] = 1
                if change in (PolicyChange.SOMETIMES_ADDS, PolicyChange.MAY_ADD_ORR_REMOVE):
                    policies[policy] = 0.5

        notables = {
            notable: 1 for notable in nation_dict['notables']
        }
        for notable, change in trotterdam_outcome['notability_changes'].items():
            if notable in notables:
                if change == PolicyChange.REMOVES:
                    del notables[notable] 
                if change in (PolicyChange.SOMETIMES_REMOVES, PolicyChange.MAY_ADD_ORR_REMOVE):
                    notables[notable] = 0.5
            else:
                if change == PolicyChange.ADDS:
                    notables[notable] = 1
                if change in (PolicyChange.SOMETIMES_ADDS, PolicyChange.MAY_ADD_ORR_REMOVE):
                    notables[notable] = 0.5
        
        prediction = OutcomePrediction(census_change, policies, notables, trotterdam_outcome['resign_WA'])
        return prediction


class NormalizedScorer(Scorer):
    def __init__(self, census_weights: dict = None, policy_weights: dict = None, allow_WA_resignation=False):
        if census_weights is None:
            census_weights = { census_name: 1 for census_name in census_names }
        if policy_weights is None:
            policy_weights = {}

        self.census_weights = census_weights
        self.policy_weights = policy_weights
        self.allow_WA_resignation = allow_WA_resignation

    def score_nation(self, nation_dict):
        census_score = sum(
            (value - census_mean[census_name]) / census_std[census_name]
            * (self.census_weights[census_name] if census_name in self.census_weights else 1)
            for census_name, value in nation_dict['census'].items()
        )

        policy_score = sum(
            self.policy_weights[policy] for policy in nation_dict['policies']
        )

        return census_score + policy_score

    def score_prediction(self, nation_dict, prediction: OutcomePrediction):
        census_score = sum(
            value / census_std[census_name]
            * (self.census_weights[census_name] if census_name in self.census_weights else 1)
            for census_name, value in prediction.census_changes.items()
        )

        policy_score = 0
        for policy, weight in self.policy_weights.items():
            policy_initial = 1 if policy in nation_dict['policies'] else 0
            policy_prediction = prediction.policies.get(policy, 0)

            policy_score += (policy_prediction - policy_initial) * weight
        
        score = census_score + policy_score
        if not self.allow_WA_resignation and prediction.resign_WA:
            score = - float('inf')

        return score