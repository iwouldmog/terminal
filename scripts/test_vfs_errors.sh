#!/bin/sh
# Этап 3: ошибки загрузки VFS и выполнения vfs-init.
. "$(dirname "$0")/common.sh"
build_vfs minimal

title "Архив VFS не существует"
emulate --vfs build/missing.zip --script startup/stage3.txt </dev/null

title "Путь к VFS является каталогом"
emulate --vfs vfs/minimal --script startup/stage3.txt </dev/null

title "Файл VFS не является ZIP-архивом"
emulate --vfs README.md --script startup/stage3.txt </dev/null

title "vfs-init не может перезаписать архив (только чтение)"
chmod a-w build/minimal.zip
printf 'vfs-init\nexit\n' | emulate --vfs build/minimal.zip
chmod u+w build/minimal.zip
