Output docs/demo.gif
Set Shell "bash"
Set FontSize 18
Set Width 1360
Set Height 840
Set Framerate 10
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms
Hide
Type "export PS1='$ '; mkdir -p .work/demo; cp examples/*.xmp .work/demo/; cd .work/demo; rm -f report.json; clear"
Enter
Sleep 500ms
Type "preset-overlap "
Show
Type "color.xmp grain.xmp finish.xmp --json report.json"
Enter
Sleep 16s
