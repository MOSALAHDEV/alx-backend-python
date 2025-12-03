#!/usr/bin/env python3
"""Unit and integration tests for client.py"""

import unittest
from parameterized import parameterized, parameterized_class
from unittest.mock import Mock, PropertyMock, patch

from client import GithubOrgClient
from fixtures import TEST_PAYLOAD


def _as_parameterized_class_payload(payload):
    """
    Convert fixtures.TEST_PAYLOAD into a list of dicts suitable for
    parameterized_class.
    """
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload

    out = []
    for item in payload:
        if isinstance(item, dict):
            out.append(item)
        elif isinstance(item, (list, tuple)) and len(item) >= 4:
            out.append(
                {
                    "org_payload": item[0],
                    "repos_payload": item[1],
                    "expected_repos": item[2],
                    "apache2_repos": item[3],
                }
            )

    if out:
        return out

    return [
        {
            "org_payload": {},
            "repos_payload": [],
            "expected_repos": [],
            "apache2_repos": [],
        }
    ]


INTEGRATION_PAYLOADS = _as_parameterized_class_payload(TEST_PAYLOAD)


class TestGithubOrgClient(unittest.TestCase):
    """Unit tests for GithubOrgClient"""

    @parameterized.expand([
        ("google",),
        ("abc",),
    ])
    @patch("client.get_json")
    def test_org(self, org_name, mock_get_json):
        """Test GithubOrgClient.org returns expected value."""
        expected = {"login": org_name}
        mock_get_json.return_value = expected

        org_client = GithubOrgClient(org_name)
        self.assertEqual(org_client.org, expected)

        mock_get_json.assert_called_once_with(
            "https://api.github.com/orgs/{}".format(org_name)
        )

    def test_public_repos_url(self):
        """Test GithubOrgClient._public_repos_url returns repos_url."""
        payload = {"repos_url": "http://example.com/repos"}
        with patch(
            "client.GithubOrgClient.org",
            new_callable=PropertyMock
        ) as mock_org:
            mock_org.return_value = payload
            org_client = GithubOrgClient("google")
            self.assertEqual(org_client._public_repos_url, payload["repos_url"])

    @patch("client.get_json")
    def test_public_repos(self, mock_get_json):
        """Test GithubOrgClient.public_repos returns expected repo names."""
        payload = [{"name": "repo1"}, {"name": "repo2"}]
        mock_get_json.return_value = payload

        with patch(
            "client.GithubOrgClient._public_repos_url",
            new_callable=PropertyMock
        ) as mock_url:
            mock_url.return_value = "http://example.com/repos"

            org_client = GithubOrgClient("google")
            self.assertEqual(org_client.public_repos(), ["repo1", "repo2"])

            mock_url.assert_called_once()
            mock_get_json.assert_called_once_with("http://example.com/repos")

    @parameterized.expand([
        ({"license": {"key": "my_license"}}, "my_license", True),
        ({"license": {"key": "other_license"}}, "my_license", False),
    ])
    def test_has_license(self, repo, license_key, expected):
        """Test GithubOrgClient.has_license returns expected boolean."""
        self.assertEqual(
            GithubOrgClient.has_license(repo, license_key),
            expected
        )


@parameterized_class(INTEGRATION_PAYLOADS)
class TestIntegrationGithubOrgClient(unittest.TestCase):
    """Integration tests for GithubOrgClient"""

    @classmethod
    def setUpClass(cls):
        """Patch requests.get and serve fixture payloads."""
        cls.get_patcher = patch("requests.get")
        cls.mock_get = cls.get_patcher.start()

        cls.org_name = (
            cls.org_payload.get("login")
            or cls.org_payload.get("name")
            or cls.org_payload.get("org")
            or "google"
        )
        cls.org_url = "https://api.github.com/orgs/{}".format(cls.org_name)
        cls.repos_url = cls.org_payload.get("repos_url")

        def _response(payload):
            resp = Mock()
            resp.json.return_value = payload
            return resp

        def side_effect(url, *args, **kwargs):
            if url == cls.org_url:
                return _response(cls.org_payload)
            if cls.repos_url and url == cls.repos_url:
                return _response(cls.repos_payload)
            return _response({})

        cls.mock_get.side_effect = side_effect

    @classmethod
    def tearDownClass(cls):
        """Stop patcher."""
        cls.get_patcher.stop()

    def test_public_repos(self):
        """public_repos returns expected repos from fixtures."""
        org_client = GithubOrgClient(self.org_name)
        self.assertEqual(org_client.public_repos(), self.expected_repos)

    def test_public_repos_with_license(self):
        """public_repos(license='apache-2.0') returns expected apache2 repos."""
        org_client = GithubOrgClient(self.org_name)
        self.assertEqual(
            org_client.public_repos(license="apache-2.0"),
            self.apache2_repos
        )

