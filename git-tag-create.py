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
    string_version = f'{version_major.version}.{version_minor.version}.{version_patch.version}'
    content        = f.read()
    content_new    = re.sub(r'version\s*=\s*.*', f'version = {string_version}', content)

if not content:
    print(f'File {FILE_SETUP} not found')
elif content_new == content:
    print(f'Version {string_version} already exists')
elif content_new != content:

    # Write updated setup.cfg
    with open(FILE_SETUP, 'w') as f:
        f.write(content_new)
        
        # Commit setup.cfg change
        if system(f'git commit {FILE_SETUP} -m "Create tag version {string_version}') != 0:
            print(f'Error while committing {FILE_SETUP} changes')
            
        else:
            string_tag = f'v{string_version}'

            # Create tag
            if system(f'git tag {string_tag}') == 0:
                print(f'Tag {string_tag} created')

                input_push = input('Push tag [y/n]? ').lower()
                if len(input_push) > 0 and input_push[0] == 'y':

                    # Push tag
                    if system(f'git push origin {string_tag}') == 0:
                        print(f'Tag {string_tag} pushed')
                    else:
                        print(f'Error while pushing tag {string_tag}')
                else:
                    print(f'Tag {string_tag} was not pushed')
            else:
                print(f'Error while creating tag {string_tag}')
