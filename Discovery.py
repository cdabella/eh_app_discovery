class Discoverer(object):
    """An application disc"""

    import httplib

    def __init__(self, apikey='', host=''):
        self.apikey = apikey
        self.host   = host

    def get_devices_by_type(self, type):
        return _eh_api_get('/api/v1/devices?' +
                           'limit=0&' +
                           'search_type=type&' +
                           'value='+ type + '&' +
                           'active_from=-86400000&' +
                           'active_until=0')

    def tag_by_metric_identifier(self, metric_category, metric, key, tag):

        # Check that tag exists
        tag_id      = _make_tag(tag)
        device_type = _process_metric_category(metric_category)
        devices     = get_devices_by_type(device_type) 

    def _make_tag(self, tag):
        # Check that tag exist

        tags = _eh_api_get('/api/v1/tags')
        for t in tags:
            if (t.name == tag):
                return t.id

        # Tag does not exist
        _eh_api_post('/api/v1/tags', {"name": tag})

        tags = _eh_api_get('/api/v1/tags')
        for t in tags:
            if (t.name == tag):
                return t.id

    def _process_metric_category(self,metric_category):
        # EH metrics take the form extrahop.[object_type].[metric_category]
        metric_components = metric_category.split('.')

        if (metric_components[0] != 'extrahop'):
            raise ValueError('Unexpected metric_category',metric_category)
        elif (metric_components[1] != 'device'):
            raise ValueError('Tagging occurs at the device level',metric_category)

        mc = metric_components[3].split('_')
        for i in range(0,len(mc)):
            # if mc[i] is server or client, the previous index holds the protocol
            if (mc[i] == 'server' || mc[i] == 'client'):
                return mc[i-1] + '_' + mc[i]


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
