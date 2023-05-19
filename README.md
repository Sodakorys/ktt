# Korys Tester Tools

This package serves as a toolbox + framework to help making simple python tests on external devices
The main purpose is HW validation.


## Setup

install the requirements:
For local testing
```
python3 -m pip install -r requirements.txt
```

For package generation, documentation, etc...
```
python3 -m pip install -r requirements.build.txt
```

## Generate package

```
make package
```

## Generate documentation

```
make doc
```

## Implementation

Define your own tester python file that imports our modules:

Timeout:        Generates a timed thread and you can check for `has_timeout_occured()` to know if you have reached it or not.
AtHandler:      At command handler, capable of handling multiple serial ports (1 for command and 1 for reception)
TestStep:       Small object that handle each test from its start to its result
ResultHandler:  Higher class to handle multiple TestSteps and order them by module/components and generate a csv
Transcriptor:   Using the ResultHandler setps, capable to generate a LaTex report provided you implemnt your default text for each kind of component
CliHandler:     Simple console handler, capable to handle both serial and Telnet consoles. Stores in parallel in a logfile.
