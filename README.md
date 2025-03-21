# NSTools

NSTools is a collection of tools to build projects for NationStates. It includes a wrapper of the NationStates API, and some abstractions to simplify interacting with it.

Coming versions will include an asynchronous API implementation, as well as support for the Server-Sent Events streams.

I may also implement abstractions for working with cards.

## Installation

To install NSTools, run the following command:

```sh
pip install git+https://github.com/bekaertruben/nstools
```

## Census Maximizer

Currently, the main thing implemented in NSTools is the `CensusMaximizer`, which allows you to automate issue answering. See the example script [`maximizer_example.py`](examples/maximizer_example.py) to get started in adapting it to your needs.

## Nations Database

In the releases tab, I will periodically include [a dump of nation data on all nations on NationStates](https://github.com/bekaertruben/nstools/releases/download/v0.0.1/nations.feather).
This can be used to study how census scales correlate with eachother and other nation stats.
