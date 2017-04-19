#!/usr/bin/env python
"""
 Written by Michael Rice
 Github: https://github.com/michaelrice
 Website: https://michaelrice.github.io/
 Blog: http://www.errr-online.com/
 This code has been released under the terms of the Apache 2 licenses
 http://www.apache.org/licenses/LICENSE-2.0.html

 Script to quickly get all the VMs with a set of common properties.

"""

from __future__ import print_function
import atexit
from time import clock
import ssl
from pyVim import connect
from pyVmomi import vim
from tools import pchelper, tasks
import json 
import logging

# set the project root directory as the static folder, you can set others.
# List of properties.
# See: http://goo.gl/fjTEpW
# for all properties.
vm_properties = ["name", "config.uuid", "guest.net", "guest.ipAddress","guest.guestState", 
                    "config.guestFullName", "network"]
net_properties = ["name", "vm", "summary.name"]
host_properties = ["name", "config.network.vswitch", "config.network.portgroup", 
                    "vm", "config.product.osType", "summary.overallStatus", 
                    "hardware.systemInfo.model", "hardware.systemInfo.vendor"]

class VMWareUtil :

    def __init__(self, vCenterIp, userName, password):
        self.vCenterIp = vCenterIp
        self.userName = userName
        self.password = password
        self.service_instance = None

    def _connect(self):
        
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.verify_mode = ssl.CERT_NONE
            self.service_instance = connect.SmartConnect(host= self.vCenterIp,
                                                    user= self.userName,
                                                    pwd= self.password,
                                                    port= 443,
                                                    sslContext= context)
            atexit.register(connect.Disconnect, self.service_instance)
            #atexit.register(endit)
        except IOError as e:
            pass

        if not self.service_instance:
            raise SystemExit("Unable to connect to host with supplied info.")

    def check_connectivity(self):
        try:
            if not self.service_instance :
                self._connect()
            _content = self.service_instance.RetrieveContent()
        except IOError as e:
            logging.info('re-connect vmware vcenter.... ')
            self._connect()

    def reconfigureVM(self, uuid, portGroup):
        self.check_connectivity()
        _content = self.service_instance.RetrieveContent()
        target_vm = _content.searchIndex.FindByUuid(None, uuid, True)
        device_change = []
        for device in target_vm.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualEthernetCard):
                nicspec = vim.vm.device.VirtualDeviceSpec()
                nicspec.operation = \
                    vim.vm.device.VirtualDeviceSpec.Operation.edit
                nicspec.device = device
                nicspec.device.wakeOnLanEnabled = True

                if True:
                    nicspec.device.backing = \
                        vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                    nicspec.device.backing.network = \
                        pchelper.get_obj(_content, [vim.Network], portGroup)
                    nicspec.device.backing.deviceName = portGroup
                else:
                    network = pchelper.get_obj(_content,
                                      [vim.dvs.DistributedVirtualPortgroup],
                                      portGroup)
                    dvs_port_connection = vim.dvs.PortConnection()
                    dvs_port_connection.portgroupKey = network.key
                    dvs_port_connection.switchUuid = \
                        network.config.distributedVirtualSwitch.uuid
                    nicspec.device.backing = \
                        vim.vm.device.VirtualEthernetCard. \
                        DistributedVirtualPortBackingInfo()
                    nicspec.device.backing.port = dvs_port_connection

                nicspec.device.connectable = \
                    vim.vm.device.VirtualDevice.ConnectInfo()
                nicspec.device.connectable.startConnected = True
                nicspec.device.connectable.allowGuestControl = True
                device_change.append(nicspec)
                break

        config_spec = vim.vm.ConfigSpec(deviceChange=device_change)
        task = target_vm.ReconfigVM_Task(config_spec)
        retval = tasks.wait_for_tasks(self.service_instance, [task])
        print ("reconfigure result ", retval)
        return retval

    def lookupHost(self, hostMap, vmId):
        found = False
        key_host = None
        for key_host in hostMap:
            for vm in hostMap[key_host]['vms']:
                if vmId in vm.itervalues():
                    found = True
                    break
            if found:
                break
        if found:
            return key_host
        else:
            return None

    def lookupPortGroups(self, hostMap, host):
        portgroups = []
        for host_key in hostMap:
            for net in hostMap[host_key]['nets']:
                portgroups.append( net['name'])
        return portgroups


    def lookupHostList(self, hostMap):
        hosts = []
        for host_key in hostMap:
            hosts.append( host_key)
        return hosts

    def getInventory(self):
        self.check_connectivity()

        hosts = self.getHosts()
        vms = self._getVMs()
        for idx,vm in enumerate( vms[:]):
            vms[idx]['host'] = self.lookupHost( hosts, vm["vmId"])

        host_list = self.lookupHostList( hosts)
        for host in host_list:
            self.lookupPortGroups( hosts, host)

        return json.dumps(vms)

    def getHosts(self):
        self.check_connectivity()

        total_hosts = []
        hosts = {}
        self.root_folder = self.service_instance.content.rootFolder
        host_view = pchelper.get_container_view(self.service_instance,
                                   obj_type=[vim.HostSystem])
        host_data = pchelper.collect_properties(self.service_instance, view_ref=host_view,
                                      obj_type=vim.HostSystem,
                                      path_set=host_properties,
                                      include_mors=True)
        for host in host_data:
            hosts[ host['name']] = {}
            hosts[ host['name']]['nets'] = []
            portgroups = host["config.network.portgroup"]
            for portgroup in portgroups:
                spec = { "name": portgroup.spec.name, "vlanId" : portgroup.spec.vlanId, "vswitch": portgroup.vswitch }
                hosts[ host['name']]['nets'].append( spec)

            hosts[ host['name']]['vms'] = []
            vms = host["vm"]
            for vm in vms:
                spec = {"id": str(vm._moId)}
                hosts[ host['name']]['vms'].append( spec)
        #print( hosts)
        return hosts
        
    def _getPortGroups(self):
        self.check_connectivity()
        total_portgroups = []
        portgroups = {}
        self.root_folder = self.service_instance.content.rootFolder
        net_view = pchelper.get_container_view(self.service_instance,
                                   obj_type=[vim.Network])
        net_data = pchelper.collect_properties(self.service_instance, view_ref=net_view,
                                      obj_type=vim.Network,
                                      path_set=net_properties,
                                      include_mors=True)
        for net in net_data:
            #print( "{0} is name of {1}".format( net['name'], net['obj']._moId))
            portgroups[ net['obj']._moId] = net["name"]

        return portgroups

    def _getPortGroupName(self, _dict, _key, _default='N/A'):
        return _dict[_key] if _dict.has_key(_key) else _default

    def _getVMs(self):
        self.check_connectivity()
        total_vms = []
        self.root_folder = self.service_instance.content.rootFolder
        vm_view = pchelper.get_container_view(self.service_instance,
                                           obj_type=[vim.VirtualMachine])
        vm_data = pchelper.collect_properties(self.service_instance, view_ref=vm_view,
                                              obj_type=vim.VirtualMachine,
                                              path_set=vm_properties,
                                              include_mors=True)
        portgroups = self._getPortGroups()
        for vm in vm_data:
            #print(str(vm))
            if vm["guest.guestState"] != "running":
                continue
            macs =[]
            val = {}
            val['vmId'] = str(vm["obj"]._moId)
            val['uuid'] = str(vm["config.uuid"])
            val['vmName'] = str(vm["name"])
            val['vmGuest']= str(vm["config.guestFullName"])
            for nic in vm["guest.net"]:
                macs.append(nic.macAddress)
            val['vmNetwork'] = {}
            for idx,net in enumerate(vm["network"]):
                netcfg = { "portGroup": self._getPortGroupName(portgroups, net._moId, 'N/A'), 
                "macAddress": macs[idx] if len(macs) > idx else 'N/A', 
                "ipAddress": str(vm["guest.ipAddress"])}
                val['vmNetwork'][str(idx)] = netcfg
                #print(net._moId)
            total_vms.append(val)
        return total_vms
        #return json.dumps(total_vms)

if __name__ == '__main__':
    vmware = VMWareUtil('10.72.86.43', 'administrator@vsphere.local', '!234Qwer')
    vmware.connect()
    #print ( vmware._getVMs())
    #print ( vmware._getPortGroups())
    vmware.getInventory()
