#!/usr/bin/env python
import rich.progress
from nstools.nsapi import *
from nstools.nation import Nation
import rich
import pandas as pd
import argparse

"""
This is a script to collect data on all nations in NationStates.
It will collect data on all nations and save it to a feather file.

Contact info must be passed by command line argument. Your main nation or email suffices.
"""

parser = argparse.ArgumentParser(
    prog="census-collector",
    description="Store data on all nations in NationStates",
)
parser.add_argument('-C', '--CONTACT', type=str, required=True, help="Contact info for the API")

args = parser.parse_args()
contact = args.CONTACT

import logging
logging.getLogger("nsapi").setLevel(logging.ERROR)

api = NationStatesAPI(contact)
nation_names = api.shard("nations").split(",")

nation_dicts = []

logfile = open("census-collector.log", "w")
console = rich.console.Console(file=logfile, force_terminal=True)

progress = rich.progress.Progress(
    "[progress.description]{task.description}",
    rich.progress.BarColumn(),
    "[progress.percentage]{task.percentage:>3.0f}%",
    "({task.completed}/{task.total})",
    console=console,
)

nation_tracker = progress.add_task("Gathering nation data", total=len(nation_names))
progress.start()

for i, name in enumerate(nation_names, start=1):
    try:
        nation_api = api.nation(name)
        nation_dicts.append(Nation(nation_api).dict())
    except Exception as e:
        if isinstance(e, NSAPIException) and e.code == 404:
            console.log(f"{name} has ceased to exist")
        else:
            console.log(f"Error fetching {name}: {e}")

progress.stop()
console.log("Finished gathering data")
logfile.close()

names = [n['name'] for n in nation_dicts]
founding_time = pd.DataFrame({n['name']: {'founded': n['founded']} for n in nation_dicts}).T
fetched = pd.DataFrame({n['name']: {'fetched': n['last_updated']} for n in nation_dicts}).T
wa = pd.DataFrame({n['name']: {'WA': n['wa']} for n in nation_dicts}).T

census_data = pd.DataFrame({n['name']: n['census_data'] for n in nation_dicts}).T[census_names.values()]
for col in census_data.columns:
    if census_data[col].apply(float.is_integer).all():
        census_data[col] = census_data[col].astype(int)

sectors = pd.DataFrame({n['name']: n['sectors'] for n in nation_dicts}).T
government = pd.DataFrame({n['name']: n['government'] for n in nation_dicts}).T

policy_names = set()
sensibility_names = set()
notable_names = set()
death_names = set()

for nation in nation_dicts:
    policy_names.update(nation['policies'])
    sensibility_names.update(nation['sensibilities'])
    notable_names.update(nation['notables'])
    death_names.update(nation['deaths'].keys())

policy_names = sorted(policy_names)
sensibility_names = sorted(sensibility_names)
notable_names = sorted(notable_names)
death_names = sorted(death_names)

policies_df = pd.DataFrame({
    n['name']: {
        p: (p in n['policies']) for p in policy_names
    } for n in nation_dicts
}).T
sensibilities_df = pd.DataFrame({
    n['name']: {
        s: (s in n['sensibilities']) for s in sensibility_names
    } for n in nation_dicts
}).T
notables_df = pd.DataFrame({
    n['name']: {
        s: (s in n['notables']) for s in notable_names
    } for n in nation_dicts
}).T
deaths_df = pd.DataFrame({
    n['name']: {
        s: n['deaths'].get(s, 0) for s in death_names
    } for n in nation_dicts
}).T


nations_df = pd.concat([
    founding_time,
    fetched,
    census_data.add_prefix("census/"),
    wa,
    sectors.add_prefix("sector/"),
    government.add_prefix("government/"),
    policies_df.add_prefix("policy/"),
    sensibilities_df.add_prefix("sensibility/"),
    notables_df.add_prefix("notable/"),
    deaths_df.add_prefix("death/")
], axis=1)

nations_df.to_feather("nations.feather", compression="zstd", compression_level=19)