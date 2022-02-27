.. _arvan_module:


arvan -- Arvan inventory source
===============================

.. contents::
   :local:
   :depth: 1


Synopsis
--------

Get inventory hosts from Arvan cloud.

Uses an YAML configuration file ending with either *arvan.yml* or *arvan.yaml* to set parameter values (also see examples).

Uses *api_config*, *~/.arvan.ini*, *./arvan.ini* or ``ARVAN_API_CONFIG`` pointing to a Arvan credentials INI file

By default all host added to group *arvan*






Parameters
----------

  plugin (True, string, None)
    Token that ensures this is a source file for the 'arvan' plugin.


  api_config (optional, path, None)
    Path to the arvan configuration file. If not specified will be taken from regular Arvan configuration.


  api_key (optional, string, None)
    Arvan API key. If not specified will be taken from regular Arvan configuration.


  api_timeout (optional, int, None)
    HTTP timeout to Arvan API.

    Fallback value is 5 seconds if not specified.


  api_retries (optional, int, None)
    Amount of retries in case of the Arvan API returns an HTTP 503 code or timeout.

    Fallback value is 2 retries if not specified.


  api_retry_max_delay (optional, int, None)
    Retry backoff delay in seconds is exponential up to this max. value, in seconds.

    Fallback value is 5 seconds.


  api_account (optional, str, default)
    Name of the ini section in the ``arvan.ini`` file.


  api_endpoint (optional, str, None)
    URL to API endpint (without trailing slash).

    Fallback value is https://napi.arvancloud.com/ecc/v1 if not specified.


  hostname (optional, string, v4_public_ip)
    Determine how ansible_host will be set

    Choices are

    - v4_public_ip

    - v4_private_ip

    - v4_public_or_private_ip

    - v4_private_or_public_ip

    - v6_public_ip

    - name

    If set to "name", ansible_host will not be set


  filter_by_tag (optional, string, None)
    Only return servers filtered by this tag


  filter_by_dcs (optional, list, None)
    Only retrun servers filtered by dc code or dc name


  ignore_soon_dcs (optional, bool, True)
    Ignore soon dcs


  ignore_failed_dcs (optional, bool, True)
    Ignore dcs which api request for list of their servers failed


  strict (optional, bool, False)
    If ``yes`` make invalid entries a fatal error, otherwise skip and continue.

    Since it is possible to use facts in the expressions they might not always be available and we ignore those errors by default.


  compose (optional, dict, {})
    Create vars from jinja2 expressions.


  groups (optional, dict, {})
    Add hosts to group based on Jinja2 conditionals.


  keyed_groups (optional, list, [])
    Add hosts to group based on the values of a variable.


    parent_group (optional, str, None)
      parent group for keyed group


    prefix (optional, str, )
      A keyed group name will start with this prefix


    separator (optional, str, _)
      separator used to build the keyed group name


    key (optional, str, None)
      The key from input dictionary used to generate groups


    default_value (optional, str, None)
      The default value when the host variable's value is an empty string.

      This option is mutually exclusive with ``trailing_separator``.


    trailing_separator (optional, bool, True)
      Set this option to *False* to omit the ``separator`` after the host variable when the value is an empty string.

      This option is mutually exclusive with ``default_value``.



  use_extra_vars (optional, bool, False)
    Merge extra vars into the available variables for composition (highest precedence).


  leading_separator (optional, boolean, True)
    Use in conjunction with keyed_groups.

    By default, a keyed group that does not have a prefix or a separator provided will have a name that starts with an underscore.

    This is because the default prefix is "" and the default separator is "_".

    Set this option to False to omit the leading underscore (or other separator) if no prefix is given.

    If the group name is derived from a mapping the separator is still used to concatenate the items.

    To not use a separator in the group name at all, set the separator for the keyed group to an empty string instead.









Examples
--------

.. code-block:: yaml+jinja

    
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







Status
------





Authors
~~~~~~~

- Zahir Mohsen Moradi <zm.moradi@protonmail.com>

