
set PVBDIR=C:\pvb
set MINGWDIR=C:\Qt\Tools\mingw492_32
set QTDIR=C:\Qt\5.5\mingw492_32

set LIBXML2DIR=C:\Data\PVB\pvbaddon\foreign\libxml2
set CSOAPDIR=C:\Data\PVB\pvbaddon\foreign\csoap\libsoap-1.1.0

Rem set OPENSSLDIR=Z:\temp\win\openssl-0.9.7e.win32

set PATH=%PVBDIR%\win-mingw\bin;%MINGWDIR%\bin;%QTDIR%\bin;c:\windows;c:\windows\system32

qmake opcxmlda_client.pro -o Makefile.win
mingw32-make -f Makefile.win

