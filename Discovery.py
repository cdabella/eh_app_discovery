class Discoverer(object):
    """An application disc"""

    import httplib

    def __init__(self, apikey='', host=''):
        self.apikey = apikey
        self.host   = host

    def get_devices_by_type(self, type):
        _eh_api_get('/api/v1/devices?' +
                    'limit=0&' +
                    'search_type=type&' +
                    'value='+ type + '&' +
                    'active_from=-86400000&' +
                    'active_until=0')

    def tag_by_metric_identifier(self, metric, key, tag):

        # Check that tag exists



    def _eh_api_get(self, path):
        headers = {'Accept': 'application/json',
                   'Authorization': 'ExtraHop apikey=' + self.apikey}
        conn = httplib.HTTPSConnection(self.host)
        conn.request('GET', path, headers=headers)
        resp = conn.getresponse()
        if (resp.status != 200):
            raise ValueError('Non-200 status code from API request', resp.status, resp.reason)
        else:
            return resp.read()

    def _eh_api_post(self, path, body):
        headers = {'Accept': 'application/json',
                   'Authorization': 'ExtraHop apikey=' + self.apikey}
        conn = httplib.HTTPSConnection(self.host)
        conn.request('POST', path, headers=headers, body=body)
        resp = conn.getresponse()
        if (resp.status > 299):
            raise ValueError('Non-200s status code from API request', resp.status, resp.reason)
        else:
            return resp.read()



    def _make_tag(self, tag):
        # Check that tag exist

        tags = _eh_api_get('/api/v1/tags')
        for t in tags:
            if (t.name == tag):
                return t.id

        # Tag does not exist
        _eh_api_post('/api/v1/tags', {"name": tag})

        "
