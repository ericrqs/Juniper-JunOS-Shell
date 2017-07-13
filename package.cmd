mkdir juniper_junos_shell\pkg
mkdir juniper_junos_shell\pkg\Configuration
mkdir juniper_junos_shell\pkg\DataModel

copy juniper_junos_shell\Configuration\shellconfig.xml juniper_junos_shell\pkg\Configuration
copy juniper_junos_shell\DataModel\datamodel.xml       juniper_junos_shell\pkg\DataModel
copy juniper_junos_shell\metadata.xml                  juniper_junos_shell\pkg

mkdir "juniper_junos_shell\pkg\Resource Drivers - Python"

cd "juniper_junos_shell\Resource Drivers - Python\Generic Juniper JunOS Driver Version3"
set fn="..\..\pkg\Resource Drivers - Python\Generic Juniper JunOS Driver Version3.zip"
"c:\Program Files\7-Zip\7z.exe" a %fn% *
cd ..\..\..

cd "juniper_junos_shell\Resource Drivers - Python\Generic Juniper JunOS Firewall Driver Version1"
set fn="..\..\pkg\Resource Drivers - Python\Generic Juniper JunOS Firewall Driver Version1.zip"
"c:\Program Files\7-Zip\7z.exe" a %fn% *
cd ..\..\..

cd juniper_junos_shell\pkg
set fn="..\..\JunOS Package.zip"
del %fn%
"c:\Program Files\7-Zip\7z.exe" a %fn% *
cd ..\..

rmdir /s /q juniper_junos_shell\pkg
