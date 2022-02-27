# -*- coding: utf-8 -*-
# Copyright: (c) 2022, Zahir Mohsen Moradi <zm.moradi@protonmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

DOCUMENTATION = r'''
    name: arvan
    plugin_type: inventory
    author:
        - Zahir Mohsen Moradi <zm.moradi@protonmail.com>
    short_description: Arvan inventory source
    extends_documentation_fragment:
        - constructed
    description:
        - Get inventory hosts from Arvan cloud.
        - Uses an YAML configuration file ending with either I(arvan.yml) or I(arvan.yaml) to set parameter values (also see examples).
        - Uses I(api_config), I(~/.arvan.ini), I(./arvan.ini) or C(ARVAN_API_CONFIG) pointing to a Arvan credentials INI file
        - By default all host added to group I(arvan)
    options:
        plugin:
            description: Token that ensures this is a source file for the 'arvan' plugin.
            type: string
            required: True
            choices: [ arvancloud.iaas.arvan ]
        api_config:
            description: Path to the arvan configuration file. If not specified will be taken from regular Arvan configuration.
            type: path
            env:
                - name: ARVAN_API_CONFIG
        api_key:
            description: Arvan API key. If not specified will be taken from regular Arvan configuration.
            type: string
            env:
                - name: ARVAN_API_KEY
        api_timeout:
            description:
            - HTTP timeout to Arvan API.
            - Fallback value is 5 seconds if not specified.
            type: int
            env:
                - name: ARVAN_API_TIMEOUT
        api_retries:
            description:
            - Amount of retries in case of the Arvan API returns an HTTP 503 code or timeout.
            - Fallback value is 2 retries if not specified.
            type: int
            env:
                - name: ARVAN_API_RETRIES
        api_retry_max_delay:
            description:
            - Retry backoff delay in seconds is exponential up to this max. value, in seconds.
            - Fallback value is 5 seconds.
            type: int
            env:
                - name: ARVAN_API_RETRY_MAX_DELAY
        api_account:
            description:
            - Name of the ini section in the C(arvan.ini) file.
            type: str
            default: default
            env:
                - name: ARVAN_API_ACCOUNT
        api_endpoint:
            description:
            - URL to API endpint (without trailing slash).
            - Fallback value is U(https://napi.arvancloud.com/ecc/v1) if not specified.
            type: str
            env:
                - name: ARVAN_API_ENDPOINT
        hostname:
            description:
            - Determine how ansible_host will be set
            - Choices are
            -    'v4_public_ip'
            -    'v4_private_ip'
            -    'v4_public_or_private_ip'
            -    'v4_private_or_public_ip'
            -    'v6_public_ip'
            -    'name'
            - If set to "name", ansible_host will not be set
            type: string
            default: v4_public_ip
            choices:
                - v4_public_ip
                - v4_private_ip
                - v4_public_or_private_ip
                - v4_private_or_public_ip
                - v6_public_ip
                - name
        filter_by_tag:
            description: Only return servers filtered by this tag
            type: string
        filter_by_dcs:
            description: Only retrun servers filtered by dc code or dc name
            type: list
        ignore_soon_dcs:
            description: Ignore soon dcs
            type: bool
            default: True
        ignore_failed_dcs:
            description: Ignore dcs which api request for list of their servers failed
            type: bool
            default: True
'''

EXAMPLES = r'''
# inventory_arvan.yml file in YAML format
# Example command line: ansible-inventory --list -i inventory_arvan.yml

# Add hosts to group based on Jinja2 conditionals
plugin: arvancloud.iaas.arvan
groups:
  amsterdam_or_tehran : 'city|lower == "amsterdam" or city|lower == "tehran"'

# Create vars from Jinja2 expressions
plugin: arvancloud.iaas.arvan
compose:
  ansible_ssh_private_key_file: '["~/.ssh/",key_name]|join("")'
  ansible_user: default_username

# Add hosts to group based on the values of a variable
# group arvan_{dc_name}_{city}_{country} with parent group arvan
plugin: arvancloud.iaas.arvan
keyed_groups:
  - prefix: arvan
    key: '[dc_name|lower, city|lower, country|lower]|join("_")'
    parent_group: arvan

# Filter servers by tag
plugin: arvancloud.iaas.arvan
filter_by_tag: june

# filter servers by dc_name or dc_full_code
plugin: arvancloud.iaas.arvan
filter_by_dcs:
  - Herman
  - ir-thr-at1


'''

