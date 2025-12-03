#!/usr/bin/env python3
"""Unit and integration tests for client.py"""

import unittest
from parameterized import parameterized, parameterized_class
from unittest.mock import Mock, PropertyMock, patch

from client import GithubOrgClient
from fixtures import TEST_PAYLOAD


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


ORG_PAYLOAD = TEST_PAYLOAD[0][0]
REPOS_PAYLOAD = TEST_PAYLOAD[0][1]
EXPECTED_REPOS = TEST_PAYLOAD[0][2]
APACHE2_REPOS = TEST_PAYLOAD[0][3]

ORG_NAME = (
    ORG_PAYLOAD.get("login")
    or ORG_PAYLOAD.get("name")
    or ORG_PAYLOAD.get("org")
    or "google"
)


@parameterized_class([
    {
        "org_payload": ORG_PAYLOAD,
        "repos_payload": REPOS_PAYLOAD,
        "expected_repos": EXPECTED_REPOS,
        "apache2_repos": APACHE2_REPOS,
        "org_name": ORG_NAME,
    }
])
class TestIntegrationGithubOrgClient(unittest.TestCase):
    """Integration tests for GithubOrgClient"""

    @classmethod
    def setUpClass(cls):
        """Set up integration test mocks."""
        cls.get_patcher = patch("requests.get")
        cls.mock_get = cls.get_patcher.start()

        cls.org_url = "https://api.github.com/orgs/{}".format(cls.org_name)

        def side_effect(url):
            mock_resp = Mock()
            if url == cls.org_url:
                mock_resp.json.return_value = cls.org_payload
                return mock_resp
            if url == cls.org_payload.get("repos_url"):
                mock_resp.json.return_value = cls.repos_payload
                return mock_resp
            mock_resp.json.return_value = {}
            return mock_resp

        cls.mock_get.side_effect = side_effect

    @classmethod
    def tearDownClass(cls):
        """Stop patcher."""
        cls.get_patcher.stop()

    def test_public_repos(self):
        """Test public_repos returns expected repositories."""
        org_client = GithubOrgClient(self.org_name)
        self.assertEqual(org_client.public_repos(), self.expected_repos)

        self.mock_get.assert_any_call(self.org_url)
        self.mock_get.assert_any_call(self.org_payload.get("repos_url"))

    def test_public_repos_with_license(self):
        """Test public_repos filters by license."""
        org_client = GithubOrgClient(self.org_name)
        self.assertEqual(
            org_client.public_repos(license="apache-2.0"),
            self.apache2_repos
        )

