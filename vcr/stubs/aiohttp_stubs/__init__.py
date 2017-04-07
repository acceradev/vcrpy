'''Stubs for aiohttp HTTP clients'''
from __future__ import absolute_import

import asyncio
import functools
import json
import time

from aiohttp import ClientResponse
from yarl import URL

from vcr.request import Request


class MockClientResponse(ClientResponse):
    # TODO: get encoding from header
    @asyncio.coroutine
    def json(self, *, encoding='utf-8', loads=json.loads):  # NOQA: E999
        return loads(self.content.decode(encoding))

    @asyncio.coroutine
    def text(self, encoding='utf-8'):
        return self.content.decode(encoding)

    @asyncio.coroutine
    def release(self):
        pass


def vcr_request(cassette, real_request):
    @functools.wraps(real_request)
    @asyncio.coroutine
    def new_request(self, method, url, **kwargs):
        headers = kwargs.get('headers')
        headers = self._prepare_headers(headers)
        data = kwargs.get('data')
        params = kwargs.get('params')
        if params:
            for k, v in params.items():
                params[k] = str(v)

        request_url = URL(url).with_query(params)
        vcr_request = Request(method, str(request_url), data, headers)

        if cassette.can_play_response_for(vcr_request):
            vcr_response = cassette.play_response(vcr_request)

            response = MockClientResponse(method, URL(vcr_response.get('url')))
            response.status = vcr_response['status']['code']
            response.content = vcr_response['body']['string']
            response.reason = vcr_response['status']['message']
            response.headers = vcr_response['headers']
            response.latency = vcr_response['latency']

            response.close()
            return response

        if cassette.write_protected and cassette.filter_request(vcr_request):
            # TODO: throw error instead of 599 code
            # it will be more simple to identify if we should interrupt connection
            response = MockClientResponse(method, URL(url))
            response.status = 599
            msg = ("No match for the request {!r} was found. Can't overwrite "
                   "existing cassette {!r} in your current record mode {!r}.")
            msg = msg.format(vcr_request, cassette._path, cassette.record_mode)
            response.content = msg.encode()
            response.close()
            return response

        request_start = time.perf_counter()
        response = yield from real_request(self, method, url, **kwargs)  # NOQA: E999
        latency = time.perf_counter() - request_start

        vcr_response = {
            'status': {
                'code': response.status,
                'message': response.reason,
            },
            'headers': dict(response.headers),
            'body': {'string': (yield from response.text())},  # NOQA: E999
            'url': response.url,
            'latency': latency
        }
        cassette.append(vcr_request, vcr_response)
        response.latency = latency
        return response

    return new_request
