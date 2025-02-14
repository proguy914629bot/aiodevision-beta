import asyncio
from sys import path
import aiohttp
from io import BytesIO
import imghdr
from .dataclasses import CDN, CDNStats, RTFS, RTFM, UploadStats, XKCD
import typing
from .errors import *
from .baseclasses import *
from .enums import *
from .http import HTTPClient
from .games import Games

class Client:
    def __init__(self, token: typing.Optional[str] = None, *, url: str = "https://idevision.net/", retry: int = 5) -> None:
        self.loop = asyncio.get_event_loop()
        headers = {'Authorization': token.strip()} if token else None
        self.session = aiohttp.ClientSession(headers=headers, raise_for_status = True)
        self.token = token.strip() if token else None
        self.headers = headers
        self.retry = retry
        
        if not url.endswith("/"):
            url = (url + "/")
            
        self.base_url = url
        
        self.http = HTTPClient(self)

    async def rtfs(
        self,
        *,
        query: typing.Optional[str] = None,
        library: typing.Union[LibraryEnum, str] = None,
        format: typing.Union[RTFSFormat, str] = RTFSFormat.links,
    ) -> RTFS:
        """Queries a python module's github link for the query you give and gives relevant github links to what you searched for.

        :param query: The actual query
        :type query: typing.Optional[str]
        :param library: The library to find source for
        :type library: typing.Union[LibraryEnum, str]
        :param format: the format you want the data to be returned as. can be either 'links', which returns the github links, and 'source', which returns the code it self, defaults to 'links'
        :type format: typing.Union[RTFSFormat, str], optional
        :raises UndefinedLibraryError: This library cannot be queried.
        :raises InternalServerError: An Internal Server Error occured while requesting the API.
        :return: A RTFS Class
        :rtype: RTFS
        """
        if not isinstance(library, (LibraryEnum, str)):
            raise UndefinedLibraryError(
                'The Library specficied cannot by queried. Please provide a library from the following list: twitchio, wavelink, discord.py, or aiohttp.'
            )
        library = str(library).lower()
        if library.lower() not in [
            'twitchio',
            'wavelink',
            'aiohttp',
            'discord.py',
            'discord.py-2',
            'discord.py2',
            'dpy',
            'dpy2',
            'dpy-2'
        ]:
            raise UndefinedLibraryError(
                'The Library specficied cannot by queried. Please provide a library from the following list: twitchio, wavelink, discord.py, or aiohttp.'
            )
        params = {'library': library, 'format': format}
        if query:
            params['query'] = query
        async with self.session.get(
            'https://idevision.net/api/public/rtfs', params=params
        ) as resp:
            if resp.status == 500:
                raise InternalServerError(
                    'An Internal Server Error occured.'
                    ' Please join the discord server https://discord.gg/D3Nfau4ThK and scream at IAmTomahawkx#1000'
                    " about why the RTFS endpoint doesn't work."
                )
            data = await resp.json()
        return RTFS(data['nodes'])

    async def rtfm(
        self,
        *,
        query: typing.Optional[str] = None,
        doc_url: str,
    ) -> RTFM:
        """Searches a sphinx documentation url for methods and classes that match your query.

        :param query: [
        :type query: typing.Optional[str]
        :param doc_url: [description]
        :type doc_url: str
        :raises InvalidDocumentation: [description]
        :return: [description]
        :rtype: RTFM
        """
        async with self.session.get(doc_url + '/objects.inv') as resp:
            if resp.status == 404:
                raise InvalidDocumentation(
                    'The documentation you provided cannot be provided. Please provide documentation made with spehin'
                )
        params = {'query': query, 'location': doc_url}
        async with self.session.get(
            'https://idevision.net/api/public/rtfm', params=params
        ) as resp:
            data = await resp.json()
        return RTFM(data['nodes'], float(data['query_time']))
    
    @property
    def _reload_http(self) -> HTTPClient:
        http_client = HTTPClient(self)
        self.http = http_client
        return http_client
    
    @property
    def games(self):
        return Games(self)

    async def ocr(self, image: BytesIO) -> str:
        if not self.token:
            raise TokenRequired('A Token is required to access this endpoint')
        filetype = imghdr.what(image.read(), h=image.read())
        if filetype is None:
            raise InvalidImage(
                'The Image you provided is invalid. Please provide a valid image'
            )
        params: typing.Dict[str, typing.Union[str]] = {'filetype': filetype}
        async with self.session.get(
            'https://idevision.net/api/public/ocr',
            params=params,
            data=image,
        ) as resp:
            if resp.status == 500:
                raise InternalServerError(
                    'An Internal Server Error occured.'
                    ' Please join the discord server https://discord.gg/D3Nfau4ThK and scream at IAmTomahawkx#1000'
                    " about why the OCR endpoint doesn't work."
                )
            data = await resp.json()
        return data['data']

    async def xkcd(self, query: str) -> XKCD:
        params = {'query': query}
        async with self.session.get(
            'https://idevision.net/api/public/xkcd', params=params
        ) as resp:
            data = await resp.json()
        return XKCD(data['nodes'], float(data['query_time']))

    async def xkcd_tags(self, word: str, num: int) -> str:
        payload = {'tag': word, 'num': num}
        async with self.session.put(
            'https://idevision.net/api/public/xkcd/tags', data=payload
        ):
            return 'Succesfully added tags to xkcd comic'

    async def hompage(self, payload: typing.Dict[str, str]):
        if not self.token:
            raise TokenRequired('A Token is required to access this endpoint.')
        async with self.session.post(
            'https://idevision.net/api/homepage', data=payload
        ):
            return 'Successfully set up homepage'

    async def cdn_upload(self, image: BytesIO) -> CDN:
        if not self.token:
            raise TokenRequired('A Token is required to access this endpoint')
        ext = imghdr.what(image.read(), h=image.read())
        if ext is None:
            raise InvalidImage(
                'The Image you provided is invalid. Please provide a valid image'
            )
        headers: typing.Dict[str, str] = {
            'File-Name': 'aiodevision.{0}'.format(ext)
        }
        async with self.session.post(
            'https://idevision.net/', data=image, headers=headers
        ) as resp:
            data: typing.Dict[str, str] = await resp.json()
        return CDN(data)

    async def cdn_stats(self) -> CDNStats:
        async with self.session.get('https://idevision.net/api/cdn') as resp:
            data = await resp.json()
        return CDNStats(data)

    async def get_upload_stats(self, node: str, slug: str):
        if not self.token:
            raise TokenRequired('A Token is required to access this endpoint')
        async with self.session.get(
            'https://idevision.net/api{0}/{1}'.format(node, slug)
        ) as resp:
            data = await resp.json()
            return UploadStats(data)

    async def delete_cdn(self, node: str, slug: str) -> str:
        if not self.token:
            raise TokenRequired('A Token is required to access this endpoint')
        url = 'https://idevision.net/api/{0}/{1}'.format(node, slug)
        async with self.session.delete(url):
            return 'Succesfully deleted upload'
