from collections import OrderedDict

from cloudshell.shell.core.context_utils import get_resource_address, get_attribute_by_name_wrapper
from cloudshell.shell.core.dependency_injection.context_based_logger import get_logger_with_thread_id
from cloudshell.snmp.quali_snmp_cached import QualiSnmpCached

ERROR_MAP = OrderedDict(
    {r'[Ee]rror\s+saving\s+configuration': 'Save configuration error',
     r'syntax\s+error': 'Syntax error',
     r'[Uu]nknown\s+command': 'Uncnown command',
     r'[Ee]rror\s+.+': 'Error'})

DEFAULT_PROMPT = '[>%#]\s*$|[>%#]\s*\n'
CONFIG_MODE_PROMPT = r'.*#\s*$'

QUALISNMP_INIT_PARAMS = {'ip': get_resource_address,
                         'snmp_version': get_attribute_by_name_wrapper('SNMP Version'),
                         'snmp_user': get_attribute_by_name_wrapper('SNMP V3 User'),
                         'snmp_password': get_attribute_by_name_wrapper('SNMP V3 Password'),
                         'snmp_community': get_attribute_by_name_wrapper('SNMP Read Community'),
                         'snmp_private_key': get_attribute_by_name_wrapper('SNMP V3 Private Key')}


def create_snmp_handler():
    kwargs = {}
    for key, value in QUALISNMP_INIT_PARAMS.iteritems():
        if callable(value):
            kwargs[key] = value()
        else:
            kwargs[key] = value
    return QualiSnmpCached(**kwargs)


SNMP_HANDLER_FACTORY = create_snmp_handler

GET_LOGGER_FUNCTION = get_logger_with_thread_id