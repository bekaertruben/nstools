from nstools.nsapi import NationStatesAPI
from nstools.nation import Nation
from nstools.census_maximizer import *
import pandas as pd
import yaml

##### LOAD DATA #####

df = pd.read_feather("../data/nations.feather") # find the fine on the github releases tab
df = df[df.columns[df.columns.str.startswith("census/")]]
df.columns = df.columns.str.replace("census/", "")

census_mean = df.mean(axis=0).to_dict()
census_std = df.std(axis=0).to_dict()

with open("maximizer_weights.yaml", "r") as f:
    maximizer_weights = yaml.safe_load(f)

##### SET UP MAXIMIZER #####

api = NationStatesAPI("bekaertruben@gmail.com [Vicken]")
nation = Nation(api.nation("Testlandia", password="******"))

scorer = NormalizedScorer(census_mean, census_std, **maximizer_weights)
predictor = TrotterdamPredictor()
maximizer = CensusMaximizer(nation, predictor, scorer)

##### RUN MAXIMIZER #####

for issue, choice, initial_dict, new_dict, predicted_scores in maximizer.run():
    actual_outcome = OutcomePrediction.calc_actual_change(initial_dict, new_dict)
    score = scorer.score_prediction(initial_dict, actual_outcome)
    print(f"{[issue.id]} {issue.title}:")
    if choice == -1:
        print("\tchose to dismiss issue")
    else:
        print(f"\tchose {choice}, score changed by {score:.3e}")
        print(f"\tprediction was: {predicted_scores[choice]:.3e}")
