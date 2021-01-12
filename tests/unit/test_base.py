import pytest
from loadbalancer_interface.base import (
    HealthCheck,
    Request,
    Response,
)
from marshmallow import ValidationError


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


def test_request():
    with pytest.raises(TypeError):
        Request()
    with pytest.raises(TypeError):
        Request('app', 'relation', 'name', 'foo')
    with pytest.raises(ValidationError):
        Request('app', 'relation', 'name',
                traffic_type='https',
                backend_ports=['none'])
    with pytest.raises(ValidationError):
        Request('app', 'relation', 'name',
                traffic_type='https',
                backend_ports=[443],
                foo='bar')

    req = Request('app', 'relation', 'name',
                  traffic_type='https',
                  backend_ports=[443])
    assert req.health_checks == []

    hc = HealthCheck(traffic_type='https', port=443)
    req = Request('app', 'relation', 'name',
                  traffic_type='https',
                  backend_ports=[443],
                  health_checks=[hc])
    assert req.health_checks == [hc]
    assert req.dump() == {
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
    }
    assert req.hash == '227e12b7f5eb3388ac931e89a3510285'


def test_response():
    assert Response