import json
import time
import threading
import random
import os

from ansible.errors import AnsibleError
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable
try:
    # python3
    from configparser import ConfigParser
except ImportError:
    # python2
    from ConfigParser import ConfigParser
from ansible.module_utils.urls import open_url
from ansible.module_utils._text import to_native

ARVAN_API_ENDPOINT = "https://napi.arvancloud.com/ecc/v1"
ARVAN_USER_AGENT = 'Ansible Arvan'


class GetAPIRequestThread(threading.Thread):
    '''
    API GET Request Thread
    '''
    def __init__(self, api_key, dc=None, resource="regions", timeout=10, retries=1, retry_max_delay=1.0, endpoint=ARVAN_API_ENDPOINT):
        super().__init__()
        self.api_key = api_key
        self.timeout = timeout
        self.retries = retries
        self.retry_max_delay = retry_max_delay
        self.response_data = None
        self.response_status = 0
        self.name = "%s-%s" % (dc, resource)
        self.dc = dc
        if resource == "regions":
            self.url = '%s/regions' % (endpoint)
        else:
            self.url = '%s/regions/%s/%s' % (endpoint, dc, resource)

    def run(self):
        randomness = random.randint(0, 1000) / 1000.0
        for try_counter in range(self.retries):
            try:
                response = open_url(
                    self.url,
                    method="GET",
                    headers={'Authorization': self.api_key, 'Content-type': 'application/json'},
                    http_agent=ARVAN_USER_AGENT,
                    timeout=self.timeout
                )
                self.response_status = response.status
                if response.status == 200:
                    resource_list = json.loads(response.read())
                    self.response_data = resource_list.get("data")
                    break
            except ValueError:
                print("Empty or Incorrect JSON payload in API Response")
            except KeyError:
                print("No data in Response")
            except Exception as e:
                print("Error while fetching %s: %s" % (self.url, to_native(e)))

            # If request failed with timeout or empty response or 503 status code
            # and this is not last try , Use exponential backoff plus a little bit of randomness
            if (self.response_status == 503 or self.response_data == 0) and try_counter < self.max_tries - 1:
                delay = 2 ** try_counter + randomness
                if delay > self.retry_max_delay:
                    delay = self.retry_max_delay + randomness
                time.sleep(delay)
            else:
                break


def get_nested_dicts(parent_dict, keys):
    '''
    Retrun value of a key in nested dicts
    '''
    for key in keys:
        if parent_dict:
            parent_dict = parent_dict.get(key, None)
        else:
            break
    return parent_dict


def get_addresses(parent_obj, keys):
    '''
    Convert addresses key in GET servers response to list of dicts
    '''
    try:
        return [addr_spec for net in get_nested_dicts(parent_obj, keys).values() for addr_spec in net]
    except Exception:
        return list()


def parse_object(object, schema):
    spec = dict()
    for field_name, field_spec in schema.items():
        getter = field_spec.get("getter", get_nested_dicts)
        keys = field_spec.get("keys", None)
        convert_to = field_spec.get("convert_to", None)
        default_value = field_spec.get("default", None)
        v = getter(object, keys)
        if convert_to == "int":
            try:
                v = int(v)
            except ValueError:
                v = default_value()
        elif v is None and default_value:
            v = default_value()
        spec[field_name] = v
    return spec


def apply_filter(objects, **kwargs):
    '''
    Filter list of objects based on key/value pairs in kwargs
    '''
    for k, v in kwargs.items():
        objects = [o for o in objects if o.get(k, None) == v]
    return objects


def load_conf(path, ini_group):
    '''
    Parse ini configuration
    '''
    if path:
        conf = ConfigParser()
        conf.read(path)

        if not conf._sections.get(ini_group):
            return dict()

        return dict(conf.items(ini_group))
    else:
        paths = (
            os.path.join(os.path.expanduser('~'), '.arvan.ini'),
            os.path.join(os.getcwd(), 'arvan.ini'),
        )
        if 'ARVAN_API_CONFIG' in os.environ:
            paths += (os.path.expanduser(os.environ['ARVAN_API_CONFIG']),)

        conf = ConfigParser()
        conf.read(paths)

        if not conf._sections.get(ini_group):
            return dict()

        return dict(conf.items(ini_group))


