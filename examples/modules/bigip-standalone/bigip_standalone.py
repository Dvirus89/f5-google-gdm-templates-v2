# Copyright 2021 F5 Networks All rights reserved.
#
# Version 0.1.0

"""Creates BIGIP Instance"""
COMPUTE_URL_BASE = 'https://www.googleapis.com/compute/v1/'


def generate_name(prefix, suffix):
    """ Generate unique name """
    return prefix + "-" + suffix


def create_instance(context):
    """ Create standalone instance """
    # Build instance property lists
    required_properties = ['zone']
    optional_properties = [
        'advancedMachineFeatures',
        'canIpForward',
        'confidentialInstanceConfig',
        'deletionProtection',
        'description',
        'disks',
        'displayDevice',
        'guestAccelerators',
        'hostname',
        'labels',
        'machineType',
        'minCpuPlatform',
        'privateIpv6GoogleAccess',
        'reservationAffinity',
        'resourcePolicies',
        'scheduling',
        'serviceAccounts',
        'shieldedInstanceConfig',
        'shieldedInstanceIntegrityPolicy',
        'tags'
    ]
    name = context.properties.get('name') or \
        context.env['name']
    instance_name = generate_name(context.properties['uniqueString'], name)
    properties = {}
    # Setup Defaults - property updated to given value when property exists in config
    properties.update({
            'canIpForward': True,
            'description': 'Standalone F5 BIG-IP.',
            'disks': [{
                'deviceName': 'boot',
                'type': 'PERSISTENT',
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': ''.join([COMPUTE_URL_BASE, 'projects/',
                    'f5-7626-networks-public/global/images/', context.properties['imageName'],
                    ])
                }
            }],
            'hostname': ''.join([instance_name,
            '.c.', context.env['project'], '.internal']),
            'machineType': ''.join([COMPUTE_URL_BASE, 'projects/', context.env['project'],
            '/zones/', context.properties['zone'], '/machineTypes/',
            context.properties['instanceType']]),
            'metadata': metadata(context),
            'name': instance_name,
            'networkInterfaces': create_nics(context)
    })
    for config in context.properties:
        # Setup Instance Properties
        properties.update(
            {
                p: context.properties[p]
                for p in required_properties
            }
        )
        properties.update(
            {
                p: context.properties[p]
                for p in optional_properties
                if p in config
            }
        )
    instance = {
            'type': 'compute.v1.instance',
            'name': instance_name,
            'properties': properties
    }
    return instance

def create_nics(context):
    """ Create interface configuration for instance """
    # Build interface properties lists
    interface_required_properties = ['network', 'subnetwork']
    interface_optional_properties = [
        'description',
        'networkIP',
        'ipv6Address',
        'networkTier',
        'stackType',
        'queueCount',
        'nicType',
        'aliasIpRanges',
        'ipv6AccessConfigs',
        'accessConfigs',
        'name'
    ]
    network_interfaces = []
    for network in context.properties.get('networkInterfaces', []):
        # Build interface configuration
        interface_properties = {p: network[p] for p in interface_required_properties}
        interface_properties.update(
            {
                p: network[p]
                for p in interface_optional_properties
                if p in network
            }
        )
        network_interfaces.append(
            interface_properties
        )
    return network_interfaces

