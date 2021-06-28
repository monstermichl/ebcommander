from __future__ import annotations # Used to state return types of own class within a class

import requests;
import re
import json
import copy
import os
import unicodedata

from datetime     import datetime
from bs4          import BeautifulSoup, Tag
from typing       import List
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from enum         import Enum
from yaml         import dump


PATTERN_ANY_CHAR = r'\.*'


class SizeUnit(Enum):
    """
    The SizeUnit enum represents file size units
    """
    UNKNOWN    = 0
    BYTE       = 1
    KILO_BYTE  = 2
    MEGA_BYTE  = 3
    GIGA_BYTE  = 4
    TERRA_BYTE = 5


class Size:
    """
    The Size class represents a file size by its value and by its unit
    """
    def __init__(self, value: float, unit: SizeUnit) -> None:
        """
        Size constructor

        :param value: Size value
        :type value: float
        :param unit: Size unit
        :type unit: SizeUnit
        """
        self.value = value
        self.unit  = unit

    @staticmethod
    def parse(s: str) -> Size | None:
        """
        Creates Size object from a size string

        :param s: String to parse (e.g. 2.4 MB, 643B, 6.2kB, ...)
        :type s: str
        :return: Size object if successful, otherwise None
        :rtype: Size
        """
        s    = re.sub('\s+', '', s.strip())
        size = re.match(r'^((\d+)(\.\d+)?)(\w+)$', s)

        if size:
            value      = float(size.group(1))
            unit       = None
            first_char = size.group(4)[0].upper()

            for entry in (
                ('B', SizeUnit.BYTE      ),
                ('K', SizeUnit.KILO_BYTE ),
                ('M', SizeUnit.MEGA_BYTE ),
                ('G', SizeUnit.GIGA_BYTE ),
                ('T', SizeUnit.TERRA_BYTE),
            ):
                if first_char == entry[0]:
                    unit = entry[1]
                    break

            if unit:
                size = Size(value, unit)
            else:
                size = None
        return size


class Sublink:
    """
    The Sublink class represents an HTML href-tag but also stores its text, its full
    URL - based on the URL base path - and its parameters
    """
    def __init__(self, url_base: str, tag: Tag) -> None:
        """
        Sublink constructor

        :param url_base: URL base (e.g. http://localhost)
        :type url_base: str
        :param tag: BeautifulSoup4 href tag
        :type tag: Tag
        """
        self.url_base    = url_base
        self.tag         = tag
        self.description = re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', self.tag.text.strip()))
        self.href        = tag.attrs.get('href')
        self.url         = urljoin(self.url_base, self.href)

        url_parsed = urlparse(self.href)

        self.path   = url_parsed.path
        self.params = { key: value[0] for key, value in parse_qs(url_parsed.query).items() }


class EbCommandSublink(Sublink):
    """
    The EbCommandSublink class inherits from Sublink. It contains (if found) tag siblings
    information (e.g. upload time, size) which belong to the downloadable EB file
    """
    def __init__(self, url_base: str, tag: Tag) -> None:
        """
        EbCommandlink constructor

        :param url_base: URL base (e.g. http://localhost)
        :type url_base: str
        :param tag: BeautifulSoup4 href tag
        :type tag: Tag
        """
        super().__init__(url_base, tag)

        table_row = self.tag.find_parent('tr')
        if table_row:
            for table_data in table_row.find_all('td'):
                if hasattr(table_data, 'text'):
                    text        = table_data.text.strip()
                    upload_time = re.match(r'(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})', text)
                    size        = Size.parse(text)

                    if upload_time:
                        self.upload_time = datetime(int(upload_time.group(1)),
                                                    int(upload_time.group(2)),
                                                    int(upload_time.group(3)),
                                                    int(upload_time.group(4)),
                                                    int(upload_time.group(5)),
                                                    int(upload_time.group(6)))
                    elif size:
                        self.size = size


