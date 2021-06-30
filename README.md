# Overview
EBCommander is intended as an interaction layer between Python and EBCommand (https://command.elektrobit.com). It can either be used as a module or directly via Commandline. The Python documentation can be found in [doc](https://htmlpreview.github.io/?https://github.com/monstermichl/ebcommander/blob/master/doc/ebcommander/ebcommander.html).

---

## Preconditions
The script depends on the following Python packages
- beautifulsoup4
- requests
- pyyaml

---

## Use as module
Import EBCommand.
> from ebcommander import EbCommand

Create an instance (this starts the initial data retrieval which may take a while, therefore, it should be considered to run it asynchronously).
> commander = EbCommand('your-user', 'your-password')

---

## Use from the Commandline
### Direct call
For simple requests (e.g. just to get a glimpse at a specific file) the script can be called with the following arguments

| Argument   | Description                                       |
|------------|---------------------------------------------------|
| --json     | JSON file to which filtered data shall be written |
| --yaml     | YAML file to which filtered data shall be written |
| --filter   | File filter pattern                               |
| --download | Path to which the files shall be downloaded       |

---

### Complex calls
For more versatile operations a config file must provided. It can contain several settings to apply filters on projects, distributions, versions and files, store JSON and YAML files and download the retrieved files. For more information see example-config.yaml

The config is provided by the following arguments

| Argument   | Description                            |
|------------|----------------------------------------|
| --config   | Path to config for more complex setups |

---

Regardless, if direct or compex calls, the following arguments must be provided

| Argument   | Description             |
|------------|-------------------------|
| --user     | EBCommand username      |
| --password | EBCommand user password |

---

Additionally, the following arguments can optionally be provided

| Argument      | Description                               |
|---------------|-------------------------------------------|
| --proxy-http  | HTTP proxy  (e.g. http://localhost:1234)  |
| --proxy-https | HTTPS proxy (e.g. https://localhost:1234) |