def metadata(context):
    """ Create metadata for instance """
    number_of_interfaces = len(context.properties.get('networkInterfaces', []))
    multi_nic = number_of_interfaces > 1
    metadata_config = {
                'items': [{
                    'key': 'startup-script',
                    'value': ('\n'.join(['#!/bin/bash',
                                    'if [ -f /config/startup_finished ]; then',
                                    '    exit',
                                    'fi',
                                    'if [ -f /config/first_run_flag ]; then',
                                    '   echo "Skip first run steps, already ran."',
                                    'else',
                                    '   /usr/bin/mkdir -p  /var/log/cloud /config/cloud /var/lib/cloud/icontrollx_installs /var/config/rest/downloads',
                                    '   LOG_FILE=/var/log/cloud/startup-script-pre-nic-swap.log',
                                    '   /usr/bin/touch $LOG_FILE',
                                    '   npipe=/tmp/$$.tmp',
                                    '   /usr/bin/trap "rm -f $npipe" EXIT',
                                    '   /usr/bin/mknod $npipe p',
                                    '   /usr/bin/tee <$npipe -a $LOG_FILE /dev/ttyS0 &',
                                    '   exec 1>&-',
                                    '   exec 1>$npipe',
                                    '   exec 2>&1',
                                    '   /usr/bin/cat << \'EOF\' > /config/nic-swap.sh',
                                    '   #!/bin/bash',
                                    '   /usr/bin/touch /config/nic_swap_flag',
                                    '   /usr/bin/setdb provision.managementeth eth1',
                                    '   /usr/bin/setdb provision.extramb 1000',
                                    '   /usr/bin/setdb restjavad.useextramb true',
                                    '   reboot',
                                    'EOF',
                                    '   /usr/bin/cat << \'EOF\' > /config/startup-script.sh',
                                    '   #!/bin/bash',
                                    '   LOG_FILE=/var/log/cloud/startup-script-post-swap-nic.log',
                                    '   touch $LOG_FILE',
                                    '   npipe=/tmp/$$.tmp',
                                    '   /usr/bin/trap "rm -f $npipe" EXIT',
                                    '   /usr/bin/mknod $npipe p',
                                    '   /usr/bin/tee <$npipe -a $LOG_FILE /dev/ttyS0 &',
                                    '   exec 1>&-',
                                    '   exec 1>$npipe',
                                    '   exec 2>&1',
                                    '   NUMBER_OF_INTERFACES=' + str(number_of_interfaces),
                                    '   if [ "${NUMBER_OF_INTERFACES}" -ge 2 ]; then',
                                    '       # Need to remove existing and recreate a MGMT default route as not provided by DHCP on 2nd NIC Route name must be same as in DO config.',
                                    '       tmsh modify sys global-settings mgmt-dhcp disabled',
                                    '       tmsh delete sys management-route all',
                                    '       tmsh delete sys management-ip all',
                                    '       source /usr/lib/bigstart/bigip-ready-functions',
                                    '       wait_bigip_ready',
                                    '       # Wait until a little more until dhcp/chmand is finished re-configuring MGMT IP w/ "chmand[4267]: 012a0003:3: Mgmt Operation:0 Dest:0.0.0.0"',
                                    '       sleep 15',
                                    '       MGMT_GW=$(egrep static-routes /var/lib/dhclient/dhclient.leases | tail -1 | grep -oE \'[^ ]+$\' | tr -d \';\')',
                                    '       tmsh create sys management-route defaultManagementRoute network default gateway $MGMT_GW mtu 1460',
                                    '       tmsh modify sys global-settings remote-host add { metadata.google.internal { hostname metadata.google.internal addr 169.254.169.254 } }',
                                    '       tmsh save /sys config',
                                    '   fi',
                                    '   # install and run f5-bigip-runtime-init',
                                    '   bash /var/config/rest/downloads/f5-bigip-runtime-init.gz.run -- \'--cloud gcp\'',
                                    '   /usr/bin/cat /config/cloud/runtime-init-conf.yaml',
                                    '   /usr/local/bin/f5-bigip-runtime-init --config-file /config/cloud/runtime-init-conf.yaml',
                                    '   /usr/bin/touch /config/startup_finished',
                                    'EOF',
                                    '   /usr/bin/chmod +x /config/nic-swap.sh',
                                    '   /usr/bin/chmod +x /config/startup-script.sh',
                                    '   MULTI_NIC=' + str(multi_nic),
                                    '   RUNTIME_CONFIG=' + str(context.properties['bigIpRuntimeInitConfig']),
                                    '   for i in {1..30}; do',
                                    '       /usr/bin/curl -fv --retry 1 --connect-timeout 5 -L ' + str(context.properties['bigIpRuntimeInitPackageUrl']) + ' -o "/var/config/rest/downloads/f5-bigip-runtime-init.gz.run" && break || sleep 10',
                                    '   done',
                                    '   if [[ ${RUNTIME_CONFIG} =~ ^http.* ]]; then',
                                    '       for i in {1..30}; do',
                                    '           /usr/bin/curl -fv --retry 1 --connect-timeout 5 -L "${RUNTIME_CONFIG}" -o /config/cloud/runtime-init-conf.yaml && break || sleep 10',
                                    '       done',
                                    '   else',
                                    '       /usr/bin/printf \'%s\\n\' "${RUNTIME_CONFIG}" | jq .  > /config/cloud/runtime-init-conf.yaml',
                                    '   fi',
                                    '   /usr/bin/touch /config/first_run_flag',
                                    'fi',
                                    'if [[ ${MULTI_NIC} == "True" ]]; then',
                                    '   nohup /config/nic-swap.sh &',
                                    'else',
                                    '   /usr/bin/touch /config/nic_swap_flag',
                                    'fi',
                                    'if [ -f /config/nic_swap_flag ]; then',
                                    '   nohup /config/startup-script.sh &',
                                    'fi'
                                    ])
                    )
                }]
    }
    return metadata_config

def create_instance_outputs(context):
    """ Create standalone instance outputs"""
    name = context.properties.get('name') or \
        context.env['name']
    instance_name = generate_name(context.properties['uniqueString'], name)
    instance = {
        'name': 'instanceName',
        'value': instance_name
    }
    return instance

def generate_config(context):
    """ Create single bigip instance"""
    # build resources
    resources = [create_instance(context),]
    outputs = [create_instance_outputs(context)]
    return {'resources': resources, 'outputs': outputs}