class EbCommandEntry:
    """
    The EbCommandEntry class represents the base class for an entry in the EbCommand
    hierarchy (e.g. project, distribution, version, file)
    """
    def __init__(self, sublink: EbCommandSublink, id: int, subentry_type: type = None, subentries: list = None) -> None:
        """
        EbCommandEntry constructor

        :param sublink: EbCommandSublink which represents the actual entry location
        :type sublink: EbCommandSublink
        :param id: EB Command reference id
        :type id: int
        :param subentry_type: Specifies of which type the subentries are. Defaults to None
        :type subentry_type: type, optional
        :param subentries: List of subentries. Defaults to None
        :type subentries: list, optional
        """
        self.sublink     = sublink
        self.description = sublink.description
        self.id          = id
        self.subentries  = []

        self.add_subentries(subentries, subentry_type)

    def add_subentries(self, subentries: list, subentry_type: type):
        """
        Adds a new subentry

        :param subentries: A list of subentries or a single entry of the given subentry-type
        :type subentries: list
        :param subentry_type: Subentry type
        :type subentry_type: type
        """
        if subentries is not None and subentry_type is not None:
            if isinstance(subentries, subentry_type):
                self.subentries.append(subentries)
            elif isinstance(subentries, list) or isinstance(subentries, tuple):
                for subfolder in subentries:
                    self.add_subentries(subfolder, subentry_type)

    def to_dict(self, sub_description: str = 'sub') -> dict:
        """
        Creates a dictionary representation of the object

        :param sub_description: Key description of the subentry list. Defaults to 'sub'
        :type sub_description: str, optional
        :return: Dictionary representation of the object
        :rtype: dict
        """
        KEY_DESCRIPTION = 'description'
        KEY_ID          = 'id'
        KEY_URL         = 'url'
        KEY_SUBFOLDER   = sub_description
        dictionary      = \
        {
            KEY_DESCRIPTION: self.description,
            KEY_ID         : self.id,
            KEY_URL        : self.sublink.url,
        }

        if len(self.subentries) > 0:
            dictionary[KEY_SUBFOLDER] = [subfolder.to_dict() for subfolder in self.subentries]
        return dictionary

    def filter(self, subs_patterns: List[str]) -> EbCommandEntry:
        """
        Filters all subentries based on their descriptions

        :param subs_patterns: List of patterns where each pattern is applicable for a subentry layer
        :type subs_patterns: List[str]
        :return: If all patterns found at least one element a copy of the filtered object is returned, otherwise None
        :rtype: EbCommandEntry
        """
        self_copy  = copy.copy(self)
        subentries = []
        
        if len(subs_patterns) > 0:
            for subentry in self_copy.subentries:
                if len(subs_patterns) > 1:
                    subentry = subentry.filter(subs_patterns[1:])
                
                if subentry:
                    if re.match(subs_patterns[0], subentry.description):
                        subentries.append(subentry)
                    else:
                        subentry = None

            # refill sufolders (done this way instead of using self_copy.subfolders = subfolders,
            # to keep referenced lists (distributions, version, files, ...) up-to-date)
            self_copy.subentries.clear()
            self_copy.subentries.extend(subentries)

        return self_copy if len(self_copy.subentries) > 0 else None


class EbCommandFile(EbCommandEntry):
    """
    The EbCommandFile class represents a file in the EbCommand hierarchy
    """
    def __init__(self, sublink: Sublink, id: int) -> None:
        """
        EbCommandFile constructor

        :param sublink: EbCommandSublink which represents the actual entry location
        :type sublink: Sublink
        :param id: EB Command reference id
        :type id: int
        """
        super().__init__(sublink, id)
        
        self.upload_time = sublink.upload_time
        self.size        = sublink.size

    def to_dict(self) -> dict:
        """
        Creates a dictionary representation of the object

        :return: Dictionary representation of the object
        :rtype: dict
        """
        KEY_UPLOAD_TIME = 'upload-time'
        KEY_SIZE        = 'size'

        dictionary = super().to_dict()

        dictionary[KEY_UPLOAD_TIME] = self.upload_time.strftime(f'%Y-%m-%d %H:%M:%S')

        for entry in (
            (SizeUnit.BYTE      ,  'B'),
            (SizeUnit.KILO_BYTE , 'KB'),
            (SizeUnit.MEGA_BYTE , 'MB'),
            (SizeUnit.GIGA_BYTE , 'GB'),
            (SizeUnit.TERRA_BYTE, 'TB'),
        ):
            if self.size.unit == entry[0]:
                dictionary[KEY_SIZE] = f'{self.size.value} {entry[1]}'
                break
        return dictionary



