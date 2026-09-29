#!/bin/sh
# Этап 3: минимальная VFS (только файл motd) и VFS по умолчанию.
. "$(dirname "$0")/common.sh"
build_vfs minimal

title "VFS по умолчанию (без --vfs): пустая, без motd"
printf 'vfs-init\nexit\n' | emulate

title "Минимальная VFS: при старте выводится motd"
emulate --vfs build/minimal.zip </dev/null

title "Стартовый скрипт этапа 3 (в конце vfs-init)"
emulate --vfs build/minimal.zip --script startup/stage3.txt </dev/null

title "Повторный запуск: архив очищен командой vfs-init"
emulate --vfs build/minimal.zip </dev/null
