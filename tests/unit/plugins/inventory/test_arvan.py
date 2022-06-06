# -*- coding: utf-8 -*-
# Copyright: (c) 2022, Zahir Mohsen Moradi <zm.moradi@protonmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from os import path, listdir, environ
import json
import pytest
from mock import MagicMock, patch

from plugins.inventory.arvan import InventoryModule, GetAPIRequestThread, DOCUMENTATION, ARVAN_API_ENDPOINT

from ansible.errors import AnsibleError
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.inventory.data import InventoryData
from ansible import constants as C
from ansible.plugins.doc_fragments.constructed import ModuleDocFragment


def pytest_generate_tests(metafunc):
    # called once per each test function
    funcargdict = metafunc.cls.params[metafunc.function.__name__]
    argnames = sorted(list(funcargdict.values())[0])
    metafunc.parametrize(
        argnames, [[funcargdict[test_id][name] for name in argnames] for test_id in sorted(funcargdict.keys())],
        ids=list(sorted(funcargdict.keys()))
    )


dirname = path.dirname(path.abspath(__file__))
inventory_paths = [path.abspath("{0}/fixtures/yml/inventory{1}_arvan.yml".format(dirname, n)) for n in range(12)]
api_config_paths = [path.abspath("{0}/fixtures/ini/api_config{1}.ini".format(dirname, n)) for n in range(3)]
json_base_path = path.abspath("%s/fixtures/json/" % dirname)
success_servers_res = {"ir-tbz-dc1": 200, "ir-thr-at1": 200, "ir-thr-c2": 200, "ir-thr-mn1": 200, "nl-ams-su1": 200}
success_dcs_res = 200


class APIResponseGenerator:
    def __init__(self, json_base_path, dcs_res_status, servers_res_status):
        self.servers = dict()
        self.servers_res_status = servers_res_status
        self.dcs_res_status = dcs_res_status
        try:
            for entry in listdir(json_base_path):
                if entry.endswith(".json"):
                    fp = open(path.join(json_base_path, entry))
                    if entry == "dcs.json":
                        self.dcs = json.loads(fp.read())
                    elif entry.startswith("servers_"):
                        self.servers[entry.split("_")[1].split(".")[0]] = json.loads(fp.read())
                    fp.close()
        except Exception as e:
            print("__init__ Exception {0} {1}".format(json_base_path, e))
            self.dcs = list()
            self.servers = dict()

    def side_effect(self, api_key, dc=None, resource="regions", timeout=10, retries=1, retry_max_delay=1.0, endpoint=ARVAN_API_ENDPOINT):
        m = MagicMock(autospec=GetAPIRequestThread)
        m.dc = dc
        if resource == "regions":
            m.response_data = self.dcs
            m.response_status = self.dcs_res_status
        elif resource == "servers":
            if dc in self.servers:
                m.response_data = self.servers[dc]
                if dc in self.servers_res_status:
                    m.response_status = self.servers_res_status[dc]
                else:
                    m.response_status = 0
            else:
                m.response_data = list()
                m.response_status = 0
        return m


def create_InventoryModule():
    inv = InventoryModule()
    inv._redirected_names = "arvancloud.iaas.arvan"
    inv._load_name = "arvan"
    dstring1 = AnsibleLoader(DOCUMENTATION).get_single_data()
    dstring2 = AnsibleLoader(ModuleDocFragment.DOCUMENTATION).get_single_data()
    dstring1['options'].update(dstring2['options'])
    C.config.initialize_plugin_configuration_definitions('inventory', inv._load_name, dstring1['options'])
    return inv


def update_return(a, b):
    a = dict(a)
    a.update(b)
    return a


def build_v6_addresses(addr):
    return dict(publicv6=[dict(addr=addr, version="6", type="fixed", is_public=True)])