class EbCommandVersion(EbCommandEntry):
    """
    The EbCommandVersion class represents a distribution version in the EbCommand hierarchy.
    """
    def __init__(self, sublink: Sublink, id: int, files: List[EbCommandFile] = None) -> None:
        """
        EbCommandVersion constructor

        :param sublink: EbCommandSublink which represents the actual entry location
        :type sublink: Sublink
        :param id: EB Command reference id
        :type id: int
        :param files: List of version files. Defaults to None
        :type files: List[EbCommandFile], optional
        """
        super().__init__(sublink, id, EbCommandFile, files)
        self.files = self.subentries

    def add_files(self, files: List[EbCommandFile]):
        """
        Adds file entries

        :param files: A list of files or a single file entry
        :type files: List[EbCommandFile]
        """
        self.add_subentries(files, EbCommandFile)

    def to_dict(self) -> dict:
        """
        Creates a dictionary representation of the object

        :return: Dictionary representation of the object
        :rtype: dict
        """
        return super().to_dict(sub_description='files')


class EbCommandDistribution(EbCommandEntry):
    """
    The EbCommandDistribution class represents a distribution in the EbCommand hierarchy.
    """
    def __init__(self, sublink: Sublink, id: int, versions: List[EbCommandVersion] = None) -> None:
        super().__init__(sublink, id, EbCommandVersion, versions)
        self.versions = self.subentries

    def add_versions(self, versions: List[EbCommandVersion]):
        """
        Adds version entries

        :param versions: A list of versions or a single version entry
        :type versions: List[EbCommandVersion]
        """
        self.add_subentries(versions, EbCommandVersion)

    def to_dict(self) -> dict:
        """
        Creates a dictionary representation of the object

        :return: Dictionary representation of the object
        :rtype: dict
        """
        return super().to_dict(sub_description='versions')


class EbCommandProject(EbCommandEntry):
    """
    The EbCommandProject class represents a project in the EbCommand hierarchy.
    """
    def __init__(self, sublink: Sublink, id: int, distributions: List[EbCommandDistribution] = None) -> None:
        super().__init__(sublink, id, EbCommandDistribution, distributions)
        self.distributions = self.subentries

    def add_distributions(self, distributions: List[EbCommandDistribution]):
        """
        Adds distribution entries

        :param distributions: A list of distributions or a single distribution
        :type distributions: List[EbCommandDistribution]
        """
        self.add_subentries(distributions, EbCommandDistribution)

    def to_dict(self) -> dict:
        """
        Creates a dictionary representation of the object

        :return: Dictionary representation of the object
        :rtype: dict
        """
        return super().to_dict(sub_description='distributions')


class EbCommandDownloadFile:
    """
    The EbCommandDownloadFile is a collection of all necessary information to download
    a file from EBCommand.
    """
    def __init__(self, file: EbCommandFile, version: EbCommandVersion, distribution: EbCommandDistribution, project: EbCommandProject) -> None:
        """
        EbCommandDownloadFile constructor

        :param file: EbCommandFile
        :type file: EbCommandFile
        :param version: EbCommandVersion to which the file belongs
        :type version: EbCommandVersion
        :param distribution: EbCommandDistribution to which the version belongs
        :type distribution: EbCommandDistribution
        :param project: EbCommandProject to which the distribution belongs
        :type project: EbCommandProject
        """
        self.file         = file
        self.version      = version
        self.distribution = distribution
        self.project      = project
        self.description  = self.file.description
        self.url          = self.file.sublink.url

    def __str__(self) -> str:
        """
        Returns a string representation of the object

        :return: String representation of the object
        :rtype: str
        """
        s = ''
        for i, description in enumerate([
            self.project.description     ,
            self.distribution.description,
            self.version.description     ,
            self.description
        ]):
            s = s + ('-' if i > 0 else '') + description.replace('\\', '-').replace('/', '-')
        return s


