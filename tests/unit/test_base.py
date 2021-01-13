import json
from unittest.mock import Mock

import pytest
from marshmallow import ValidationError

from loadbalancer_interface.base import (
    HealthCheck,
    Request,
    Response,
)


def test_request():
    app = Mock(name='app')
    relation = Mock(name='relation', data={app: {}})
    with pytest.raises(TypeError):
        Request()
    with pytest.raises(TypeError):
        Request(app, relation, 'foo')
    with pytest.raises(ValidationError):
        Request(app, relation,
                name='name',
                traffic_type='https',
                backend_ports=['none'])
    with pytest.raises(ValidationError):
        Request(app, relation,
                name='name',
                traffic_type='https',
                backend_ports=[443],
                foo='bar')

    req = Request(app, relation,
                  name='name',
                  traffic_type='https',
                  backend_ports=[443])
    assert req.health_checks == []

    req_foo_d = json.dumps({
        'name': 'foo',
        'traffic_type': 'https',
        'backends': [],
        'backend_ports': [443],
        'algorithm': [],
        'sticky': False,
        'health_checks': [{
            'traffic_type': 'https',
            'port': 443,
            'path': None,
            'interval': 30,
            'retries': 3,
        }],
        'public': True,
        'tls_termination': False,
        'tls_cert': None,
        'tls_key': None,
        'ingress_address': None,
        'ingress_ports': [],
    }, sort_keys=True)
    req_bar_d = json.dumps({
        'name': 'bar',
        'traffic_type': 'udp',
        'backend_ports': [4444],
    }, sort_keys=True)
    resp_bar_d = json.dumps({
        'name': 'bar',
        'success': True,
        'address': 'lb',
        'request_hash': '',
    }, sort_keys=True)
    hc = HealthCheck(traffic_type='https', port=443)
    req_foo = Request(app, relation,
                      name='foo',
                      traffic_type='https',
                      backend_ports=[443],
                      health_checks=[hc])
    assert req_foo.health_checks == [hc]
    assert req_foo.dump() == req_foo_d
    assert req_foo.hash == '5a1e549064d5a2fe10b8b8e25a16afae'

    assert Request.get_all(app, relation) == []
    relation.data[app]['request_bar'] = req_bar_d
    relation.data[app]['response_bar'] = resp_bar_d
    assert Request.get_all(app, relation)[0].traffic_type == 'udp'
    assert Request.get(app, relation, 'bar').response.address == 'lb'
    req_foo.write()
    assert Request.get_all(app, relation)[1].name == 'foo'
    assert Request.get(app, relation, 'foo').dump() == req_foo_d


def test_response():
    app = Mock(name='app')
    relation = Mock(name='relation', data={app: {}})
    with pytest.raises(TypeError):
        Response()
    with pytest.raises(TypeError):
        Response(app, relation, 'foo')
    with pytest.raises(ValidationError):
        Response(app, relation,
                 name='name',
                 success=True,
                 address=None,
                 request_hash=None)
    with pytest.raises(ValidationError):
        Response(app, relation,
                 name='name',
                 success=True,
                 address='https://my-lb.aws.com/',
                 response_hash='',
                 foo='bar')
    with pytest.raises(ValidationError):
        Response(app, relation,
                 name='name',
                 success=False,
                 address='https://my-lb.aws.com/',
                 request_hash='')

    Response(app, relation,
             name='name',
             success=True,
             address='https://my-lb.aws.com/',
             request_hash='')


def test_health_check():
    with pytest.raises(ValidationError):
        HealthCheck()
    with pytest.raises(TypeError):
        HealthCheck('foo')
    with pytest.raises(ValidationError):
        HealthCheck(traffic_type='https',
                    port='none')
    with pytest.raises(ValidationError):
        HealthCheck(traffic_type='https',
                    port=443,
                    foo='bar')

    hc = HealthCheck(traffic_type='https',
                     port=443)
    assert hc.traffic_type == 'https'
    assert hc.port == 443
    assert hc.path is None
    assert hc.interval == 30
    assert hc.retries == 3

    hc = HealthCheck(traffic_type='http',
                     port=80,
                     path='/foo',
                     interval=60,
                     retries=5)
    assert hc.traffic_type == 'http'
    assert hc.port == 80
    assert hc.path == '/foo'
    assert hc.interval == 60
    assert hc.retries == 5
