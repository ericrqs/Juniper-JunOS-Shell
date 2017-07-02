mkdir pkg
mkdir pkg\Configuration
mkdir pkg\DataModel

copy Configuration\shellconfig.xml pkg\Configuration
copy DataModel\datamodel.xml pkg\DataModel
copy metadata.xml pkg

mkdir "pkg\Resource Drivers - Python"

cd "Resource Drivers - Python\Generic Juniper JunOS Driver Version3"
set fn="..\..\pkg\Resource Drivers - Python\Generic Juniper JunOS Driver Version3.zip"
"c:\Program Files\7-Zip\7z.exe" a %fn% *
cd ..\..

cd "Resource Drivers - Python\Generic Juniper JunOS Firewall Driver Version1"
set fn="..\..\pkg\Resource Drivers - Python\Generic Juniper JunOS Firewall Driver Version1.zip"
"c:\Program Files\7-Zip\7z.exe" a %fn% *
cd ..\..

cd pkg
set fn="..\JunOS Package.zip"
del %fn%
"c:\Program Files\7-Zip\7z.exe" a %fn% *
cd ..

rmdir /s /q pkg
