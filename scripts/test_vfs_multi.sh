#!/bin/sh
# Этап 3: VFS с несколькими файлами в корне (включая двоичный).
. "$(dirname "$0")/common.sh"
build_vfs multi

title "VFS с несколькими файлами: motd и статистика"
emulate --vfs build/multi.zip </dev/null

title "Стартовый скрипт этапа 3 (в конце vfs-init)"
emulate --vfs build/multi.zip --script startup/stage3.txt </dev/null

title "Повторный запуск: архив очищен командой vfs-init"
emulate --vfs build/multi.zip </dev/null
