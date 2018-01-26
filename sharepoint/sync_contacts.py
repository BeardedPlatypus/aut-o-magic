#!/usr/bin/env python
"""
Sync Exchange Online contacts with a specified Share Point list of contacts
"""

import subprocess
import os
import getpass

from time import sleep


__author__ = "Maarten Tegelaers"
__copyright__ = "Copyright 2018, Maarten Tegelaers"
__credits__ = ["Maarten Tegelaers", "Sven Quax"]

__license__ = "All Rights Reserved"
__version__ = "0.1"
__status__ = "development"


GET_SP_OBJECTS_MODULE_PATH = ""


class PowerShellSession:
    """
    PowerShellSession manages a single PowerShellSession. It provides an
    interface for sending commands, as well as a close function.
    """
    def __init__(self,
                 tmp_out_name="stdout.tmp",
                 powershell_exe="C:\\WINDOWS\\system32\\WindowsPowerShell\\v1.0\\powershell.exe"):
        """
        Construct a new PowerShellSession with the given tmp_out_name and
        power_shell_exe path.

        :param tmp_out_name: The temporary file used to write stdout / stderr to.
        :param powershell_exe: The path to the powershell.exe
        """
        self._tmp_out_name = tmp_out_name
        self._tmp_err_name = tmp_err_name

        self._f_out_w = open(tmp_out_name, 'wb')
        self._f_out_r = open(tmp_out_name, 'r')

        self._ps_process = subprocess.Popen([powershell_exe, "-NoLogo"],
                                            stdin=subprocess.PIPE,
                                            stdout=self._f_out_w,
                                            stderr=self._f_out_w)

        # ensure the first interactive prompt has been printed and read
        expected_string = "PS {}>".format(os.getcwd())
        while True:
            if expected_string in self._f_out_r.readline():
                break
            else:
                sleep(0.1)

    def send_cmd(self, cmds : list) -> str:
        """
        Send the specified commands to this PowerShellSession.

        :param cmds: List of byte strings containing commands

        :returns: The output of the powershell session
        """
        # construct cmd
        if cmds:
            # construct a single cmd out of the provided cmds
            cmd_str = ""
            for cmd in cmds:
                cmd_stripped = cmd.strip()
                if cmd_stripped[-1] != ';':
                    cmd_stripped += ';'
                cmd_str += cmd_stripped
            cmd_str += '\n' # simulate enter press from user
            cmd_str = str.encode(cmd_str)

            # send the cmd to the powershell process
            self._ps_process.stdin.write(cmd_str)
            self._ps_process.stdin.flush()

            # wait for the cmd to finish
            cmd_str_utf = cmd_str.decode("utf-8")
            result = ""

            #TODO: Read error messages properly

            expected_string = "PS {}>".format(os.getcwd())
            while True:
                line = self._f_out_r.readline()
                if not line:
                    sleep(0.1)
                else:
                    if expected_string in line:
                        break
                    elif cmd_str_utf in line:
                        continue
                    else:
                        result += line

            return result
        else:
            return ""

    def close(self):
        """
        Close this PowerShellProcess.
        """
        self._ps_process.terminate()
        self._f_out_w.close()
        self._f_out_r.close()

        #os.remove(self._tmp_out_name)
        #os.remove(self._tmp_err_name)


def authenticate_exchange_online(ps_session: PowerShellSession, user: str, password: str):
    """
    Connect the specified ps_session with Exchange Online given the
    specified user and password

    :param ps_session: The powershell session to be connected to Exchange online.
    :param user: The user name with which should be connected to Exchange online.
    :param password: The password accompanying the user.
    """
    # authenticate the user in powershell without a prompt
    # https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.security/get-credential?view=powershell-5.1 example 5

    cmds = ['$user = "{}"'.format(user),                                                                                      # set user to the specified user
            '$PWord = ConvertTo-SecureString -String "{}" -AsPlainText -Force'.format(password),                              # set password to the specified password
            '$UserCredential = New-Object -TypeName "System.Management.Automation.PSCredential" -ArgumentList $User, $PWord', # obtain the credentials without prompting user
            # obtain session with credentials
            '$Session = New-PSSession -ConfigurationName Microsoft.Exchange -ConnectionUri https://outlook.office365.com/powershell-liveid/ -Credential $UserCredential -Authentication Basic -AllowRedirection',
            'Import-PSSession $Session',                                                                                      # import session into this powershell
           ]
    ps_session.send_cmds(cmds)


def close_exchange_online(ps_session: PowerShellSession):
    """
    Disconnect the specified ps_session from exchange online.

    Should be called before closing PowerShellSession, if
    authenticate_exchange_online was called

    :param ps_session: The powershell session to be connected to Exchange online.
    """
    ps_session.send_cmd("Remove-PSSession $Session")


def sort_contacts(list_of_contacts: list) -> list:
    """
    Sort the list_of_contacts by name.

    :param list_of_contacts: list of contacts to be sorted

    :returns: A sorted list of contacts
    """
    n_contacts = len(list_of_contacts)
    li = (list(list_of_contacts), [None,] * n_contacts)
    i_input_list = 0
    chunk_size = 1

    while (chunk_size < n_contacts):
        offset_in = 0
        offset_out = 0
        i = 0
        j = 0

        while offset_out < n_contacts:
            cursor_i = offset_in + i
            cursor_j = offset_in + chunk_size + j

            if i < chunk_size and j < chunk_size and cursor_i < n_contacts and cursor_j < n_contacts:
                if li[i_input_list][offset_in + i]["name"] < li[i_input_list][offset_in + chunk_size + j]["name"]:
                    li[i_input_list + 1 & 1][offset_out] = li[i_input_list][cursor_i]
                    i += 1
                else:
                    li[i_input_list + 1 & 1][offset_out] = li[i_input_list][cursor_j]
                    j += 1
                offset_out += 1
            elif i < chunk_size and cursor_i < n_contacts and (j >= chunk_size or cursor_j >= n_contacts):
                li[i_input_list + 1 & 1][offset_out] = li[i_input_list][cursor_i]
                i += 1
                offset_out += 1
            elif j < chunk_size and cursor_j < n_contacts and i >= chunk_size:
                li[i_input_list + 1 & 1][offset_out] = li[i_input_list][cursor_j]
                j += 1
                offset_out += 1
            else:
                offset_in += 2 * chunk_size
                i = 0
                j = 0

        chunk_size *= 2
        i_input_list = i_input_list + 1 & 1
    return li[i_input_list]


