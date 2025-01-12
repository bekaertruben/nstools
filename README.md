This is the initial incarnation of the project, kept here for archival purposes.  
Back then, this repo was still github.com/bekaertruben/ns-census-maximizer.  
The code is terrible, and I hate looking at it. Just use the main branch, please :)

# Nationstates Census Maximizer
This is a script that solves a nation's issues by attempting to maximise the world census scales of your choosing.

## Requirements
Only tested on python 3.9 but any version 3.5 and higher should work fine.

The required modules can be installed using pip: `pip install -r requirements.txt`

## Configuration and Usage
To use one should change the `USER` and `PASSWORD` variables to the nation's login credentials. For use of the Nationstates API you should also provide contact details of some shape or form in `CONTACT`.

Sample usage is illustrated in `example.py`. To configure what census scales to prioritize as well as what scores to attribute to policies, modify the `census` and `policy` dicts passed to `CensusMaximizer.adjust_weights`. For example:

```py
solver.adjust_weights(census = {
    -1 : ("Wealth Gaps", "Obesity", "Crime", "Charmlessness", "Primitiveness", "Averageness", "Death Rate", "Taxation"),
    0  : ("Rudeness", "Ignorance", "Corruption", "Government Size", "Political Apathy", "Authoritarianism"),
    2  : ("Economy", "Political Freedom"),
    3  : ("Civil Rights",),
}, policy={
    "No Internet": -10
})
```

By default all census ranks are weighed by world mean as an increase of 10 points for "Industry: Information Technology" doesn't mean all that much whereas +10 Economy is a massive increase. The above code then changes these weights further to ensure "Wealth Gaps", "Obesity", etc. get minimized and "Civil Rights" gets weighed three times more than other stats. The policy "No Internet" gets a negative score to ensure the nation cannot get this policy and will remove it when given the chance. This is useful because this policy strongly limits available choices.
