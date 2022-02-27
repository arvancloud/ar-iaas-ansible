[![Sanity](https://github.com/arvancloudi/ar-iaas-ansible/actions/workflows/sanity.yml/badge.svg)](https://github.com/arvancloud/ar-iaas-ansible/actions/workflows/sanity.yml)
[![Units](https://github.com/arvancloud/ar-iaas-ansible/actions/workflows/units.yml/badge.svg)](https://github.com/arvancloud/ar-iaas-ansible/actions/workflows/units.yml)
[![License](https://img.shields.io/badge/license-GPL%20v3.0-brightgreen.svg)](LICENSE)
# Ansible Inventory Plugin for Arvan Cloud

This collection provides a inventory plugin for [Arvan](https://www.arvancloud.com) Iaas servers .


## Installation


```bash
ansible-galaxy collection install git+https://github.com/arvancloud/ar-iaas-ansible.git
```
## Requirements
- ansible version >= 2.9

## Usage

You need a inventory file which its name ends with 'arvan.yml' or 'arvan.yaml' and this file must at least contains plugin option :

```yaml
# use namespace.collection-name.plugin-name
plugin: arvancloud.iaas.arvan
```


Also you need enable this plugin in ansible.cfg
```ini
[inventory]
enable_plugins=arvancloud.iaas.arvan
```

And you need to add API key from your arvan account to inventory file:
```yaml
plugin: arvancloud.iaas.arvan
api_key: Apikey 01234567-9abc-def0-1234-56789abcdef0
```
Or in ini file:
```ini
[default]
key=Apikey 01234567-9abc-def0-1234-56789abcdef0
```

This plugin will look for ini file in this order:

- File specified by api_account module parameter or environment variable ARVAN_API_CONFIG 
- arvan.ini file located in current working directory
- $HOME/.arvan.ini

A example of ini file:

```ini
[default]
key=Apikey 01234567-9abc-def0-1234-56789abcdef0
timeout=20
max_tries=2
retry_max_delay=1

[account1]
key=Apikey 01234567-9abc-def0-1234-56789abcdef1
timeout=5
```

If ARVAN_API_ACCOUNT environment variable or api_account module parameter is not specified, this plugin will look for the section named "default"

[Plugin options and examples](docs/arvan.rst)

## Host variables
[Here](docs/server_vm0.json) is an example of host variables which this plugin returns

New host variables can be composed by compose option in inventory file


## License

GNU General Public License v3.0

See [COPYING](COPYING) to see the full text.
