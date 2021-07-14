import re

from os import system


FILE_SETUP = 'setup.cfg'


class Version:
    def __init__(self, description: str, version: int = 0) -> None:
        self.description = description
        self.version     = version


version_major = Version('Major')
version_minor = Version('Minor')
version_patch = Version('Patch')

# Ask for versions
for version in (version_major, version_minor, version_patch):
    input_version = input(f'{version.description} version: ')
    if not re.match(r'\d+', input_version):
        Exception('Invalid version input')
    else:
        version.version = int(input_version)

content = None

# Read setup.cfg
with open(FILE_SETUP, 'r') as f:
    content = f.read()

if content:
    result = None

    # Write updated setup.cfg and create tag
    with open(FILE_SETUP, 'w') as f:
        string_version = f'{version_major.version}.{version_minor.version}.{version_patch.version}'
        string_tag     = f'v{string_version}'
        content        = re.sub(r'\s*version\s*=\s*.*', f'version = {string_version}', content)
        
        f.write(content)
        result = system(f'git commit {FILE_SETUP} -m "Create tag version {string_version}')

    if result == 0:
        result = system(f'git tag {string_tag}')
    else:
        print(f'Error while committing {FILE_SETUP} changes')

    # If tagging ok, push if allowed
    if result == 0:
        print(f'Tag {string_tag} created')

        input_push = input('Push tag [y/n]? ').lower()
        if len(input_push) > 0 and input_push[0] == 'y':
            if system(f'git push origin {string_tag}') == 0:
                print(f'Tag {string_tag} pushed')
            else:
                print(f'Error while pushing tag {string_tag}')
        else:
            print(f'Tag {string_tag} was not pushed')
    else:
        print(f'Error while creating tag {string_tag}')
