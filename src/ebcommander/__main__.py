import argparse
import os

from pathlib     import Path
from yaml        import load, CLoader
from ebcommander import EbCommand


def main():
    """
    Entry point of the script. It's only called of the script is executed directly (e.g. via commandline).
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('--user'       , help='EBCommand username'                               , required=True , type=str)
    parser.add_argument('--password'   , help='EBCommand user password'                          , required=True , type=str)
    parser.add_argument('--proxy-http' , help='HTTP proxy (e.g. http://localhost:1234)'          , required=False, type=str)
    parser.add_argument('--proxy-https', help='HTTPS proxy (e.g. https://localhost:1234)'        , required=False, type=str)
    parser.add_argument('--json'       , help='JSON file to which filtered data shall be written', required=False, type=str)
    parser.add_argument('--yaml'       , help='YAML file to which filtered data shall be written', required=False, type=str)
    parser.add_argument('--filter'     , help='File filter pattern'                              , required=False, type=str)
    parser.add_argument('--download'   , help='Path to which the files shall be downloaded'      , required=False, type=str)
    parser.add_argument('--config'     , help='Path to config for more complex setups'           , required=False, type=str)

    args    = parser.parse_args()
    command = EbCommand(args.user, args.password, args.proxy_http, args.proxy_https)

    def write_file(path: str, content: str):
        with open(path, 'w') as f:
            f.write(content)

    def download(path: str, command_object: EbCommand, filename_only: bool = False, newer_only: bool = False):
        path = Path(path).absolute()
        if path.exists():
            command_object.download(str(path), filename_only, newer_only)

    # config has higher priority
    if args.config:
        KEY_YAML_FILTER_PROJECTS      = 'filter-projects'
        KEY_YAML_FILTER_DISTRIBUTIONS = 'filter-distributions'
        KEY_YAML_FILTER_VERSIONS      = 'filter-versions'
        KEY_YAML_FILTER_FILES         = 'filter-files'
        KEY_YAML_JSON                 = 'json'
        KEY_YAML_YAML                 = 'yaml'
        KEY_YAML_DOWNLOAD             = 'download'
        KEY_YAML_PATH                 = 'path'
        KEY_YAML_FILENAME_ONLY        = 'filename-only'
        KEY_YAML_MKDIR                = 'mkdir'
        KEY_YAML_NEWER_ONLY           = 'newer-only'

        with open(args.config, 'r') as f:
            config = load(f.read(), Loader=CLoader)
        
        for entry in config:
            filters = {}

            # process filters
            if KEY_YAML_FILTER_PROJECTS in entry:
                filters['pattern_projects'] = entry[KEY_YAML_FILTER_PROJECTS]

            if KEY_YAML_FILTER_DISTRIBUTIONS in entry:
                filters['pattern_distributions'] = entry[KEY_YAML_FILTER_DISTRIBUTIONS]

            if KEY_YAML_FILTER_VERSIONS in entry:
                filters['pattern_versions'] = entry[KEY_YAML_FILTER_VERSIONS]

            if KEY_YAML_FILTER_FILES in entry:
                filters['pattern_files'] = entry[KEY_YAML_FILTER_FILES]
            filtered = command.filter(**filters)

            # file download processing
            if KEY_YAML_DOWNLOAD in entry:
                entry_download = entry[KEY_YAML_DOWNLOAD]

                if KEY_YAML_FILENAME_ONLY in entry_download:
                    filename_only = entry_download[KEY_YAML_FILENAME_ONLY]
                else:
                    filename_only = False

                if KEY_YAML_PATH in entry_download:
                    # create directory if necessary
                    if KEY_YAML_MKDIR in entry_download and not os.path.isdir(entry_download[KEY_YAML_PATH]):
                        os.mkdir(entry_download[KEY_YAML_PATH])

                    # download newer files only
                    if KEY_YAML_NEWER_ONLY in entry_download:
                        newer_only = entry_download[KEY_YAML_NEWER_ONLY]
                    else:
                        newer_only = False

                    # download file
                    download(entry_download[KEY_YAML_PATH], filtered, filename_only, newer_only)

            # store as JSON
            if KEY_YAML_JSON in entry:
                write_file(entry[KEY_YAML_JSON], filtered.json())

            # store as YAML
            if KEY_YAML_YAML in entry:
                write_file(entry[KEY_YAML_YAML], filtered.yaml())

    else:
        if args.filter:
            command = command.filter(pattern_files=args.filter)

        if args.download:
            download(args.download, command)

        if args.json:
            write_file(args.json, command.json())

        if args.yaml:
            write_file(args.yaml, command.yaml())


if __name__ == '__main__':
    main()