DC_SCHEMA = {
    "dc_flag": dict(keys=("flag",)),
    "country": dict(keys=("country",)),
    "city_code": dict(keys=("city_code",)),
    "city": dict(keys=("city",)),
    "dc_code": dict(keys=("dc_code",)),
    "dc_name": dict(keys=("dc",)),
    "dc_full_code": dict(keys=("code",)),
    "region": dict(keys=("region",)),
    "dc_soon": dict(keys=("soon",)),
    "dc_volume_backed": dict(keys=("volume_backed",)),
    "dc_new": dict(keys=("new",)),
    "dc_beta": dict(keys=("beta",)),
    "dc_visible": dict(keys=("visible",)),
    "dc_default": dict(keys=("default",), default=bool),
}

SERVER_SCHEMA = {
    "id": dict(keys=("id",)),
    "name": dict(keys=("name",)),
    "flavor_name": dict(keys=("flavor", "name")),
    "ram": dict(keys=("flavor", "ram")),
    "swap": dict(keys=("flavor", "swap"), convert_to="int", default=int),
    "vcpus": dict(keys=("flavor", "vcpus")),
    "disk": dict(keys=("flavor", "disk")),
    "status": dict(keys=("status",)),
    "image_name": dict(keys=("image", "name")),
    "os": dict(keys=("image", "os")),
    "os_type": dict(keys=("image", "metadata", "os_type")),
    "default_username": dict(keys=("image", "username")),
    "key_name": dict(keys=("key_name",)),
    "task_state": dict(keys=("task_state",)),
    "created": dict(keys=("created",)),
    "tags": dict(keys=("tags",), default=list),
    "addresses": dict(getter=get_addresses, keys=("addresses",), default=list),
}


