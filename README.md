# Juniper JunOS Shell

This Shell supports all Juniper networking devices that run JunOS operating system.

A CloudShell Shell implements integration of a device model, application or other technology with CloudShell. A Shell consists of a data-model that defines how the device and its properties are modeled in CloudShell along with an automation that enables interaction with the device via CloudShell.

This networking shell provides connectivity and management capabilities such as power management, save and restore configruations, structure autoload functionality and upgrade firmware, etc.

## vMX deployment

This is a modified version of the first generation JunOS shell that can be used with vMX virtual router on vSphere.

It handles both deployment and use of the virtual router.

The Juniper JunOS Router model is selected as the deployment target of a vSphere app for the vMX controller (VCP). This is dragged into the blueprint canvas and connected with ordinary connectors. During Setup, the resource driver automatically deploys and connects additional vSphere apps for the vMX cards (VFP) and moves the connectors to individual VFP VMs. A connector can also be added after Setup, going directly to an interface under some VFP.

VCP and VFP templates on vSphere and corresponding apps must be provided.

Point-to-point and VLAN service connections are fully supported. 

vMX is added to a blueprint by dragging a single app and drawing connectors to it. 

The function connect_child_resources in the deployed app resource driver (Generic Juniper JunOS Driver Version3) will be called by Setup. It automatically adds vMX VFP card apps to the reservation, deploys them, and rearranges the connectors so that blueprint devices with connectors to the vMX will instead be connected to deployed cards' port subresources, which are associated with VFP VM vNIC numbers through the Requested vNIC Name attribute.

The JunOS driver is capable of autoloading the vMX as if it were a standard JunOS router -- except that the port subresources under the vMX are not usable for connectors. Connectors going to the vMX app will be moved to specific VFP port subresources, and future connectors should also be drawn to specific VFP port subresources. These connections are implemented using the standard vSphere cloud provider (VLAN service, dvPortgroup, dvSwitch).

### Additions
- Router and Firewall families changed to type ResourceType="Application" so model "Juniper JunOS Router" can be used for vMX and "Juniper JunOS Firewall" for vSRX
- Added "Juniper JunOS Router" attributes that will be used during vMX deployment
  - Number of VFP Cards -- number of card apps to create
  - VFP Card App Name Prefix -- the prefix of the app that will be added for each card. Currently the card VM templates must be preconfigured with the slot id. For each slot id, create the file /var/jnx/card/local/slot and set the contents to be a single number, starting with 0 for the first card, and take a snapshot. For each snapshot, create a distinct app with a common prefix (e.g. VFPXYZ-card0, VFPXYZ-card1, ...), and set "VFP Card App Name Prefix" to the prefix (e.g. "VFPXYZ").
  - Management IP -- requested static management IP or "dhcp"
  - Extra Config Commands -- semicolon-separated commands to be executed in the top level of JunOS configuration mode
  - Note: You must also set other resource attributes on the deployed app in order for the JunOS autoload to run correctly at the end of the deployment:
    - Username
    - Password (will be set for both root and the Username user)
    - Enable Password (just in case, enter the same here as for Password)
    - SNMP Version - "v2c" works
    - SNMP Read Community - "public"
- Family "VNF Card", model "vMX VFP Card"
  - No attributes
  - Child model vMX Port
- Family "Port", model "vMX Port" with attributes that are all set automatically during deployment:
  - Requested vNIC Name (e.g. "4" representing "Network adapter 4" in vSphere) (used by cloud provider)
  - vMX Port Address (e.g. ge-0/0/5) (for information only)
  - MAC Address (lowercase, colons, no leading zeroes) (for information only)
- Function connect_child_resources for deploying the multi-VM vMX added to driver Generic Juniper JunOS Driver Version3


### Installation

Important: In Resource Manager, Resource Families, Deployment Options family, every vCenter option you will use, change Wait for IP to be a user input, or change the default to false. On all vMX-related apps, Wait for IP must be false. 

Create an app named vMX to deploy the vMX controller (VCP). Set the target resource model to be Juniper JunOS Router. Fill the vMX-specific attributes and standard JunOS attributes as described above. This app will be dragged by users to the canvas. Be sure to set Wait for IP to false.
![](screenshots/vmx_inputs.png)

