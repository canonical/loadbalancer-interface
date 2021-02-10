from unittest.mock import Mock

import pytest
from marshmallow import ValidationError

from loadbalancer_interface import schemas

v1 = schemas.versions[1]
HealthCheck = v1.HealthCheck
HealthCheckField = v1.HealthCheckField
Request = v1.Request
Response = v1.Response

values = {}


def is_set_and_changed(key, new):
    old = values.get(key)
    values[key] = new
    return new and new != old


def is_not_changed(key, new):
    return values.get(key) == new


def test_request():
    with pytest.raises(TypeError):
        Request(foo="foo")
    with pytest.raises(ValidationError):
        Request("name")._update(traffic_type="https", backend_ports=["none"])
    with pytest.raises(ValidationError):
        Request("name")._update(traffic_type="https", backend_ports=[443], foo="bar")

    req = Request("name")
    req.traffic_type = "https"
    req.backend_ports = [443]
    assert req.version == 1
    assert req.health_checks == []
    assert req.dump()
    assert req.id is None
    req.relation = Mock(id="0")
    assert req.id == "0:name"

    hc = HealthCheck()._update(traffic_type="https", port=443)
    req.health_checks.append(hc)
    assert is_set_and_changed("req.hash", req.hash)
    req.sent_hash = req.hash
    assert is_set_and_changed("req.hash", req.hash)
    hc.port = 6443
    assert is_set_and_changed("req.hash", req.hash)
    req.repsonse = "foo"
    assert is_not_changed("req.hash", req.hash)

    req.traffic_type = None
    with pytest.raises(ValidationError):
        req.dump()
    assert req.hash is None
    req.traffic_type = "https"

    req2 = Request.loads(
        "name",
        req.dumps(),
        "{"
        ' "success": true,'
        ' "address": "foo",'
        ' "received_hash": "%s"'
        "}" % req.sent_hash,
    )
    assert req2.hash == req.hash
    assert req2.response.success
    assert req2.response.address == "foo"
    assert req2.response.received_hash == req.sent_hash


def test_response():
    request = Mock(name="request")
    request.name = "name"
    with pytest.raises(TypeError):
        Response()
    with pytest.raises(ValidationError):
        Response(request)._update(success=True, address=None, received_hash=None)
    with pytest.raises(ValidationError):
        Response(request)._update(
            success=True, address="https://my-lb.aws.com/", received_hash="", foo="bar"
        )
    with pytest.raises(ValidationError):
        Response(request)._update(
            success=False, address="https://my-lb.aws.com/", received_hash=""
        )

    resp = Response(request)._update(
        success=True, address="https://my-lb.aws.com/", received_hash=""
    )
    assert resp.name == "name"
    assert is_set_and_changed("resp.hash", resp.hash)
    resp.foo = "bar"
    assert is_not_changed("resp.hash", resp.hash)

    resp.success = False
    with pytest.raises(ValidationError):
        resp.dump()
    assert resp.hash is None
    resp.message = "foo"
    assert is_set_and_changed("resp.hash", resp.hash)

    resp2 = Response(request)._update(resp.dump())
    assert resp2.hash == resp.hash


def test_health_check():
    with pytest.raises(TypeError):
        HealthCheck("foo")
    with pytest.raises(TypeError):
        HealthCheck(traffic_type="foo")
    with pytest.raises(ValidationError):
        HealthCheck().dump()
    with pytest.raises(ValidationError):
        hc = HealthCheck()
        hc.traffic_type = "https"
        hc.port = "none"
        hc.dump()
    with pytest.raises(ValidationError):
        HealthCheck()._update(traffic_type="https", port=443, foo="bar")

    hc = HealthCheck()._update(traffic_type="https", port=443)
    assert hc.version == 1
    assert hc.traffic_type == "https"
    assert hc.port == 443
    assert hc.path is None
    assert hc.interval == 30
    assert hc.retries == 3

    hc = HealthCheck()._update(
        traffic_type="http", port=80, path="/foo", interval=60, retries=5
    )
    assert hc.traffic_type == "http"
    assert hc.port == 80
    assert hc.path == "/foo"
    assert hc.interval == 60
    assert hc.retries == 5
    assert hc.hash == HealthCheckField()._deserialize(hc.dump(), "", "").hash
