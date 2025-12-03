#!/usr/bin/env python3
"""Unit tests for client.py"""

import unittest
from parameterized import parameterized
from unittest.mock import PropertyMock, patch

from client import GithubOrgClient


class TestGithubOrgClient(unittest.TestCase):
    """Tests for GithubOrgClient"""

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
            self.assertEqual(
                org_client._public_repos_url,
                payload["repos_url"]
            )

    @patch("client.get_json")
    def test_public_repos(self, mock_get_json):
        """Test GithubOrgClient.public_repos returns expected repo names."""
        payload = [
            {"name": "repo1"},
            {"name": "repo2"},
        ]
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

