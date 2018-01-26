# Sharepoint scripts

## sync_contacts

Exchange Online does not provide a simple tool to sync its contacts to that
of a SharePoint Online List. This script ensures that after running, the 
Exchange Online contacts are equal to that provided in the SharePoint Online
List. It does so by utilising PowerShell cmdlets. 

The script provides a wrapper around `subprocess.Popen` in order to interact
continuously with a single PowerShell session. In order to do this, it creates
a new file, `stdout.tmp`, which will hold input and output send to the 
PowerShell. This is done such that the `readlines` function can be used, without
blocking on lack of output. The `PowerShellSession` class provides a 
send_cmd function, as well as a close function which should be called, once the
session has ended.

### Usage

The script will prompt the user for a user and password. These are used to
log in to both Exchange Online and SharePoint Online. Once prompted it will
retrieve all the contacts in both Exchange Online and the SharePoint list.
It will update the contacts, such that after running Exchange Online contacts
is equal to the SharePoint list.

### Dependencies

In order to run this script, the [Get-SPObject cmdlet](https://gallery.technet.microsoft.com/office/Module-for-getting-4495a978) needs to be available, 
such that they can be imported, during the execution of the script.

