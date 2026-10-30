"""Callback URLs come from API callers: internal targets must be refused before any request."""

import pytest

from docparse.infrastructure.http.callback import UnsafeCallbackUrl, check_callback_url


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/hook",  # plain http
        "https://127.0.0.1/hook",  # loopback
        "https://localhost:8080/admin",
        "https://169.254.169.254/latest/meta-data/",  # cloud metadata
        "https://10.0.0.5/hook",  # RFC 1918
        "https://192.168.1.1/hook",
        "https://[::1]/hook",
        "https://[::ffff:127.0.0.1]/hook",  # loopback spelled as IPv6
        "https://user:pw@1.1.1.1/hook",  # credentials in URL
        "ftp://1.1.1.1/hook",
    ],
)
def test_internal_or_malformed_targets_are_refused(url):
    with pytest.raises(UnsafeCallbackUrl):
        check_callback_url(url)


def test_public_https_is_allowed_and_dev_opt_in_allows_local_http():
    check_callback_url("https://1.1.1.1/hook")
    check_callback_url("http://localhost:9000/hook", allow_private=True)