def get_target_contacts(ps_session: PowerShellSession) -> list:
    """
    Get the contacts currently stored in Exchange Online

    :param ps_session: an authenticated powershell session from which the
                       contacts will be retrieved.
    """
    contacts_list = ps_session.send_cmd([b"Get-MailContact -ResultSize Unlimited"]).splitlines()
    result = []

    name_size = len(contacts_list[0].split("Alias", 1)[0])
    for l in contacts_list[1:]:
        if l: # filter out empty lines
            name = l[:name_size].strip()
            details_contact = ps_session.send_cmd([str.encode('Get-MailContact -Identity "{}" | Format-List'.format(name))])

            for l_detail in details_contact.splitlines():
                vals = l_detail.split(":", 1)
                if vals[0].strip() == "EmailAddresses":
                    email_address = vals[0].strip()[1:-1].split(":", 1)[1]
                    break
            result.append({"name": name,
                           "email": email_address,
                          })
    return result


def get_source_contacts(ps_session: PowerShellSession, user: str, password: str, sp_url: str, l_name: str) -> list:
    """
    Get the contacts currently stored in the global contact list in SP Lists

    :param ps_session: an authenticated powershell session from which the
                       contacts will be retrieved.
    """
    # import the appropriate cmdlet to retrieve the list
    ps_session.send_cmd([str.encode('import-module {}'.format(GET_SP_OBJECTS_MODULE_PATH))])
    # retrieve all elements in the specified list
    list_items = ps_session.send_cmd(['$PWord = ConvertTo-SecureString -String "{}" -AsPlainText -Force'.format(password), # set password to the specified password,
                                      'Get-SPOObject -Username {} -password $PWord -url {} -object "web/lists/getbytitle("{}")/items'.format(user, sp_url, l_name)])

    element = {}
    result = []
    map_to_key = {"E-mailadres": "email",
                  "Volledige naam": "name",
                 }
    for l in list_items.splitlines():
        vals_raw = l.split(":", 1)

        raw_key = vals_raw[0].strip()

        if raw_key in map_to_key:
            key = map_to_key[raw_key]
            if key in element:
                result.append(element)
                element = {}
            element[key] = vals_raw[1].strip()
    result.append(element)
    # TODO: add assertion that no wrong elements are added
    return result


def sync_contacts(ps_session: PowerShellSession, list_sync_src: list, list_sync_target: list) -> tuple:
    """
    Sync the Exchange Online contacts with the SharePoint List contacts

    :param ps_session: an authenticated powershell session from which the
                       contacts will be retrieved.
    :param list_sync_src: Ordered list of contacts obtained through get_source_contacts
    :param list_sync_target: Ordered list of contacts obtained through get_target_contacts
    """
    # list sync is the source, the target should be the same as source after it is updated with source

    while list_sync_src and list_sync_target:
        if list_sync_src[0]["name"] == list_sync_target[0]["name"]:
            # Elements are the same, check if email needs to be updated
            if list_sync_src[0]["email"] != list_sync_target[0]["email"]:
                cmd = 'Set-MailContact -Identity "{}" -ExternalEmailAddress "{}"'.format(list_sync_src[0]["name"], list_sync_src[0]["email"])
                cmd_result = ps_session.send_cmd([cmd,])
                # TODO: add result stuff here

            list_sync_src    = list_sync_src[1:]
            list_sync_target = list_sync_target[1:]

        elif list_sync_src[0]["name"] < list_sync_target[0]["name"]:
            # There exists a name in the src list which does not exist in the target list,
            # thus this contact needs to be created.
            cmd = 'New-MailContact -Name "{}" -ExternalEmailAddress "{}"'.format(list_sync_src[0]["name"], list_sync_src[0]["email"])
            cmd_result = ps_session.send_cmd([cmd,])
            # TODO: add result stuff here

            list_sync_src    = list_sync_src[1:]

        else:
            # There exists a name in the target list which does not exist in the source list,
            # Thus this contact needs to be removed.
            cmd = 'Remove-MailContact -Identity "{}"'.format(list_sync_src[0]["name"])
            cmd_result = ps_session.send_cmd([cmd,])

            # TODO: add result stuff here
            list_sync_target = list_sync_target[1:]


if __name__ == "__main__":
    print("Sync Exchange Online and SharePoint Contact List.")
    # Assuming exchange online user and password are the same only prompt once
    user = input("User: ")
    password = getpass.getpass()

    ps_session = PowerShellSession()
    authenticate_exchange_online(ps_session, user, password)

    target_contacts = sort_contacts(get_target_contacts(ps_session))
    # TODO nams share_point url and list name
    source_contacts = sort_contacts(get_source_contacts(ps_session, user, password, sp_url="", l_name="" ))
    sync_contacts(ps_session, source_contacts, target_contacts)

    close_exchange_online(ps_session)
    ps_session.close()

