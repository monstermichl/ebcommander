# Overview
ebcommander is intended to be used as interaction layer between Python and EBCommand (command.elektrobit.com). It can either be used as a module or directly via Commandline.

---

## Preconditions
The script depends on the following Python packages
- beautifulsoup4
- requests
- pyyaml

---

## Usage
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
