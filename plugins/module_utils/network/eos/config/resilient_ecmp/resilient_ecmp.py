#
# -*- coding: utf-8 -*-
# Copyright 2021 Red Hat
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
The eos_resilient_ecmp class
It is in this file where the current configuration (as dict)
is compared to the provided configuration (as dict) and the command set
necessary to bring the current configuration to it's desired end-state is
created
"""
from ansible_collections.ansible.netcommon.plugins.module_utils.network.common.cfg.base import (
    ConfigBase,
)
from ansible_collections.ansible.netcommon.plugins.module_utils.network.common.utils import (
    to_list,
)
from ansible_collections.arista.eos.plugins.module_utils.network.eos.facts.facts import Facts


class Resilient_ecmp(ConfigBase):
    """
    The eos_resilient_ecmp class
    """

    gather_subset = [
        '!all',
        '!min',
    ]

    gather_network_resources = [
        'resilient_ecmp',
    ]

    def __init__(self, module):
        super(Resilient_ecmp, self).__init__(module)

    def get_resilient_ecmp_facts(self):
        """ Get the 'facts' (the current configuration)

        :rtype: A dictionary
        :returns: The current configuration as a dictionary
        """
        facts, _warnings = Facts(self._module).get_facts(self.gather_subset, self.gather_network_resources)
        resilient_ecmp_facts = facts['ansible_network_resources'].get('resilient_ecmp')
        if not resilient_ecmp_facts:
            return []
        return resilient_ecmp_facts

    def execute_module(self):
        """ Execute the module

        :rtype: A dictionary
        :returns: The result from module execution
        """
        result = {'changed': False}
        warnings = list()
        commands = list()

        existing_resilient_ecmp_facts = self.get_resilient_ecmp_facts()
        commands.extend(self.set_config(existing_resilient_ecmp_facts))
        if commands:
            if not self._module.check_mode:
                self._connection.edit_config(commands)
            result['changed'] = True
        result['commands'] = commands

        changed_resilient_ecmp_facts = self.get_resilient_ecmp_facts()

        result['before'] = existing_resilient_ecmp_facts
        if result['changed']:
            result['after'] = changed_resilient_ecmp_facts

        result['warnings'] = warnings
        return result

    def set_config(self, existing_resilient_ecmp_facts):
        """ Collect the configuration from the args passed to the module,
            collect the current configuration (as a dict from facts)

        :rtype: A list
        :returns: the commands necessary to migrate the current configuration
                  to the desired configuration
        """
        want = self._module.params['config']
        have = existing_resilient_ecmp_facts
        resp = self.set_state(want, have)
        return to_list(resp)

    def set_state(self, want, have):
        """ Select the appropriate function based on the state provided

        :param want: the desired configuration as a dictionary
        :param have: the current configuration as a dictionary
        :rtype: A list
        :returns: the commands necessary to migrate the current configuration
                  to the desired configuration
        """
        state = self._module.params['state']
        if state == 'overridden':
            kwargs = {}
            commands = self._state_overridden(**kwargs)
        elif state == 'deleted':
            commands = self._state_deleted(want, have)
        elif state == 'merged':
            commands = self._state_merged(want, have)
        elif state == 'replaced':
            commands = self._state_replaced(want, have)
        else:
            commands = []
        return commands

    def _state_replaced(self, want, have):
        """ The command generator when state is replaced

        :rtype: A list
        :returns: the commands necessary to migrate the current configuration
                  to the desired configuration
        """
        commands = []
        removeconfigs = []
        addconfigs = []

        for h in have:
            for w in want:
                if h["afi"] == w["afi"]:
                    haveconfigs = self._add_commands(h)
                    wantconfigs = self._add_commands(w)
                    addconfigs.extend(wantconfigs)
                    removeconfigs.extend(list(set(haveconfigs) - set(wantconfigs)))

        for command in removeconfigs:
            commands.append("no " + command)
        for wantcmd in addconfigs:
            commands.append(wantcmd)
        return commands

    @staticmethod
    def _state_overridden(**kwargs):
        """ The command generator when state is overridden

        :rtype: A list
        :returns: the commands necessary to migrate the current configuration
                  to the desired configuration
        """
        commands = []
        return commands

    def _state_merged(self, want, have):
        """ The command generator when state is merged

        :rtype: A list
        :returns: the commands necessary to merge the provided into
                  the current configuration
        """
        commands = self._set_commands(want, have)
        return commands

    def _state_deleted(self, want, have):
        """ The command generator when state is deleted

        :rtype: A list
        :returns: the commands necessary to remove the current configuration
                  of the provided objects
        """
        commands = []
        if not want:
            for h in have:
                return_command = self._add_commands(h)
                for command in return_command:
                    command = "no " + command
                    commands.append(command)
        else:
            for w in want:
                return_command = self._del_commands(w, have)
                for command in return_command:
                    commands.append(command)
        return commands

    def _set_commands(self, want, have):
        commands = []
        for w in want:
            return_command = self._add_commands(w)
            for command in return_command:
                commands.append(command)
        return commands

    @staticmethod
    def _add_commands(want):
        commandset = []
        if not want:
            return commandset
        static_command = "hardware fib ecmp resilience"
        if want["afi"] == "ipv6":
            afi = "ipv6"
        else:
            afi = "ip"
        for each_route in want['routes']:
            command = '{} {} {} capacity {} redundancy {}'.format(
                afi,
                static_command,
                each_route['dest'],
                str(each_route['capacity']),
                str(each_route['redundancy'])
            )
            commandset.append(command)
        return commandset

    def _del_commands(self, want, have):
        commandset = []
        haveconfigs = []
        for h in have:
            return_command = self._add_commands(h)
            for command in return_command:
                command = "no " + command
                haveconfigs.append(command)

        for address_family in want:
            afi = address_family['afi']
            for command in haveconfigs:
                if (afi == "ipv6" and "ipv6" in command) or (afi == "ipv4" and "ip " in command):
                    if "routes" in address_family and address_family["routes"]:
                        for route in address_family["routes"]:
                            if route['dest'] in command:
                                if "capacity" in route and route["capacity"] and "redundancy" in route and \
                                        route['redundancy']:
                                    sub_command = "capacity {} redundancy {}".format(
                                        str(route["capacity"]),
                                        str(route['redundancy'])
                                    )
                                    if sub_command in command:
                                        commandset.append(command)
                                else:
                                    commandset.append(command)
                    else:
                        commandset.append(command)
        return commandset