class TestPluginInventoryArvan:

    params = {
        "test_no_api_key_raise_AnsibleError": {
            "inventory file has no api_key":
            dict(inv_file=inventory_paths[0], env_vars=dict()),
            "inventory file has no api_key & ini file is empty":
            dict(inv_file=inventory_paths[0], env_vars=dict(ARVAN_API_CONFIG=api_config_paths[2])),
            "inventory file has no api_key & default section in ini file has no key":
            dict(inv_file=inventory_paths[0], env_vars=dict(ARVAN_API_CONFIG=api_config_paths[0])),
            "inventory file has specific api_account & account in ini has no key":
            dict(inv_file=inventory_paths[1], env_vars=dict(ARVAN_API_CONFIG=api_config_paths[0])),
            "inventory file has no api_key & account in ini has no key":
            dict(inv_file=inventory_paths[0], env_vars=dict(ARVAN_API_CONFIG=api_config_paths[0], ARVAN_API_ACCOUNT="account2"))
        },
        "test_api_key_set_methods": {
            "key in inventory file":
            dict(inv_file=inventory_paths[2], env_vars=dict(), api_key="Apikey vvv"),
            "key in ARVAN_API_KEY":
            dict(inv_file=inventory_paths[0], env_vars=dict(ARVAN_API_KEY="Apikey nnn"), api_key="Apikey nnn"),
            "key in default section of ini":
            dict(inv_file=inventory_paths[0], env_vars=dict(ARVAN_API_CONFIG=api_config_paths[1],), api_key="Apikey xxx"),
            "key in specific section of ini (section specified with env)":
            dict(
                inv_file=inventory_paths[0],
                env_vars=dict(ARVAN_API_CONFIG=api_config_paths[1], ARVAN_API_ACCOUNT="account1"),
                api_key="Apikey yyy"
            ),
            "key in specific section of ini (section specified in inventory api_account)":
            dict(inv_file=inventory_paths[1], env_vars=dict(ARVAN_API_CONFIG=api_config_paths[1]), api_key="Apikey zzz"),
            "key in inventory file & in ARVAN_API_KEY env var":
            dict(inv_file=inventory_paths[2], env_vars=dict(ARVAN_API_KEY="Apikey nnn"), api_key="Apikey vvv"),
            "key in inventory file & in default section of ini":
            dict(inv_file=inventory_paths[2], env_vars=dict(ARVAN_API_CONFIG=api_config_paths[1],), api_key="Apikey vvv"),
            "key in inventory file & in specific section of ini":
            dict(inv_file=inventory_paths[3], env_vars=dict(ARVAN_API_CONFIG=api_config_paths[1],), api_key="Apikey ooo"),
            "key in ARVAN_API_KEY & in defualt section of ini":
            dict(
                inv_file=inventory_paths[0],
                env_vars=dict(ARVAN_API_KEY="Apikey qqq", ARVAN_API_CONFIG=api_config_paths[1],),
                api_key="Apikey qqq"
            ),
        },
        "test_other_api_options": {
            "api options default values":
            dict(
                inv_file=inventory_paths[2], env_vars=dict(),
                expected_options=dict(timeout=5, retries=2, retry_max_delay=5, endpoint=ARVAN_API_ENDPOINT)
            ),
            "api options in inventory file":
            dict(
                inv_file=inventory_paths[4], env_vars=dict(),
                expected_options=dict(timeout=9999, retries=9998, retry_max_delay=9997, endpoint="APIENDPOINT1")
            ),
            "api options in env vars":
            dict(
                inv_file=inventory_paths[2],
                env_vars=dict(ARVAN_API_TIMEOUT='8999', ARVAN_API_RETRIES='8998', ARVAN_API_RETRY_MAX_DELAY='8997', ARVAN_API_ENDPOINT="APIENDPOINT2"),
                expected_options=dict(timeout=8999, retries=8998, retry_max_delay=8997, endpoint="APIENDPOINT2")
            ),
            "api options in default section of ini":
            dict(
                inv_file=inventory_paths[2], env_vars=dict(ARVAN_API_CONFIG=api_config_paths[0],),
                expected_options=dict(timeout=7999, retries=7998, retry_max_delay=7997, endpoint="APIENDPOINT3")
            ),
            "api options in specific section of ini":
            dict(
                inv_file=inventory_paths[2], env_vars=dict(ARVAN_API_CONFIG=api_config_paths[0], ARVAN_API_ACCOUNT="account3"),
                expected_options=dict(timeout=6999, retries=6998, retry_max_delay=6997, endpoint="APIENDPOINT4")
            ),
        },
        "test_hosts_groups_options": {
            "get servers - no option":
            dict(
                change_server_keys=dict(), expected_groups={"arvan": ["vm0", "vm1", "vm2"]},
                expected_hosts={
                    "vm0": dict(ansible_host="188.121.111.89"),
                    "vm1": dict(ansible_host="130.185.122.57"),
                    "vm2": dict(ansible_host="130.185.122.205")
                },
                get_dcs_status=200, get_servers_status=dict(success_servers_res),
                inv_file=inventory_paths[2], raise_error=False, raise_error_match=""
            ),
            "error in fetching dcs list":
            dict(
                change_server_keys=dict(), expected_groups={"arvan1": ["vm0x", "vm1x", "vm2x"]},
                expected_hosts={"vm0x": dict(), "vm1x": dict(), "vm2x": dict()}, get_dcs_status=503, get_servers_status=dict(success_servers_res),
                inv_file=inventory_paths[2], raise_error=True, raise_error_match="Could not fetch dcs"
            ),
            "error in fetching servers list & ignore_failed_dcs: false":
            dict(
                change_server_keys=dict(), expected_groups={"arvan2": ["vm0y", "vm1y", "vm2y"]},
                expected_hosts={"vm0y": dict(), "vm1y": dict(), "vm2y": dict()},
                get_dcs_status=200, get_servers_status=update_return(success_servers_res, {'nl-ams-su1': 503}),
                inv_file=inventory_paths[5], raise_error=True, raise_error_match="Fetching servers in.*failed$"
            ),
            "filter_by_dcs: [Herman, nl-ams-su1]":
            dict(
                change_server_keys=dict(), expected_groups={"arvan": ["vm1", "vm2"]},
                expected_hosts={"vm1": dict(), "vm2": dict()}, get_dcs_status=200, get_servers_status=dict(success_servers_res),
                inv_file=inventory_paths[6], raise_error=False, raise_error_match=""
            ),
            "filter_by_tag: tag1":
            dict(
                change_server_keys=dict(vm1={"tags": [{"name": "tag1", "id": "7777"}]}), expected_groups={"arvan": ["vm1"]},
                expected_hosts={"vm1": dict()}, get_dcs_status=200, get_servers_status=dict(success_servers_res),
                inv_file=inventory_paths[7], raise_error=False, raise_error_match=""
            ),
            "hostname: v4_private_ip":
            dict(
                change_server_keys=dict(), expected_groups={"arvan": ["vm0", "vm1", "vm2"]},
                expected_hosts={"vm0": dict(ansible_host="10.2.0.174"), "vm1": dict(ansible_host="10.3.0.166"), "vm2": dict(ansible_host="10.3.0.156")},
                get_dcs_status=200, get_servers_status=dict(success_servers_res),
                inv_file=inventory_paths[8], raise_error=False, raise_error_match=""
            ),
            "hostname: v4_private_or_public_ip":
            dict(
                change_server_keys=dict(), expected_groups={"arvan": ["vm0", "vm1", "vm2"]},
                expected_hosts={"vm0": dict(ansible_host="10.2.0.174"), "vm1": dict(ansible_host="10.3.0.166"), "vm2": dict(ansible_host="10.3.0.156")},
                get_dcs_status=200, get_servers_status=dict(success_servers_res),
                inv_file=inventory_paths[9], raise_error=False, raise_error_match=""
            ),
            "hostname: v4_public_or_private_ip":
            dict(
                change_server_keys=dict(), expected_groups={"arvan": ["vm0", "vm1", "vm2"]},
                expected_hosts={
                    "vm0": dict(ansible_host="188.121.111.89"),
                    "vm1": dict(ansible_host="130.185.122.57"),
                    "vm2": dict(ansible_host="130.185.122.205")
                },
                get_dcs_status=200, get_servers_status=dict(success_servers_res),
                inv_file=inventory_paths[10], raise_error=False, raise_error_match=""
            ),
            "hostname: v6_public_ip":
            dict(
                change_server_keys=dict(vm0={"addresses": build_v6_addresses("2001:4860:4860::8888")}),
                expected_groups={"arvan": ["vm0", "vm1", "vm2"]},
                expected_hosts={
                    "vm0": dict(ansible_host="2001:4860:4860::8888"),
                    "vm1": dict(v4_public_ip="130.185.122.57"),
                    "vm2": dict(v4_private_ip="10.3.0.156")
                },
                get_dcs_status=200, get_servers_status=dict(success_servers_res),
                inv_file=inventory_paths[11], raise_error=False, raise_error_match=""
            ),
        }
    }

    def test_no_api_key_raise_AnsibleError(self, env_vars, inv_file):
        with patch("plugins.inventory.arvan.GetAPIRequestThread", autospec=GetAPIRequestThread) as api_request:
            with patch.dict(environ, env_vars):
                api_gen = APIResponseGenerator(json_base_path=json_base_path, dcs_res_status=success_dcs_res, servers_res_status=success_servers_res)
                api_request.side_effect = api_gen.side_effect
                inv = create_InventoryModule()
                with pytest.raises(AnsibleError, match="Could not find an API key.*$"):
                    inv.parse(InventoryData(), DataLoader(), inv_file)

    def test_api_key_set_methods(self, api_key, env_vars, inv_file):
        with patch("plugins.inventory.arvan.GetAPIRequestThread", autospec=GetAPIRequestThread) as api_request:
            with patch.dict(environ, env_vars):
                api_gen = APIResponseGenerator(json_base_path=json_base_path, dcs_res_status=success_dcs_res, servers_res_status=success_servers_res)
                api_request.side_effect = api_gen.side_effect
                inv = create_InventoryModule()
                inv.parse(InventoryData(), DataLoader(), inv_file)
                assert inv.api_key == api_key

    def test_other_api_options(self, env_vars, expected_options, inv_file):
        with patch("plugins.inventory.arvan.GetAPIRequestThread", autospec=GetAPIRequestThread) as api_request:
            with patch.dict(environ, env_vars):
                api_gen = APIResponseGenerator(json_base_path=json_base_path, dcs_res_status=success_dcs_res, servers_res_status=success_servers_res)
                api_request.side_effect = api_gen.side_effect
                inv = create_InventoryModule()
                inv.parse(InventoryData(), DataLoader(), inv_file)
                for h in inv.inventory.hosts:
                    print(inv.inventory.hosts[h].vars)
                for option in expected_options:
                    assert getattr(inv, option) == expected_options[option]

    def test_hosts_groups_options(self, change_server_keys, expected_groups, expected_hosts, get_dcs_status,
                                  get_servers_status, inv_file, raise_error, raise_error_match):
        with patch("plugins.inventory.arvan.GetAPIRequestThread", autospec=GetAPIRequestThread) as api_request:
            with patch.dict(environ, dict()):
                api_gen = APIResponseGenerator(json_base_path=json_base_path, dcs_res_status=get_dcs_status, servers_res_status=get_servers_status)
                try:
                    for dc in api_gen.servers:
                        for s in api_gen.servers[dc]:
                            if s.get("name") in change_server_keys:
                                for key in change_server_keys[s.get("name")]:
                                    s[key] = change_server_keys[s.get("name")][key]
                except Exception:
                    assert False
                api_request.side_effect = api_gen.side_effect
                inv = create_InventoryModule()
                if raise_error:
                    with pytest.raises(AnsibleError, match=raise_error_match):
                        inv.parse(InventoryData(), DataLoader(), inv_file)
                else:
                    inv.parse(InventoryData(), DataLoader(), inv_file)
                    expected_num_of_hosts = len(expected_hosts)
                    result_num_of_hosts = len(inv.inventory.hosts)
                    same_hosts_in_result_and_expected = True
                    for h in expected_hosts:
                        if h not in inv.inventory.hosts:
                            same_hosts_in_result_and_expected = False
                            break
                        for k in expected_hosts[h]:
                            if k not in inv.inventory.hosts[h].vars or expected_hosts[h][k] != inv.inventory.hosts[h].vars[k]:
                                same_hosts_in_result_and_expected = False
                                break
                    same_groups_in_result_and_expected = True
                    for g in expected_groups:
                        if g not in inv.inventory.groups:
                            same_groups_in_result_and_expected = False
                            break
                        for h in expected_groups[g]:
                            if h not in [host.name for host in inv.inventory.groups[g].hosts]:
                                same_groups_in_result_and_expected = False
                                break
                    assert expected_num_of_hosts == result_num_of_hosts and same_groups_in_result_and_expected and same_hosts_in_result_and_expected
