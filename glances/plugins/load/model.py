# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
#
# Glances is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Glances is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Load plugin."""

import os
import psutil

from glances.globals import iteritems
from glances.plugins.core.model import PluginModel as CorePluginModel
from glances.plugins.plugin.model import GlancesPluginModel
from glances.logger import logger

# Fields description
fields_description = {
    'min1': {
        'description': 'Average sum of the number of processes \
waiting in the run-queue plus the number currently executing \
over 1 minute.',
        'unit': 'float',
        'short_description': '1 min',
    },
    'min5': {
        'description': 'Average sum of the number of processes \
waiting in the run-queue plus the number currently executing \
over 5 minutes.',
        'unit': 'float',
        'short_description': '5 mins',
    },
    'min15': {
        'description': 'Average sum of the number of processes \
waiting in the run-queue plus the number currently executing \
over 15 minutes.',
        'unit': 'float',
        'short_description': '15 mins',
    },
    'cpucore': {'description': 'Total number of CPU core.', 'unit': 'number'},
}

# Define the layout (for the Rich interface)
layout = {
    'title': '[blue]Load[/] {cpucore}-core',
    'content_row': ['min1', 'min5', 'min15'],
    'content_column': ['{short_description}', 'key'],
    'precision': 2,
    'width': 16
}

# SNMP OID
# 1 minute Load: .1.3.6.1.4.1.2021.10.1.3.1
# 5 minute Load: .1.3.6.1.4.1.2021.10.1.3.2
# 15 minute Load: .1.3.6.1.4.1.2021.10.1.3.3
snmp_oid = {
    'min1': '1.3.6.1.4.1.2021.10.1.3.1',
    'min5': '1.3.6.1.4.1.2021.10.1.3.2',
    'min15': '1.3.6.1.4.1.2021.10.1.3.3',
}

# Define the history items list
# All items in this list will be historised if the --enable-history tag is set
items_history_list = [
    {'name': 'min1', 'description': '1 minute load'},
    {'name': 'min5', 'description': '5 minutes load'},
    {'name': 'min15', 'description': '15 minutes load'},
]


class PluginModel(GlancesPluginModel):
    """Glances load plugin.

    stats is a dict
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(PluginModel, self).__init__(
            args=args,
            config=config,
            items_history_list=items_history_list,
            fields_description=fields_description,
            layout=layout,
        )

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Call CorePluginModel in order to display the core number
        try:
            self.nb_log_core = CorePluginModel(args=self.args).update()["log"]
        except Exception as e:
            logger.warning('Error: Can not retrieve the CPU core number (set it to 1) ({})'.format(e))
            self.nb_log_core = 1

    def _getloadavg(self):
        """Get load average. On both Linux and Windows thanks to PsUtil"""
        try:
            return psutil.getloadavg()
        except (AttributeError, OSError):
            pass
        try:
            return os.getloadavg()
        except (AttributeError, OSError):
            return None

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update load stats."""
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            # Update stats using the standard system lib

            # Get the load using the os standard lib
            load = self._getloadavg()
            if load is None:
                stats = self.get_init_value()
            else:
                stats = {'min1': load[0], 'min5': load[1], 'min15': load[2], 'cpucore': self.nb_log_core}

        elif self.input_method == 'snmp':
            # Update stats using SNMP
            stats = self.get_stats_snmp(snmp_oid=snmp_oid)

            if stats['min1'] == '':
                stats = self.get_init_value()
                return stats

            # Python 3 return a dict like:
            # {'min1': "b'0.08'", 'min5': "b'0.12'", 'min15': "b'0.15'"}
            for k, v in iteritems(stats):
                stats[k] = float(v)

            stats['cpucore'] = self.nb_log_core

        # Update the stats
        self.stats = stats

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(PluginModel, self).update_views()

        # Add specifics informations
        try:
            # Alert and log
            self.views['min15']['decoration'] = self.get_alert_log(
                self.stats['min15'], maximum=100 * self.stats['cpucore']
            )
            # Alert only
            self.views['min5']['decoration'] = self.get_alert(self.stats['min5'], maximum=100 * self.stats['cpucore'])
        except KeyError:
            # try/except mandatory for Windows compatibility (no load stats)
            pass
