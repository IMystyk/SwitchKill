#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import os

from fabric import Connection
import invoke
import pexpect
import logging
from datetime import datetime

logging.basicConfig(filename='logfile{}.log'.format(str(datetime.now())))


class AlcatelCommands:  # All methods return list of strings (commands)

    error = ["Error"]

    def __init__(self):  # Constructor
        pass

    def ShutAllPorts(self, portNumber, savePort):  # Shut all ports on the switch excluding savePort
        """
        arg
        ---
        portNumber : int : Number of ports in switch
        savePort : int : Port that we don't wanna disable

        """
        commands = []
        for i in range(1, portNumber + 1):
            if i != savePort:
                commands.append("interface 1/1/{0} admin-state disable".format(i))
        return commands

    def TurnOnAllPorts(self, portNumber):  # Turn on all ports on the switch
        """
        arg
        ---
        portNumber : int : Number of ports in switch

        """
        commands = []
        for i in range(1, portNumber + 1):
            commands.append("interface 1/1/{0} admin-state enable".format(i))
        return commands


class ExtremeXOSCommands:  # All methods return list of strings (commands)
    error = ["Error"]

    def __init__(self):  # Constructor
        pass

    def ShutAllPorts(self, portNumber, savePort):  # Shut all ports on the switch excluding savePort
        """
        arg
        ---
        portNumber : int : Number of ports in switch
        savePort : int : Port that we don't wanna disable

        """
        commands = []
        for i in range(1, portNumber + 1):
            if i != savePort:
                commands.append("disable port {0}".format(i))
        return commands

    def TurnOnAllPorts(self, portNumber):  # Turn on all ports on the switch
        """
        arg
        ---
        portNumber : int : Number of ports in switch

        """
        commands = []
        for i in range(1, portNumber + 1):
            commands.append("enable port {0}".format(i))
        return commands


class CiscoCommands:  # All methods return list of strings (commands)
    error = ["Error"]
    ciscoString = ["Cisco"]

    def __init__(self, ciscoConnection):  # Constructor
        self.ciscoConnection = ciscoConnection
        pass

    def ShutAllPorts(self, portNumber, savePort):  # Shut all ports on the switch excluding savePort
        """
        arg
        ---
        portNumber : int : Number of ports in switch
        savePort : int : Port that we don't wanna disable

        """

        self.ciscoConnection.sendline("config terminal")
        self.ciscoConnection.expect("[#]")

        for i in range(1, portNumber + 1):
            if i != savePort:
                self.ciscoConnection.sendline("interface Fa0/{0}".format(i))
                self.ciscoConnection.expect("[#]")
                self.ciscoConnection.sendline("shutdown")

        self.ciscoConnection.sendline("exit")
        self.ciscoConnection.expect("[>#]")
        return self.ciscoString

    def TurnOnAllPorts(self, portNumber):  # Turn on all ports on the switch
        """
        arg
        ---
        portNumber : int : Number of ports in switchu

        """

        self.ciscoConnection.sendline("config terminal")
        self.ciscoConnection.expect("[#]")

        for i in range(1, portNumber + 1):
            self.ciscoConnection.sendline("interface Fa0/{0}".format(i))
            self.ciscoConnection.expect("[#]")
            self.ciscoConnection.sendline("no shutdown")

        self.ciscoConnection.sendline("exit")
        self.ciscoConnection.expect("[#]")
        return self.ciscoString


class ConnectionHost:

    def __init__(self, host, user, password):  # Constructor, save data to log in in ssh
        self.host = host
        self.user = user
        self.password = password

    def Connect(self):  # Connection to ssh and choose apropriate device
        self.connection = Connection(host=self.host, user=self.user, connect_kwargs={"password": self.password})

        # Check if it's an Alcatel Switch
        try:
            output = self.connection.run("show microcode", hide=True)
            if ("alcatel" in output.stdout.lower()):
                print("Alcatel")
                return AlcatelCommands()

        except Exception:
            pass

        # Check if it's an Cisco or ExtremeXOS Switch
        try:
            output = self.connection.run("show version", hide=True)
            if "cisco" in output.stdout.lower():
                print("Logging into Cisco")

                try:
                    self.connection = pexpect.spawn(
                        "ssh -oKexAlgorithms=+diffie-hellman-group1-sha1 -c aes128-cbc {0}@{1}".format(self.user,
                                                                                                       self.host))
                    self.connection.expect("[Pp]assword: ")
                    self.connection.sendline("{0}".format(self.password))

                    try:
                        self.connection.expect("[>#]")
                    except Exception:
                        self.connection.sendline("enable")
                        self.connection.expect("[Pp]assword: ")
                        self.connection.sendline("cisco")

                    self.connection.sendline(" ")

                    try:
                        self.connection.expect("[>#]")
                    except Exception:
                        print('Cisco - unable to enter privileged mode')
                        return None

                    print("Alcatel")
                    return CiscoCommands(self.connection)

                except Exception:
                    print("Can't connect to Cisco")
                    return None

            elif "extremexos" in output.stdout.lower():
                print("ExtremeXOS")
                return ExtremeXOSCommands()

        except Exception:
            return None

    def RunCommand(self, commands, save=False):  # Run passed commands through ssh, can save output to file
        outputs = []

        if commands[0] == "Cisco":
            print("Done")
            return

        if commands[0] == "Error":
            print(commands[0])
            return
        for command in commands:
            try:
                outputs.append(self.connection.run(command, timeout=40))
            except invoke.exceptions.CommandTimedOut:
                print("Timeout, if you invoked reload command on the switch this message has to be shown")

        # Save output to file
        if save == True:
            f = open("Results.txt", "a")
            for output in outputs:
                f.write(output.stdout)
            f.close()


