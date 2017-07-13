from cloudshell.networking.juniper.runners.juniper_connectiviry_runner import \
    JuniperConnectivityRunner as ConnectivityRunner
from cloudshell.networking.juniper.runners.juniper_configuration_runner import \
    JuniperConfigurationRunner as ConfigurationRunner
from cloudshell.networking.juniper.runners.juniper_autoload_runner import JuniperAutoloadRunner as AutoloadRunner
from cloudshell.networking.juniper.runners.juniper_firmware_runner import JuniperFirmwareRunner as FirmwareRunner
from cloudshell.networking.juniper.runners.juniper_run_command_runner import JuniperRunCommandRunner as CommandRunner
from cloudshell.networking.juniper.runners.juniper_state_runner import JuniperStateRunner as StateRunner
from cloudshell.shell.core.context_utils import get_attribute_by_name
from cloudshell.networking.devices.driver_helper import get_logger_with_thread_id, get_api, get_cli
from cloudshell.shell.core.context import ResourceCommandContext
from cloudshell.networking.networking_resource_driver_interface import NetworkingResourceDriverInterface
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.driver_utils import GlobalLock

import json
import re
import telnetlib

from pyVmomi import vim # will always show up as unresolved in PyCharm
from pyVim.connect import SmartConnect, Disconnect
import ssl

from cloudshell.core.logger.qs_logger import get_qs_logger
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.context import InitCommandContext, ResourceCommandContext, AutoLoadDetails, AutoLoadResource, \
    AutoLoadAttribute, AutoLoadCommandContext
from time import sleep, strftime
import pickle
from cloudshell.api.cloudshell_api import CloudShellAPISession, SetConnectorRequest, AttributeNameValue, \
    ApiEditAppRequest, ResourceInfoDto, ResourceAttributesUpdateRequest

def log(s):
    with open(r'c:\programdata\qualisystems\vmx.log', 'a') as f:
        f.write(s + '\n')


