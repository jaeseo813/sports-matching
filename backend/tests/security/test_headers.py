from httpx import AsyncClient


async def test_security_headers_present(client: AsyncClient) -> None:
    res = await client.get("/api/v1/health")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert res.headers["referrer-policy"] == "no-referrer"
    assert "max-age" in res.headers["strict-transport-security"]
    assert "default-src 'none'" in res.headers["content-security-policy"]


async def test_cors_rejects_unknown_origin(client: AsyncClient) -> None:
    res = await client.get("/api/v1/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in res.headers
