# .. _persister_example:

import os
from ..serialize import serialize, deserialize


class FilesystemPersister(object):

    @classmethod
    def load_cassette(cls, cassette_path, serializer):
        try:
            requests, responses = [], []
            records_files = [os.path.join(cassette_path, f) for f in os.listdir(cassette_path) if os.path.isfile(os.path.join(cassette_path, f)) and f.endswith('.yml')]
            for file in records_files:
                with open(file) as f:
                    cassette_content = f.read()
                    request, response = deserialize(cassette_content, serializer)
                    requests.append(request)
                    responses.append(response)
            cassette = (requests, responses)
        except IOError:
            raise ValueError('Cassette not found.')
        return cassette

    @staticmethod
    def save_cassette(cassette_path, cassette_dict, serializer):
        data = serialize(cassette_dict, serializer)
        dirname, filename = os.path.split(cassette_path)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(cassette_path, 'w') as f:
            f.write(data)
