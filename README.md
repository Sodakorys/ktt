# Korys Tester Tools

This package serves as a toolbox + framework to help making simple python tests on external devices.

The main purpose is HW validation.


## Setup

Download the [latest whl package](https://github.com/Sodakorys/ktt/releases/latest).

Then:
```
tar xf ktt_vXX.tar.gz
python3 -m pip install dist/korys_tester_tools-*.whl
```


## Implementation

Define your own tester python file that imports our modules:

|                    ||
|---|---|
|**Timeout**        |Generates a timed thread and you can check for `has_timeout_occured()` to know if you have reached it or not.|
|**AtHandler**      |At command handler, capable of handling multiple serial ports (1 for command and 1 for reception)|
|**TestStep**       |Small object that handles each test from its start to its result|
|**ResultHandler**  |Higher class to handle multiple TestSteps and order them by module/components and generate a csv|
|**Transcriptor**   |Using the ResultHandler setps, capable of generating a LaTex report provided you implement your default text for each kind of component|
|**CliHandler**     |Simple console handler, capable of handling both serial and Telnet consoles. Stores the session logs in parallel to a logfile.|


## Developpement / contribution

### Setup

install the requirements:

For local testing
```
python3 -m pip install -r requirements.txt
```

For package generation, documentation, etc...
```
python3 -m pip install -r requirements.build.txt
```

### Generate package

```
make package
```

### Generate documentation

```
make doc
```
