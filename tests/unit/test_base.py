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
        Request(app, relation, 'response', 'foo')
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

    hc = HealthCheck(traffic_type='https', port=443)
    req = Request(app, relation,
                  name='name',
                  traffic_type='https',
                  backend_ports=[443],
                  health_checks=[hc])
    assert req.health_checks == [hc]
    assert req.hash == '6ba8b9ec3277be27270f3af4d9939488'
    hc.port = 6443
    assert req.hash == 'bb07080eeb500a34a458276021c9fa3e'
    req.repsonse = 'foo'
    assert req.hash == 'bb07080eeb500a34a458276021c9fa3e'

    req.traffic_type = None
    with pytest.raises(ValidationError):
        req.hash
    with pytest.raises(ValidationError):
        req._write(relation, app)
    req.traffic_type = 'https'

    req._write(relation, app)
    req2 = Request._read(relation, app, 'name')
    assert req2.hash == req.hash
    assert [r.hash for r in Request._read_all(relation, app)] == [req.hash]


def test_response():
    app = Mock(name='app')
    relation = Mock(name='relation', data={app: {}})
    with pytest.raises(ValidationError):
        Response()
    with pytest.raises(TypeError):
        Response('foo')
    with pytest.raises(ValidationError):
        Response(name='name',
                 success=True,
                 address=None,
                 request_hash=None)
    with pytest.raises(ValidationError):
        Response(name='name',
                 success=True,
                 address='https://my-lb.aws.com/',
                 response_hash='',
                 foo='bar')
    with pytest.raises(ValidationError):
        Response(name='name',
                 success=False,
                 address='https://my-lb.aws.com/',
                 request_hash='')

    resp = Response(name='name',
                    success=True,
                    address='https://my-lb.aws.com/',
                    request_hash='')
    assert resp.hash == '870e2bedbd21c2f92a45ee79f719e8ff'
    resp.foo = 'bar'
    assert resp.hash == '870e2bedbd21c2f92a45ee79f719e8ff'

    resp.success = False
    with pytest.raises(ValidationError):
        resp.hash
    with pytest.raises(ValidationError):
        resp._write(relation, app)
    resp.message = 'foo'
    assert resp.hash == 'af103a8fd206d8f31d97fa328c84ce99'

    resp._write(relation, app)
    resp2 = Response._read(relation, app, 'name')
    assert resp2.hash == resp.hash
    assert [r.hash for r in Response._read_all(relation, app)] == [resp.hash]


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