def GetDevicesData(dataFile):
    """
    Returns dictionary with devices' ips and other data
    """
    f = open(dataFile, "r")
    data = ""
    for line in f:
        if "BEGIN" in line or "END" in line:
            continue
        data += line

    allDevicesData = dict()
    data = data.split('\n')
    for line in data:
        if line == "":
            continue
        else:
            line = line.split()
        try:
            if len(line) == 5:
                allDevicesData[line[0]] = {"portAmount": line[1], "management_port": line[2], "username": line[3],
                                           "password": line[4]}
            elif len(line) == 4:
                allDevicesData[line[0]] = {"portAmount": line[1], "management_port": line[2], "username": line[3],
                                           "password": ""}
        except IndexError:
            print("File was encrypted or some information is missing in conf file")
            return dict()

    return allDevicesData


# Connect to devices and turn on/off all ports except management port
while True:
    print('')
    print("Welcome in PortKiller")
    print("---------------------")
    print("1. Encrypt conf file")
    print("2. Decrypt conf file")
    print("3. Turn on all devices from conf file")
    print("4. Turn off all devices from conf file")
    print("5. Exit")

    while True:
        try:
            choice = int(raw_input(">>>>:"))
            break
        except ValueError:
            print("Incorrect value")
            continue

    if choice == 1:  # Encrypt conf file
        keyFileName = raw_input("Name file which will store your key: ")
        confFileName = raw_input("Conf file name: ")
        os.system('python3 main.py --mode encrypt --key {0} --file {1}'.format(keyFileName, confFileName))
        print("Your conf file has been encypted")

    if choice == 2:  # Decrypt conf file
        keyFileName = raw_input("File which store your key: ")
        confFileName = raw_input("Conf file name: ")
        os.system('python3 main.py --mode decrypt --key {0} --file {1}'.format(keyFileName, confFileName))
        print("Your conf file has been decrypted")

    if choice == 3 or choice == 4:  # Turn on/off ports

        while True:  # Check if your conf file is encrypted/decrypted
            encrypted = raw_input("Is your conf file encrypted ( yes, no ): ")
            if encrypted == "yes" or encrypted == "no":
                break
            else:
                print("Incorrect value")

        if encrypted == "no":
            allDevicesData = GetDevicesData("data.txt")
        elif encrypted == "yes":
            keyFileName = raw_input("File which store your key: ")
            confFileName = raw_input("Conf file name: ")
            out = os.system('python3 main.py --mode decrypt --key {0} --file {1}'.format(keyFileName, confFileName))

            if out == -1:  # Error occurred
                continue
            elif out == -2:  # File is decrypted
                allDevicesData = GetDevicesData("data.txt")
            else:
                allDevicesData = GetDevicesData("data.txt")
                os.system('python3 main.py --mode encrypt --key {0} --file {1}'.format(keyFileName, confFileName))

        if (
                len(allDevicesData) == 0):  # If your file was encypted and user choose that this file wasn't encypted or some value is missing
            continue

        if choice == 3:
            state = "on"
        elif choice == 4:
            state = "off"

        # For home testing purpose this part is comment
        for deviceIp in allDevicesData:  # Connect to certain devices and turn on/off their ports
            c = ConnectionHost(deviceIp, allDevicesData[deviceIp].get('username'),
                               allDevicesData[deviceIp].get('password'))
            device = c.Connect()

            if device is not None:
                if state == "off":
                    c.RunCommand(device.ShutAllPorts(allDevicesData[deviceIp].get('portAmount'),
                                                     allDevicesData[deviceIp].get('management_port')), False)
                elif state == "on":
                    c.RunCommand(device.TurnOnAllPorts(allDevicesData[deviceIp].get('portAmount')), False)
            else:
                print("Unknown device")
                logging.warning('{0} is an Unknown device'.format(deviceIp))

        print("All ports excluding management port was turn {0}".format(state))

    if choice == 5:  # Exit
        break

"""
# Connection to Alcatel switch
#c = ConnectionHost("10.0.0.23","admin","switch")

# Connection to cisco switch
#c = ConnectionHost("10.0.0.13","cisco","cisco")

# Connection to ExtremeXOS switch
#c = ConnectionHost("10.0.0.3","admin","")

# Connect
device = c.Connect()


#c.RunCommand(device.ShutAllPorts(24,5),False)
if(not(device is None)):
#c.RunCommand(device.ShutAllPorts(24,9),False)
c.RunCommand(device.TurnOnAllPorts(24),True)
else:
print("Unknown device")

"""