Create apps for the vMX cards (VFP). These will be automatically added to the canvas by the JunOS resource driver during Setup. For each slot id, create a different image. The most efficient way is to use snapshots and linked clones. On the VFP image, power it on and log in as root (password "root" or blank). For each potential slot id (0, 1, 2, ...), create the file /var/jnx/card/local/slot and set the contents to be a single number, power off the VM, and take a snapshot. For each such snapshot, create a distinct CloudShell app using a common prefix (e.g. VFPXYZ-card0, VFPXYZ-card1, ...), and set "VFP Card App Name Prefix" on the user-facing vMX app to the prefix (e.g. "VFPXYZ").

![](screenshots/vmx_slot_id_snapshots.png)

Defining a VFP app pointing to a specific card id snapshot. Be sure to set Wait for IP to false.
![](screenshots/vmx14.png)

In the vSphere client, for each potential ESXi host where the controller VM could get deployed, go to Configuration tab, Software section, Security Profile, Firewall, Properties... and enable "VM serial port connected over network" (not "VM serial port connected to vSPC"). If needed, you can click the Firewall button while standing on "VM serial port connected over network" and enable the access only for the IP of the execution server.
![](screenshots/esxi_serial.png)


### Usage
A blueprint containing a vMX app and connectors:
![](screenshots/vmx01.png)

The vMX is deployed in multiple stages triggered by the default Setup. Most of the work is done in connect_child_resources of the Juniper JunOS Router resource driver, which is attached to the vMX deployed resource.

VFP card apps added to the reservation automatically after the controller has deployed: 
![](screenshots/vmx03.png)


Internal network automatically created and connected to VCP and VFPs during deployment:
![](screenshots/vmx04.png)
![](screenshots/vmx05.png)

Connectors going to the vMX app moved automatically to vFP VMs: 
![](screenshots/jvmx6.png)

#### Connectors

Connectors can be point-to-point from the vMX to another device (including another vMX) or from the vMX to a VLAN service.

##### Requested Source vNIC Name or Requested Target vNIC Name

Be sure to set the attribute for the correct end of the connector (Requested Source vNIC Name or Requested Target vNIC Name), especially when connecting two vMX to each other. 

Connectors without the attribute set will be automatically assigned to interfaces starting from ge-0/0/0.

The attribute can be set explicitly to a value like ge-1-0-5, where / from the vMX interface name is changed to - in the connector attribute. The first number is the card number starting from 0, the middle number is always 0, and the last number is the interface number starting from 0

The attribute can also have one of the values "ge", "et", or "xe". This will automatically assign an interface of that speed. The speeds can be set per card in the VCP template ahead of time (before the cards are actually connected), or using semicolon-separated commands in the Extra Config Commands attribute. Example command: "set chassis fpc 0 pic 0 interface-type xe". The fpc number is the card number starting from 0 and the pic number should always be 0.

Optional connector attributes - blank, ge-1-0-5, or ge
![](screenshots/vmx02.png)


#### Rest of deployment
vMX boot progress tracked in the portal:
![](screenshots/vmx06.png)
![](screenshots/vmx07.png)

Automatically configuring user credentials and management IP:
![](screenshots/vmx08.png)
![](screenshots/vmx09.png)

Polling for expected interfaces based on number of cards:
![](screenshots/vmx10.png)

Autoloaded ports under VFP deployed app resources:
![](screenshots/vmx11.png)

VFP ports connected to VLANs:
![](screenshots/vmx12.png)

After deployment, you can SSH to the vMX using the Address of the deployed vMX resource:
![](screenshots/vmx13.png)

Drawing and connecting a connector to a specific vMX port on a deployed VFP:
![](screenshots/jvmx2.png)
![](screenshots/jvmx3.png)

![](screenshots/jvmx5.png)


### Notes

Only vSphere is supported for vMX. The driver uses pyvmomi for additional vSphere operations beyond the standard cloud provider. No need to install PowerCLI or anything else.

If the first NIC of the vMX controller template isn't already on the management network, connect a manual VLAN service representing the management VLAN to the vMX app with Requested Source/Target vNIC Name on the connector explicitly set to "1". 

If a VFP VM has 10 vNICs, there will be 10 interfaces ge-x/0/0 through ge-x/0/9, but only 7 of these interfaces will be usable. They will have MAC addresses from vNICs. The remaining 3 interfaces will have bogus MAC addresses and it is unknown whether they are usable for anything. Presumably this has something to do with the first vNICs being reserved for management interfaces, but only two management interfaces are mentioned in the docs. 

If you add a vMX to an existing sandbox, you can simply rerun Setup to deploy it. Alternatively you can run Deploy App, then on the deployed resource run the resource function connect_child_resources, then do Connect on all connectors. 