class JuniperJunOSResourceDriver(ResourceDriverInterface, NetworkingResourceDriverInterface, GlobalLock):
    SUPPORTED_OS = [r'[Jj]uniper']

    def __init__(self):
        super(JuniperJunOSResourceDriver, self).__init__()
        self._cli = None

    def initialize(self, context):
        """Initialize method

        :type context: cloudshell.shell.core.context.driver_context.InitCommandContext
        """

        session_pool_size = int(get_attribute_by_name(context=context, attribute_name='Sessions Concurrency Limit'))
        self._cli = get_cli(session_pool_size)
        return 'Finished initializing'

    def cleanup(self):
        pass

    def ApplyConnectivityChanges(self, context, request):
        """
        Create vlan and add or remove it to/from network interface

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param str request: request json
        :return:
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)
        connectivity_operations = ConnectivityRunner(cli=self._cli, context=context, api=api, logger=logger)
        logger.info('Start applying connectivity changes, request is: {0}'.format(str(request)))
        result = connectivity_operations.apply_connectivity_changes(request=request)
        logger.info('Finished applying connectivity changes, response is: {0}'.format(str(
            result)))
        logger.info('Apply Connectivity changes completed')

        return result

    @GlobalLock.lock
    def restore(self, context, path, configuration_type, restore_method, vrf_management_name):
        """Restore selected file to the provided destination

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param path: source config file
        :param configuration_type: running or startup configs
        :param restore_method: append or override methods
        :param vrf_management_name: VRF management Name
        """

        if not configuration_type:
            configuration_type = 'running'

        if not restore_method:
            restore_method = 'override'

        if not vrf_management_name:
            vrf_management_name = get_attribute_by_name(context=context, attribute_name='VRF Management Name')

        logger = get_logger_with_thread_id(context)
        api = get_api(context)

        configuration_operations = ConfigurationRunner(logger=logger, api=api, cli=self._cli, context=context)
        logger.info('Restore started')
        configuration_operations.restore(path=path, restore_method=restore_method,
                                         configuration_type=configuration_type,
                                         vrf_management_name=vrf_management_name)
        logger.info('Restore completed')

    def save(self, context, folder_path, configuration_type, vrf_management_name):
        """Save selected file to the provided destination

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param configuration_type: source file, which will be saved
        :param folder_path: destination path where file will be saved
        :param vrf_management_name: VRF management Name
        :return str saved configuration file name:
        """

        if not configuration_type:
            configuration_type = 'running'

        if not vrf_management_name:
            vrf_management_name = get_attribute_by_name(context=context, attribute_name='VRF Management Name')

        logger = get_logger_with_thread_id(context)
        api = get_api(context)

        configuration_operations = ConfigurationRunner(logger=logger, cli=self._cli, context=context, api=api)
        logger.info('Save started')
        response = configuration_operations.save(folder_path=folder_path, configuration_type=configuration_type,
                                                 vrf_management_name=vrf_management_name)
        logger.info('Save completed')
        return response

    def orchestration_save(self, context, mode, custom_params):
        """

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param mode: mode
        :param custom_params: json with custom save parameters
        :return str response: response json
        """

        if not mode:
            mode = 'shallow'

        logger = get_logger_with_thread_id(context)
        api = get_api(context)

        configuration_operations = ConfigurationRunner(logger=logger, api=api, cli=self._cli, context=context)
        logger.info('Orchestration save started')
        response = configuration_operations.orchestration_save(mode=mode, custom_params=custom_params)
        logger.info('Orchestration save completed')
        return response

    def orchestration_restore(self, context, saved_artifact_info, custom_params):
        """

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param saved_artifact_info: OrchestrationSavedArtifactInfo json
        :param custom_params: json with custom restore parameters
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)

        configuration_operations = ConfigurationRunner(logger=logger, api=api, cli=self._cli, context=context)
        logger.info('Orchestration restore started')
        configuration_operations.orchestration_restore(saved_artifact_info=saved_artifact_info,
                                                       custom_params=custom_params)
        logger.info('Orchestration restore completed')

    @GlobalLock.lock
    def get_inventory(self, context):
        """Return device structure with all standard attributes

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :return: response
        :rtype: str
        """

        log('get_inventory called')
        vfpp = context.resource.attributes.get('VFP Card App Name Prefix')
        if vfpp and vfpp != 'DONE':
            log('get_inventory 1')
            rv = AutoLoadDetails()
            rv.resources = []
            rv.attributes = []
            return rv
        log('get_inventory 2')

        logger = get_logger_with_thread_id(context)
        api = get_api(context)
        autoload_operations = AutoloadRunner(cli=self._cli, logger=logger, context=context, api=api,
                                             supported_os=self.SUPPORTED_OS)
        logger.info('Autoload started')
        response = autoload_operations.discover()
        logger.info('Autoload completed')
        return response

    @GlobalLock.lock
    def load_firmware(self, context, path, vrf_management_name):
        """Upload and updates firmware on the resource

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param path: full path to firmware file, i.e. tftp://10.10.10.1/firmware.tar
        :param vrf_management_name: VRF management Name
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)
        if not vrf_management_name:
            vrf_management_name = get_attribute_by_name(context=context, attribute_name='VRF Management Name')

        logger.info('Start Load Firmware')
        firmware_operations = FirmwareRunner(cli=self._cli, logger=logger, context=context, api=api)
        response = firmware_operations.load_firmware(path=path, vrf_management_name=vrf_management_name)
        logger.info('Finish Load Firmware: {}'.format(response))

    def run_custom_command(self, context, custom_command):
        """Send custom command

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :return: result
        :rtype: str
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)
        send_command_operations = CommandRunner(cli=self._cli, logger=logger, context=context, api=api)
        response = send_command_operations.run_custom_command(custom_command=custom_command)
        return response

    def health_check(self, context):
        """Performs device health check

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :return: Success or Error message
        :rtype: str
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)
        state_operations = StateRunner(cli=self._cli, logger=logger, api=api, context=context)
        return state_operations.health_check()

    def run_custom_config_command(self, context, custom_command):
        """Send custom command in configuration mode

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :return: result
        :rtype: str
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)
        send_command_operations = CommandRunner(cli=self._cli, logger=logger, context=context, api=api)
        result_str = send_command_operations.run_custom_config_command(custom_command=custom_command)
        return result_str

    @GlobalLock.lock
    def update_firmware(self, context, remote_host, file_path):
        """Upload and updates firmware on the resource

        :param remote_host: path to firmware file location on ftp or tftp server
        :param file_path: firmware file name
        :return: result
        :rtype: str
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)
        vrf_management_name = get_attribute_by_name(context=context, attribute_name='VRF Management Name')

        logger.info('Start Update Firmware')
        firmware_operations = FirmwareRunner(cli=self._cli, logger=logger, context=context, api=api)
        response = firmware_operations.load_firmware(path=remote_host, vrf_management_name=vrf_management_name)
        logger.info('Finish Update Firmware: {}'.format(response))

    def send_custom_command(self, context, custom_command):
        """Send custom command in configuration mode

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :return: result
        :rtype: str
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)
        send_command_operations = CommandRunner(cli=self._cli, logger=logger, context=context, api=api)
        response = send_command_operations.run_custom_command(custom_command=custom_command)
        return response

    def send_custom_config_command(self, context, custom_command):
        """Send custom command in configuration mode

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :return: result
        :rtype: str
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)
        send_command_operations = CommandRunner(cli=self._cli, logger=logger, context=context, api=api)
        result_str = send_command_operations.run_custom_config_command(custom_command=custom_command)
        return result_str

    def shutdown(self, context):
        """
        Request power off
        :param context:
        :return:
        """
        logger = get_logger_with_thread_id(context)
        api = get_api(context)
        state_operations = StateRunner(cli=self._cli, logger=logger, api=api, context=context)
        return state_operations.shutdown()

    def connect_child_resources(self, context):
        log('Connect child resources called')
        vfp_app_prefix = context.resource.attributes.get('VFP Card App Name Prefix')
        if not vfp_app_prefix:
            return
        ncards = int(context.resource.attributes.get('Number of VFP Cards', '0'))
        if not ncards:
            return
        # logger = get_logger_with_thread_id(context)
        resid = context.reservation.reservation_id
        api = CloudShellAPISession(host=context.connectivity.server_address, token_id=context.connectivity.admin_auth_token, domain="Global")

        resource2pos = {}
        for pos in api.GetReservationResourcesPositions(resid).ResourceDiagramLayouts:
            resource2pos[pos.ResourceName] = (pos.X, pos.Y)

        vfp_name_template = context.resource.name + '_vfp%d'

        x0, y0 = resource2pos[context.resource.name]
        todeploy = []
        log('ncards = %d' % ncards)
        for i in range(ncards):
            vfp_app_name = '%s-card%d' % (vfp_app_prefix, i)
            log('add app %s' % vfp_app_name)
            api.AddAppToReservation(resid, vfp_app_name, positionX=x0, positionY=y0+100+i*100)
            an = vfp_name_template % i
            todeploy.append(an)
            log('rename %s to %s' % (vfp_app_name, an))
            api.EditAppsInReservation(resid, [ApiEditAppRequest(vfp_app_name, an, 'auto generated vfp %d' % i, None, None)])

        for td in todeploy:
            api.WriteMessageToReservationOutput(resid, 'Deploying vMX card %s' % td)
            api.DeployAppToCloudProvider(resid, td, [])
        # # api.DeployAppToCloudProviderBulk(resid, todeploy, tdinputs)

        vmxip = context.resource.attributes.get('Management IP', 'dhcp')
        if vmxip.lower() == 'dhcp':
            ipcommand = "set interfaces fxp0.0 family inet dhcp"
        else:
            if '/' not in vmxip:
                if vmxip.startswith('172.16.'):
                    vmxip += '/16'
                else:
                    vmxip += '/24'
            ipcommand = "set interfaces fxp0.0 family inet address %s" % vmxip
        log('Connect child resources 5')

        telnetpool = {
            'isolation': 'Exclusive',
            'reservationId': resid,
            'poolId': 'vmxconsoleport',
            'ownerId': '',
            'type': 'NextAvailableNumericFromRange',
            'requestedRange': {
                'start': 9300,
                'end': 9330
            }
        }
        log('Connect child resources 5a')

        telnetport = int(api.CheckoutFromPool(json.dumps(telnetpool)).Items[0])
        # telnetport = 9300

        log('Connect child resources 5b')

        cardaddrstr2cardvmname = {}
        cardvms = []
        rd = api.GetReservationDetails(resid).ReservationDescription
        for r in rd.Resources:
            for i in range(ncards):
                if (vfp_name_template % i) in r.Name:
                    cardaddrstr2cardvmname[str(i)] = r.Name
                    cardvms.append(r.Name)
        log('cardaddrstr2cardvmname: %s' % cardaddrstr2cardvmname)

        cpd = api.GetResourceDetails(api.GetResourceDetails(context.resource.name).VmDetails.CloudProviderFullName)
        vcenterip = cpd.Address
        vcenteruser = [x.Value for x in cpd.ResourceAttributes if x.Name == 'User'][0]
        vcenterpassword = api.DecryptPassword([x.Value for x in cpd.ResourceAttributes if x.Name == 'Password'][0]).Value

        sslContext = ssl.create_default_context()
        sslContext.check_hostname = False
        sslContext.verify_mode = ssl.CERT_NONE


        log('connecting to vCenter %s' % vcenterip)
        si = SmartConnect(host=vcenterip, user=vcenteruser, pwd=vcenterpassword, sslContext=sslContext)
        log('connected')
        content = si.RetrieveContent()
        vm = None
        cardvm2mac2nicname = {}

        for c in content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True).view:
            for cardvm in cardvms:
                if c.name == cardvm:
                    for d in c.config.hardware.device:
                        try:
                            mac = d.macAddress
                            mac = mac.lower()
                            mac = mac.replace(':0', ':')
                            if mac.startswith('0'):
                                mac = mac[1:]
                            network_adapter_n = d.deviceInfo.label
                            if cardvm not in cardvm2mac2nicname:
                                cardvm2mac2nicname[cardvm] = {}
                            cardvm2mac2nicname[cardvm][mac] = network_adapter_n
                        except:
                            pass
            if c.name == context.resource.name:
                vm = c
        log('cardvm2mac2nicname = %s' % cardvm2mac2nicname)
        esxi_ip = vm.runtime.host.name
        log('adding serial port to %s' % context.resource.name)
        spec = vim.vm.ConfigSpec()
        serial_spec = vim.vm.device.VirtualDeviceSpec()
        serial_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        serial_spec.device = vim.vm.device.VirtualSerialPort()
        serial_spec.device.yieldOnPoll = True
        serial_spec.device.backing = vim.vm.device.VirtualSerialPort.URIBackingInfo()
        serial_spec.device.backing.serviceURI = 'telnet://:%d' % telnetport
        serial_spec.device.backing.direction = 'server'
        spec.deviceChange.append(serial_spec)
        vm.ReconfigVM_Task(spec=spec)
        log('added serial port')

        Disconnect(si)

        internal_connector_requests = []
        api.AddServiceToReservation(resid, 'VLAN Auto', 'vMX internal network', [])
        api.SetReservationServicePosition(resid, 'vMX internal network', x0-100, y0-150)
        internal_connector_requests.append((context.resource.name, 2, 'vMX internal network', 0, 'br-int', {}))
        for cardvm in cardvms:
            internal_connector_requests.append((cardvm, 2, 'vMX internal network', 0, 'br-int', {}))
        log('internal connector requests: %s' % internal_connector_requests)

        api.SetConnectorsInReservation(resid, [
            SetConnectorRequest(source, target, 'bi', alias)
            for source, _, target, _, alias, _ in internal_connector_requests
        ])
        for source, sourcenic, target, targetnic, _, name2value in internal_connector_requests:
            tc = []
            if sourcenic > 0:
                tc.append(AttributeNameValue('Requested Source vNIC Name', str(sourcenic)))
            if targetnic > 0:
                tc.append(AttributeNameValue('Requested Target vNIC Name', str(targetnic)))
            # if netid > 0:
            #     tc.append(AttributeNameValue('Selected Network', str(targetnic)))

            for name, value in name2value.iteritems():
                tc.append(AttributeNameValue(name, value))
            if tc:
                api.SetConnectorAttributes(resid, source, target, tc)
            api.WriteMessageToReservationOutput(resid, 'Adding connector %s.%s &lt;-&gt; %s.%s' % (source, sourcenic, target, targetnic))

        log('Connect child resources 4')

        endpoints = []
        for x in internal_connector_requests:
            source, _, target, _, _, _ = x
            endpoints.append(source)
            endpoints.append(target)
        log('connecting endpoints %s' % endpoints)

        api.ConnectRoutesInReservation(resid, endpoints, 'bi')
        log('Connect child resources 5')

        # rootpassword = api.DecryptPassword(context.resource.attributes.get('Root Password', '')).Value
        username = context.resource.attributes.get('User', 'user')
        userpassword = api.DecryptPassword(context.resource.attributes.get('Password', '')).Value
        rootpassword = userpassword
        userfullname = context.resource.attributes.get('User Full Name', username)
        log('Connect child resources 6')

        ecc = context.resource.attributes.get('Extra Config Commands', '')
        extra_config_commands = [
                                    (s.strip(), '#')
                                    for s in ecc.split(';')] + [('commit', '#')] if ecc else []
        command_patterns = [
            ("", "login:"),
            ("root", "#"),
            ("cli", ">"),
            ("configure", "#"),
            (ipcommand, "#"),
            ("commit", "#"),
            ("set system root-authentication plain-text-password", "password:"),
            (rootpassword, "password:"),
            (rootpassword, "#"),
            ("commit", "#"),
            ("edit system services ssh", "#"),
            ("set root-login allow", "#"),
            ("commit", "#"),
            ("exit", "#"),
            ("edit system login", "#"),
            ("set user %s class super-user" % username, "#"),
            ("set user %s full-name \"%s\"" % (username, userfullname), "#"),
            ("set user %s authentication plain-text-password" % username, "password:"),
            (userpassword, "password:"),
            (userpassword, "#"),
            ("commit", "#"),
            ("exit", "#"),
        ] + extra_config_commands + [
            ("exit", ">"),
            ("SLEEP", "10"),
            ("show interfaces fxp0.0 terse", ">"),
        ]
        api.WriteMessageToReservationOutput(resid, 'Powering on %s' % context.resource.name)
        api.ExecuteResourceConnectedCommand(resid, context.resource.name, 'PowerOn', 'power')
        api.WriteMessageToReservationOutput(resid, 'Waiting 60 seconds for kernel load')
        log('Connect child resources 7')

        sleep(60)
        api.WriteMessageToReservationOutput(resid, 'Configuring vMX over serial port: telnet://%s:%d. User %s (%s). IP: %s' % (esxi_ip, telnetport, userfullname, username, vmxip))
        log('Connect child resources 8')

        tn = telnetlib.Telnet(esxi_ip, telnetport)
        ts = ''
        for command, pattern in command_patterns:
            if command=='SLEEP':
                sleep(int(pattern))
                continue
            tn.write(command + '\n')
            s = ''
            while True:
                t = tn.read_until(pattern, timeout=5)
                tt = re.sub(r'''[^->'_0-9A-Za-z*:;,.#@/"(){}\[\] \t\r\n]''', '_', t)
                while tt:
                    api.WriteMessageToReservationOutput(resid, tt[0:500])
                    tt = tt[500:]
                s += t
                if pattern in s:
                    ts += s
                    break
            sleep(1)
        ips = re.findall(r'\D(\d+[.]\d+[.]\d+[.]\d+)/', ts)

        vmxeip = ips[-1]
        log('Connect child resources 9')

        for cardvm in cardvms:
            api.WriteMessageToReservationOutput(resid, 'Powering on %s' % cardvm)
            api.ExecuteResourceConnectedCommand(resid, cardvm, 'PowerOn', 'power')
        log('Connect child resources 10')


        tn.write('exit\n')
        tn.read_until('#')

        mac2ifname = {}
        while True:
            mac2ifname0 = {}
            tn.write('ifconfig\n')
            ifconfig = tn.read_until('#')
            tt = re.sub(r'''[^->'_0-9A-Za-z*:;,.#@/"(){}\[\] \t\r\n]''', '_', ifconfig)
            while tt:
                api.WriteMessageToReservationOutput(resid, tt[0:500])
                tt = tt[500:]
            m = re.findall(
                r'^((fe|ge|xe|et)-\d+/\d+/\d+).*?([0-9a-fA-F]+:[0-9a-fA-F]+:[0-9a-fA-F]+:[0-9a-fA-F]+:[0-9a-fA-F]+:[0-9a-fA-F]+)',
                ifconfig, re.DOTALL + re.MULTILINE)
            for j in m:
                ifname, _, mac = j
                mac = mac.lower()
                mac2ifname0[mac] = ifname
            log('mac2ifname0 = %s' % mac2ifname0)
            seencards = set()
            for mac, ifname in mac2ifname0.iteritems():
                seencards.add(int(ifname.split('-')[1].split('/')[0]))

            if len(seencards) >= len(cardvms):
                mac2ifname = mac2ifname0
                break

            api.WriteMessageToReservationOutput(resid, 'Still waiting for %d card(s)' % (len(cardvms)-len(seencards)))
            sleep(5)

        tocreate = []
        attrupdates = []
        intfpool = []
        for cardvm in cardvm2mac2nicname:
            mac2nicname = cardvm2mac2nicname[cardvm]
            for mac, nicname in mac2nicname.iteritems():
                if mac not in mac2ifname:
                    log('NIC %s %s not represented as JunOS interface' % (mac, nicname))
                    continue
                ifname = mac2ifname[mac]
                intfpool.append(ifname.replace('/', '-'))
                tocreate.append(ResourceInfoDto('Port',
                                                'vMX Port',
                                                ifname.replace('/', '-'),
                                                ifname.replace('/', '-'),
                                                '',
                                                cardvm,
                                                ''
                                                ))
                attrupdates.append(ResourceAttributesUpdateRequest(
                    '%s/%s' % (cardvm, ifname.replace('/', '-')), [
                        AttributeNameValue('vMX Port Address', ifname),
                        AttributeNameValue('Requested vNIC Name', nicname.replace('Network adapter ', '')),
                        AttributeNameValue('MAC Address', mac),
                    ]
                ))

        api.CreateResources(tocreate)
        api.SetAttributesValues(attrupdates)

        intfpool = sorted(intfpool)
        log('intfpool before: %s' % intfpool)
        for c in rd.Connectors:
            name2attr = {}
            for a in c.Attributes:
                name2attr[a.Name] = a.Value

            if context.resource.name == c.Source or context.resource.name == c.Target:
                req = 'Requested Source vNIC Name' if context.resource.name == c.Source else 'Requested Target vNIC Name'
                if req in name2attr:
                    avreq = name2attr[req]
                    if avreq in intfpool:
                        intfpool.remove(avreq)

        log('intfpool after: %s' % intfpool)

        connector_requests = []
        removeconnectors = []
        mgmtconnectors = []
        bb = ''
        for c in rd.Connectors:
            bb += c.Source + ' -- ' + c.Target + '\n'
        log(bb)

        for c in rd.Connectors:
            name2attr = {}
            for a in c.Attributes:
                name2attr[a.Name] = a.Value

            if context.resource.name == c.Source or context.resource.name == c.Target:
                req = 'Requested Source vNIC Name' if context.resource.name == c.Source else 'Requested Target vNIC Name'
                if req in name2attr:
                    avreq = name2attr[req]
                    del name2attr[req]
                    log('Connector attribute %s' % avreq)
                else:
                    avreq = 'AUTO'
                    log('Blank connector attribute')

                if avreq == 'AUTO':
                    av = intfpool.pop(0)
                    log('Pool allocated interface %s' % av)
                elif avreq in ['ge', 'fe', 'te', 'et', 'xe']:
                    av = ''
                    for i in range(len(intfpool)):
                        if intfpool[i].startswith(avreq):
                            av = intfpool.pop(i)
                            log('Pool allocated interface type %s: %s' % (avreq, av))
                            break
                    if not av:
                        log('No interfaces available for requested type %s' % avreq)
                        av = intfpool.pop(0)
                        api.WriteMessageToReservationOutput(resid, 'Warning: No interfaces available for requested type %s. Allocated %s instead.' % (avreq, av))
                elif avreq.startswith('ge-') or \
                        avreq.startswith('fe-') or \
                        avreq.startswith('te-') or \
                        avreq.startswith('et-') or \
                        avreq.startswith('xe-'):
                    av = avreq
                    log('Explicit interface request %s' % av)
                else:
                    av = ''
                    log('Skipping management interface request %s' % avreq)
                log('Pool now %s' % intfpool)
                if av:
                    av2 = av
                    for s in ['ge', 'fe', 'te', 'et', 'xe']:
                        av2 = av2.replace(s+'-', '')
                    vfpno = int(av2.split('-')[0])
                    if context.resource.name == c.Source:
                        src = cardaddrstr2cardvmname[str(vfpno)] + '/' + av
                        tgt = c.Target
                    else:
                        src = c.Source
                        tgt = cardaddrstr2cardvmname[str(vfpno)] + '/' + av
                    connector_requests.append((src, 0, tgt, 0, c.Alias, name2attr))
                    removeconnectors.append((c.Source, c.Target))
                else:
                    mgmtconnectors.append((c.Source, c.Target))

        log('connector requests: %s' % connector_requests)

        for c in removeconnectors:
            api.RemoveConnectorsFromReservation(resid, [c[0], c[1]])

        api.SetConnectorsInReservation(resid, [
            SetConnectorRequest(source, target, 'bi', alias)
            for source, _, target, _, alias, _ in connector_requests
        ])
        for source, sourcenic, target, targetnic, _, name2value in connector_requests:
            tc = []
            if sourcenic > 0:
                tc.append(AttributeNameValue('Requested Source vNIC Name', str(sourcenic)))
            if targetnic > 0:
                tc.append(AttributeNameValue('Requested Target vNIC Name', str(targetnic)))
            # if netid > 0:
            #     tc.append(AttributeNameValue('Selected Network', str(targetnic)))

            for name, value in name2value.iteritems():
                tc.append(AttributeNameValue(name, value))

            if tc:
                api.SetConnectorAttributes(resid, source, target, tc)
            api.WriteMessageToReservationOutput(resid, 'Adding connector %s.%s &lt;-&gt; %s.%s' % (source, sourcenic, target, targetnic))

        api.WriteMessageToReservationOutput(resid, 'vMX IP is %s' % vmxeip)
        api.UpdateResourceAddress(context.resource.name, vmxeip)
        api.SetAttributeValue(context.resource.name, 'VFP Card App Name Prefix', 'DONE')

        mgmtendpoints = []
        for c in mgmtconnectors:
            a, b = c
            mgmtendpoints.append(a)
            mgmtendpoints.append(b)
        if mgmtendpoints:
            api.ConnectRoutesInReservation(resid, mgmtendpoints, 'bi')

        api.AutoLoad(context.resource.name)
