del /F /Q wix-installer\bin\*
del /F /Q wix-installer\obj\*
del /F /Q wix-installer\Files.wxs
"%WIX%bin\heat" dir ".\dist\modern_relay" -srd -gg -sfrag -cg PublishedComponents -dr INSTALLFOLDER -template fragment -t ".\wix-installer\RemoveFiles.xslt" -o ".\wix-installer\Files.wxs"
"%WIX%bin\candle" -ext WixUtilExtension -arch x64 wix-installer\*.wxs -o wix-installer\obj\
"%WIX%bin\light" -b ".\dist\modern_relay" -ext WixUIExtension -ext WixUtilExtension -cultures:en-us -loc wix-installer\Localization.wsl wix-installer\obj\*.wixobj -o wix-installer\bin\Installer.msi
