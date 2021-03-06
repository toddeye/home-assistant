"""
tests.test_updater
~~~~~~~~~~~~~~~~~~

Tests updater component.
"""
import unittest
from unittest.mock import patch

import requests

import homeassistant.core as ha
from homeassistant.const import __version__ as CURRENT_VERSION
from homeassistant.components import updater
import homeassistant.util.dt as dt_util
from tests.common import fire_time_changed

NEW_VERSION = '10000.0'


class TestUpdater(unittest.TestCase):
    """ Test the demo lock. """

    def setUp(self):  # pylint: disable=invalid-name
        self.hass = ha.HomeAssistant()

    def tearDown(self):  # pylint: disable=invalid-name
        """ Stop down stuff we started. """
        self.hass.stop()

    @patch('homeassistant.components.updater.get_newest_version')
    def test_new_version_shows_entity_on_start(self, mock_get_newest_version):
        mock_get_newest_version.return_value = NEW_VERSION

        self.assertTrue(updater.setup(self.hass, {
            'updater': None
        }))

        self.assertTrue(self.hass.states.is_state(updater.ENTITY_ID,
                                                  NEW_VERSION))

    @patch('homeassistant.components.updater.get_newest_version')
    def test_no_entity_on_same_version(self, mock_get_newest_version):
        mock_get_newest_version.return_value = CURRENT_VERSION

        self.assertTrue(updater.setup(self.hass, {
            'updater': None
        }))

        self.assertIsNone(self.hass.states.get(updater.ENTITY_ID))

        mock_get_newest_version.return_value = NEW_VERSION

        fire_time_changed(self.hass,
                          dt_util.utcnow().replace(hour=0, minute=0, second=0))

        self.hass.pool.block_till_done()

        self.assertTrue(self.hass.states.is_state(updater.ENTITY_ID,
                                                  NEW_VERSION))

    @patch('homeassistant.components.updater.requests.get')
    def test_errors_while_fetching_new_version(self, mock_get):
        mock_get.side_effect = requests.RequestException

        self.assertIsNone(updater.get_newest_version())

        mock_get.side_effect = ValueError

        self.assertIsNone(updater.get_newest_version())

        mock_get.side_effect = KeyError

        self.assertIsNone(updater.get_newest_version())
