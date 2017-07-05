# Juniper JunOS Shell

[![Build status](https://travis-ci.org/QualiSystems/Juniper-JunOS-Shell.svg?branch=dev)](https://travis-ci.org/QualiSystems/Juniper-JunOS-Shell)
[![Coverage Status](https://coveralls.io/repos/github/QualiSystems/Juniper-JunOS-Shell/badge.svg)](https://coveralls.io/github/QualiSystems/Juniper-JunOS-Shell)
[![PyPI version](https://badge.fury.io/py/Juniper-JunOS-Shell.svg)](https://badge.fury.io/py/Juniper-JunOS-Shell)
[![Dependency Status](https://dependencyci.com/github/QualiSystems/Juniper-JunOS-Shell/badge)](https://dependencyci.com/github/QualiSystems/Juniper-JunOS-Shell)
[![Stories in Ready](https://badge.waffle.io/QualiSystems/Juniper-JunOS-Shell.svg?label=ready&title=Ready)](http://waffle.io/QualiSystems/Juniper-JunOS-Shell)

This Shell supports all Juniper networking devices that run JunOS operating system.

A CloudShell Shell implements integration of a device model, application or other technology with CloudShell. A Shell consists of a data-model that defines how the device and its properties are modeled in CloudShell along with an automation that enables interaction with the device via CloudShell.

This networking shell provides connectivity and management capabilities such as power management, save and restore configruations, structure autoload functionality and upgrade firmware, etc.

This shell is forked from Quali's official JunOS first generation shell.

vMX is added to a blueprint by dragging a single app and drawing connectors to it. The added function connect_child_resources in the deployed app resource driver (Generic Juniper JunOS Driver Version3) will be called by Setup and will automatically add vMX VFP card apps to the reservation, deploy them, and rearrange the connectors so that blueprint devices with connectors to the vMX will instead be connected to ports under deployed cards.

The JunOS driver is capable of autoloading the vMX as if it were a standard JunOS router.

- Router and Firewall families changed to type ResourceType="Application" so model "Juniper JunOS Router" can be used for vMX and "Juniper JunOS Firewall" for vSRX
- Added "Juniper JunOS Router" attributes that will be used during vMX deployment
  - Number of VFP Cards -- number of card apps that should be automatically deployed
  - VFP Card App Name Prefix -- the prefix of the app that will be added for each card. Currently the card VM templates must be preconfigured with the slot id. For each slot id, create the file /var/jnx/card/local/slot and set the contents to be a single number, starting with 0 for the first card, and take a snapshot. For each snapshot, create a distinct app with a common prefix (e.g. VFPXYZ-card0, VFPXYZ-card1, ...), and set "VFP Card App Name Prefix" to the prefix (e.g. "VFPXYZ").
  - Management IP -- requested static management IP or "dhcp"
  - Extra Config Commands -- semicolon-separated commands to be executed in the top level of JunOS configuration mode
- Family "VNF Card", model "vMX VFP Card"
  - No attributes
  - Child model vMX Port
- Family "Port", model "vMX Port" with attributes:
  - Requested vNIC Name (e.g. "4" representing "Network adapter 4" in vSphere) (used by cloud provider)
  - vMX Port Address (e.g. ge-0/0/5) (for information only)
  - MAC Address (lowercase, colons, no leading zeroes) (for information only)
- Function connect_child_resources for deploying the multi-VM vMX added to driver Generic Juniper JunOS Driver Version3