class EbCommand:
    """
    The EbCommand class represents the interface to interact with the Elekrobit Command Server.
    """

    # URL information
    _URL_BASE             = 'https://command.elektrobit.com/command/mod_perl/'
    _PATH_LOGIN           = 'login.pl'
    _PATH_DEPLOY          = 'deploy.pl'
    _PATH_ATTACHMENT      = 'attachment.pl'

    # HTML param keys
    _KEY_DO               = 'Do'
    _KEY_USER             = 'Al'
    _KEY_PASSWORD         = 'Passwd'
    _KEY_PROJECT_ID       = 'ProjectId'
    _KEY_ID               = 'Id'

    # DO types
    _DO_TYPE_LOGIN        = 'LOGIN'
    _DO_TYPE_DISTRIBUTION = 'DISTR'
    _DO_TYPE_VERSION      = 'VERSION'
    _DO_TYPE_GET          = 'GET'

    # patterns
    _PATTERN_ID           = r'\d+'

    def __init__(self, user: str, password: str, proxy_http: str = None, proxy_https: str = None) -> None:
        """
        EbCommand constructor

        :param user: EB Command username
        :type user: str
        :param password: EB Command user password
        :type password: str
        :param proxy_http: HTTP proxy address (e.g. http://localhost:1234). Defaults to None
        :type proxy_http: str, optional
        :param proxy_https: HTTPS proxy address (e.g. https://localhost:1234). Defaults to None
        :type proxy_https: str, optional
        """
        self._session     = None
        self._user        = user
        self._password    = password
        self._proxies     = {}

        if proxy_http:
            self._proxies['http'] = proxy_http
        if proxy_https:
            self._proxies['https'] = proxy_https

        self._projects    = self._get_projects()

    def files(self) -> List[EbCommandDownloadFile]:
        """
        Returns a list of downloadable files

        :return: List of downloadable files
        :rtype: List[EbCommandDownloadFile]
        """
        download_files = []
        for project in self._projects:
            for distribution in project.distributions:
                for version in distribution.versions:
                    for file in version.files:
                        download_files.append(EbCommandDownloadFile(file, version, distribution, project))
        return download_files

    def json(self) -> str:
        """
        Returns a JSON representation of the object

        :return: JSON representation of the object
        :rtype: str
        """
        return json.dumps([project.to_dict() for project in self._projects], indent=3)

    def yaml(self) -> str:
        """
        Returns a YAML representation of the object

        :return: YAML representation of the object
        :rtype: str
        """
        return dump([project.to_dict() for project in self._projects])

    def download(self, path_output: str, filename_only: bool = False):
        """
        Downloads the retrieved files to the specified folder

        :param path_output: Output path
        :type path_output: str
        :param filename_only: If true, only the file description is used as filename, otherwise the filename is a combination of project, distribution, version and file description. Defaults to False
        :type filename_only: bool, optional
        """
        for download_file in self.files():
            content = self._request(download_file.url)

            if content:
                if not filename_only:
                    file_name = str(download_file)
                else:
                    file_name = download_file.description
                    
                path_file = os.path.join(path_output, file_name)
                with open(path_file, 'wb') as f:
                    f.write(content)

    def filter(self, pattern_projects     : str = PATTERN_ANY_CHAR,
                     pattern_distributions: str = PATTERN_ANY_CHAR,
                     pattern_versions     : str = PATTERN_ANY_CHAR,
                     pattern_files        : str = PATTERN_ANY_CHAR) -> EbCommand:
        """
        Returns a copy of the current object with a filtered project list

        :param pattern_projects: Regex pattern to filter projects. Defaults to PATTERN_ANY_CHAR
        :type pattern_projects: str, optional
        :param pattern_distributions: Regex pattern to filter distributions. Defaults to PATTERN_ANY_CHAR
        :type pattern_distributions: str, optional
        :param pattern_versions: Regex pattern to filter versions. Defaults to PATTERN_ANY_CHAR
        :type pattern_versions: str, optional
        :param pattern_files: Regex pattern to filter files. Defaults to PATTERN_ANY_CHAR
        :type pattern_files: str, optional
        :return: Copy of the current object with a filtered project list
        :rtype: EbCommand
        """
        self_copy = copy.copy(self)
        projects  = []

        for project in self._projects:
            if re.match(pattern_projects, project.description):
                project = project.filter([pattern_distributions, pattern_versions, pattern_files])

                if project:
                    projects.append(project)
        
        self_copy._projects = projects
        return self_copy

    def _filter_duplicates(self, folders: List[EbCommandEntry]) -> List[EbCommandEntry]:
        """
        Filters EbCommandFolder duplicates. Duplicates could appear if the parsed page contains several links to the same folder

        :param folders: EbCommandFolder list (e.g. project, distribution, ...)
        :type folders: List[EbCommandEntry]
        :return: EbCommandFolder list without duplicates
        :rtype: List[EbCommandEntry]
        """
        for i in reversed(range(0, len(folders))):
            filtered = list(filter(lambda x: x.id == folders[i].id, folders))

            if len(filtered) > 1:
                del folders[i]
        return folders


    def _get_projects(self) -> List[EbCommandProject]:
        """
        Retrieves all projects from EB Command

        :return: List of retrieved projects
        :rtype: List[EbCommandProject]
        """
        projects = []
        html     = self._request(EbCommand._PATH_LOGIN,
        {
            EbCommand._KEY_DO      : EbCommand._DO_TYPE_LOGIN,
            EbCommand._KEY_USER    : self._user              ,
            EbCommand._KEY_PASSWORD: self._password
        }, post=True)

        for sublink in self._get_sublinks(html, EbCommand._PATH_DEPLOY, { EbCommand._KEY_PROJECT_ID: EbCommand._PATTERN_ID }):
            project = EbCommandProject(sublink, int(sublink.params[EbCommand._KEY_PROJECT_ID]))

            project.add_distributions(self._get_distributions(project))
            projects.append(project)
        return self._filter_duplicates(projects)

    def _get_distributions(self, project: EbCommandProject) -> List[EbCommandDistribution]:
        """
        Retrieves all distributions of the given project from EB Command

        :param project: Project from which to get the distributions
        :type project: EbCommandProject
        :return: List of project distributions
        :rtype: List[EbCommandDistribution]
        """
        distributions = []
        html          = self._request(EbCommand._PATH_DEPLOY, { EbCommand._KEY_PROJECT_ID: project.id }, post=False)

        for sublink in self._get_sublinks(html, EbCommand._PATH_DEPLOY, { EbCommand._KEY_DO: EbCommand._DO_TYPE_DISTRIBUTION, EbCommand._KEY_ID: EbCommand._PATTERN_ID }):
            distribution = EbCommandDistribution(sublink, int(sublink.params[EbCommand._KEY_ID]))

            distribution.add_versions(self._get_versions(distribution))
            distributions.append(distribution)
        return self._filter_duplicates(distributions)

    def _get_versions(self, distribution: EbCommandDistribution) -> List[EbCommandVersion]:
        """
        Retrieves all versions of the given distribution from EB Command

        :param distribution: Distribution from which to get the versions
        :type distribution: EbCommandDistribution
        :return: List of distribution versions
        :rtype: List[EbCommandVersion]
        """
        versions = []
        html     = self._request(EbCommand._PATH_DEPLOY, { EbCommand._KEY_DO: EbCommand._DO_TYPE_DISTRIBUTION, EbCommand._KEY_ID: distribution.id }, post=False)

        for sublink in self._get_sublinks(html, EbCommand._PATH_DEPLOY, { EbCommand._KEY_DO: EbCommand._DO_TYPE_VERSION, EbCommand._KEY_ID: EbCommand._PATTERN_ID }):
            version = EbCommandVersion(sublink, int(sublink.params[EbCommand._KEY_ID]))

            version.add_files(self._get_files(version))
            versions.append(version)
        return self._filter_duplicates(versions)

    def _get_files(self, version: EbCommandVersion) -> List[EbCommandFile]:
        """
        Retrieves all files of the given version from EB Command

        :param version: Version from which to get the files
        :type version: EbCommandVersion
        :return: List of version files
        :rtype: List[EbCommandFile]
        """
        files = []
        html  = self._request(EbCommand._PATH_DEPLOY, { EbCommand._KEY_DO: EbCommand._DO_TYPE_VERSION, EbCommand._KEY_ID: version.id }, post=False)

        for sublink in self._get_sublinks(html, EbCommand._PATH_ATTACHMENT, { EbCommand._KEY_DO: EbCommand._DO_TYPE_GET, EbCommand._KEY_ID: EbCommand._PATTERN_ID }):
            file = EbCommandFile(sublink, int(sublink.params[EbCommand._KEY_ID]))
            files.append(file)
        return self._filter_duplicates(files)

    def _get_sublinks(self, html_element: Tag, path: str, conditions: dict) -> List[EbCommandSublink]:
        """
        Gets all sublinks (href links) below a specific element which fulfills the given conditions

        :param html_element: BeautifulSoup4 tag below which the sublinks are searched
        :type html_element: Tag
        :param path: URL subpath (e.g. deploy.pl)
        :type path: str
        :param conditions: Parameters and according patterns the href must contain
        :type conditions: dict
        :return: List of sublinks which fulfil the given conditions
        :rtype: List[EbCommandSublink]
        """
        sublinks = []

        for tag_link in html_element.find_all('a'):
            sublink = self._parse_sublink(tag_link, path, conditions)

            if sublink:
                sublinks.append(sublink)
        return sublinks

    def _parse_sublink(self, tag: Tag, path: str, conditions: dict) -> EbCommandSublink | None:
        """
        Parses a sublink (href) and returns a EbCommandSublink if all conditons are fulfilled

        :param tag: BeautifulSoup4 href tag
        :type tag: Tag
        :param path: URL subpath (e.g. deploy.pl)
        :type path: str
        :param conditions: parameters and according patterns the href must contain
        :type conditions: dict
        :return: EbCommandSublink if all conditions were fulfilled, otherwise None
        :rtype: EbCommandSublink
        """
        sublink = EbCommandSublink(EbCommand._URL_BASE, tag)
        ok      = True

        # check if conditions are met
        for key, value in conditions.items():
            if sublink.path != path or not (key in sublink.params.keys() and re.match(value, sublink.params.get(key))):
                ok = False
                break

        if not ok:
            sublink = None
        return sublink


    def _build_url(self, path: str, params: dict = None) -> str:
        """
        Builds EB Command URL with the given path (e.g. deploy.pl) and parameters

        :param path: URL subpath (e.g. deploy.pl)
        :type path: str
        :param params: Dictionary with parameter names and values. Defaults to None
        :type params: dict, optional
        :return: EB Command URL
        :rtype: str
        """
        return urljoin(EbCommand._URL_BASE, path + (f'?{urlencode(params)}' if params else ''))

    def _request(self, path: str, data: dict = None, post: bool = False) -> Tag | any | None:
        """
        Requests data from EB Command

        :param path: URL subpath (e.g. deploy.pl)
        :type path: str
        :param data: Dictionary with parameter names and values. Defaults to None
        :type data: dict, optional
        :param post: If true, a POST request is sent, otherwise a GET request. Defaults to False
        :type post: bool, optional
        :return: If the request was successful and the returned data was HTML, a BeautifulSoup4 tag element. If the request was successful and the returned data was not HTML, the requested content. Else, None
        :rtype: any
        """
        params_common = { 'proxies': self._proxies, 'verify': False }
        content       = None

        if not self._session:
            self._session = requests.Session()

        if post:
            result = self._session.post(self._build_url(path), data=data, **params_common)
        else:
            result = self._session.get(self._build_url(path, data), **params_common)

        if result.status_code == 200:
            content_type = result.headers.get('content-type').lower()

            if 'html' in content_type:
                content = BeautifulSoup(result.content.decode(result.encoding))
            else:
                content = result.content
        return content