class InventoryModule(BaseInventoryPlugin, Constructable):

    NAME = 'arvancloud.iaas.arvan'

    def verify_file(self, path):
        valid = False
        if super(InventoryModule, self).verify_file(path):
            # inventory file name must be ended with arvan.yaml or arvan.yml
            if path.endswith(('arvan.yaml', 'arvan.yml')):
                valid = True
        return valid

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path)
        # read inventory file options
        self._read_config_data(path=path)

        try:
            conf = load_conf(self.get_option('api_config'), self.get_option('api_account'))
        except KeyError:
            pass

        try:
            # API Key must be found in inventory file or arvan configuration files
            self.api_key = self.get_option('api_key') or conf['key']
        except KeyError:
            raise AnsibleError('Could not find an API key. Check inventory file and arvan configuration files.')

        try:
            self.retry_max_delay = self.get_option('api_retry_max_delay') or int(conf.get('retry_max_delay', 5))
            self.retries = self.get_option('api_retries') or int(conf.get('retries', 2))
            self.timeout = self.get_option('api_timeout') or int(conf.get('timeout', 5))
            self.endpoint = self.get_option('api_endpoint') or conf.get('endpoint', ARVAN_API_ENDPOINT)
        except ValueError:
            raise AnsibleError('Error parsing API request parameters')

        filter_by_dcs = self.get_option('filter_by_dcs')

        if filter_by_dcs:
            try:
                filter_by_dcs = [dc.lower() for dc in filter_by_dcs]
            except AttributeError:
                raise AnsibleError("Error parsing filter_by_dcs")

        other_arguments = {"api_key": self.api_key, "retry_max_delay": self.retry_max_delay,
                           "retries": self.retries, "timeout": self.timeout, "endpoint": self.endpoint}
        # fetch all DCs by API
        dcs_thread = GetAPIRequestThread(resource='regions', **other_arguments)
        dcs_thread.start()
        dcs_thread.join()

        if dcs_thread.response_status == 200:
            dcs = dict()
            for dc_entry in dcs_thread.response_data:
                dc = parse_object(dc_entry, DC_SCHEMA)
                try:
                    dc_name = dc.get("dc_name").lower()
                    dc_full_code = dc.get("dc_full_code")
                    # Ignore dcs with soon flag
                    if dc['dc_soon'] and self.get_option("ignore_soon_dcs"):
                        continue
                    # Ignore dcs not in filter_by_dcs
                    if filter_by_dcs and dc_name not in filter_by_dcs and dc_full_code not in filter_by_dcs:
                        continue
                    dcs[dc_full_code] = dc
                except Exception:
                    raise AnsibleError("Error parsing list Of dcs")
        else:
            raise AnsibleError("Could not fetch dcs")

        del dcs_thread

        # Fetch servers from each DC by API
        servers_threads = [GetAPIRequestThread(dc=dc, resource='servers', **other_arguments) for dc in dcs]
        for thread in servers_threads:
            thread.start()
        for thread in servers_threads:
            thread.join()

        # Add a top group 'arvan'
        self.inventory.add_group(group='arvan')

        # Filter by tag is not supported by the api and will be checked against every server
        filter_by_tag = self.get_option('filter_by_tag')
        # Use constructed if applicable
        strict = self.get_option('strict')

        for thread in servers_threads:
            if thread.response_status != 200:
                if not self.get_option("ignore_failed_dcs"):
                    raise AnsibleError("Fetching servers in %s failed" % thread.dc)
                else:
                    print("Fetching servers in %s failed" % thread.dc)
            else:
                for server_entry in thread.response_data:
                    server = parse_object(server_entry, SERVER_SCHEMA)
                    try:
                        tags = [tag.get("name") for tag in server.get("tags")]
                        if filter_by_tag and filter_by_tag not in tags:
                            continue
                        addresses_spec = server.get("addresses")
                    except KeyError:
                        # Ignore servers without tags or addresses key
                        continue
                    server["tags"] = tags
                    hostname_preference = self.get_option('hostname')
                    # Find first available public & private ip addresses & set appropiate keys
                    try:
                        # first available fixed version 4 public ip address
                        addr = apply_filter(addresses_spec, is_public=True, version="4", type="fixed")[0].get("addr")
                        server["v4_public_ip"] = addr
                    except Exception:
                        if hostname_preference == "v4_public_ip":
                            hostname_preference = "name"
                    try:
                        # first available version 4 private ip address
                        addr = apply_filter(addresses_spec, is_public=False, version="4", type="fixed")[0].get("addr")
                        server["v4_private_ip"] = addr
                    except Exception:
                        if hostname_preference == "v4_private_ip":
                            hostname_preference = "name"
                    try:
                        # first available version 6 public ip address
                        addr = apply_filter(addresses_spec, is_public=True, version="6", type="fixed")[0].get("addr")
                        server["v6_public_ip"] = addr
                    except Exception:
                        if hostname_preference == "v6_public_ip":
                            hostname_preference = "name"

                    if hostname_preference in ("v4_private_or_public_ip", "v4_public_or_private_ip") and\
                            not server.get("v4_public_ip") and not server.get("v4_private_ip"):
                        hostname_preference = "name"

                    del server["addresses"]

                    # merge server and dc keys
                    server.update(dcs[thread.dc])

                    # If there is a server with same name in inventory, append id to its name
                    while server["name"] in self.inventory.hosts:
                        server["name"] = server["name"] + "_" + server["id"]

                    # create host and add to arvan group
                    self.inventory.add_host(host=server['name'], group='arvan')

                    # set other attributes
                    for attribute, value in server.items():
                        self.inventory.set_variable(server['name'], attribute, value)

                    if hostname_preference != 'name':
                        if hostname_preference == "v4_private_or_public_ip":
                            addr = server.get("v4_private_ip") or server.get("v4_public_ip")
                        elif hostname_preference == "v4_public_or_private_ip":
                            addr = server.get("v4_public_ip") or server.get("v4_private_ip")
                        else:
                            addr = server.get(hostname_preference)
                        self.inventory.set_variable(server['name'], 'ansible_host', addr)

                    # Composed variables
                    self._set_composite_vars(self.get_option('compose'), server, server['name'], strict=strict)

                    # Complex groups based on jinja2 conditionals, hosts that meet the conditional are added to group
                    self._add_host_to_composed_groups(self.get_option('groups'), server, server['name'], strict=strict)

                    # Create groups based on variable values and add the corresponding hosts to it
                    self._add_host_to_keyed_groups(self.get_option('keyed_groups'), server, server['name'], strict=strict)
