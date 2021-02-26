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
        Request()._update(
            name="foo",
            id="foo",
            protocol=Request.protocols.https,
            port_mapping={"none": "none"},
        )
    with pytest.raises(ValidationError):
        Request()._update(
            name="foo",
            id="foo",
            protocol=Request.protocols.https,
            port_mapping={443: 443},
            foo="bar",
        )

    req = Request()
    req.name = "name"
    req.id = "id"
    req.protocol = req.protocols.https
    req.port_mapping = {443: 443}
    assert req.version == 1
    assert req.health_checks == []
    assert req.dump()

    hc = HealthCheck()._update(protocol=req.protocols.https, port=443)
    req.health_checks.append(hc)
    assert is_set_and_changed("req.hash", req.hash)
    req.sent_hash = req.hash
    assert is_set_and_changed("req.hash", req.hash)
    hc.port = 6443
    assert is_set_and_changed("req.hash", req.hash)
    req.repsonse = "foo"
    assert is_not_changed("req.hash", req.hash)

    req.protocol = None
    with pytest.raises(ValidationError):
        req.dump()
    assert req.hash is None
    req.protocol = req.protocols.https

    req2 = Request.loads(
        req.dumps(),
        '{"address": "foo", "received_hash": "%s"}' % req.sent_hash,
    )
    assert req2.hash == req.hash
    assert not req2.response.error
    assert req2.response.address == "foo"
    assert req2.response.received_hash == req.sent_hash


def test_response():
    request = Mock(name="request")
    request.name = "name"
    with pytest.raises(TypeError):
        Response()
    with pytest.raises(ValidationError):
        Response(request)._update()
    with pytest.raises(ValidationError):
        Response(request)._update(address="https://my-lb.aws.com/", foo="bar")
    with pytest.raises(ValidationError):
        Response(request)._update(error=Response.error_types.unsupported)

    resp = Response(request)._update(address="https://my-lb.aws.com/", received_hash="")
    assert resp.name == "name"
    assert is_set_and_changed("resp.hash", resp.hash)
    resp.foo = "bar"
    assert is_not_changed("resp.hash", resp.hash)

    resp.error = resp.error_types.unsupported
    with pytest.raises(ValidationError):
        resp.dump()
    assert resp.hash is None
    resp.error_message = "foo"
    assert is_set_and_changed("resp.hash", resp.hash)
    resp.error_message = None
    resp.error_fields = {"foo": "unknown"}
    with pytest.raises(ValidationError):
        resp.dump()
    resp.error_fields = {"public": "not supported"}
    assert is_set_and_changed("resp.hash", resp.hash)

    resp2 = Response(request)._update(resp.dump())
    assert resp2.hash == resp.hash


def test_health_check():
    with pytest.raises(TypeError):
        HealthCheck("foo")
    with pytest.raises(TypeError):
        HealthCheck(protocol="foo")
    with pytest.raises(ValidationError):
        HealthCheck().dump()
    with pytest.raises(ValidationError):
        hc = HealthCheck()
        hc.protocol = Request.protocols.https
        hc.port = "none"
        hc.dump()
    with pytest.raises(ValidationError):
        HealthCheck()._update(protocol=Request.protocols.https, port=443, foo="bar")

    hc = HealthCheck()._update(protocol=Request.protocols.https, port=443)
    assert hc.version == 1
    assert hc.protocol == Request.protocols.https
    assert hc.port == 443
    assert hc.path is None
    assert hc.interval == 30
    assert hc.retries == 3

    hc = HealthCheck()._update(
        protocol=Request.protocols.http, port=80, path="/foo", interval=60, retries=5
    )
    assert hc.protocol == Request.protocols.http
    assert hc.port == 80
    assert hc.path == "/foo"
    assert hc.interval == 60
    assert hc.retries == 5
    assert hc.hash == HealthCheckField()._deserialize(hc.dump(), "", "").hash
