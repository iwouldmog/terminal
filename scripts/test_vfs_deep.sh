#!/bin/sh
# Этап 3: VFS с вложенностью каталогов не менее 3 уровней.
. "$(dirname "$0")/common.sh"
build_vfs deep

title "Глубокая VFS: motd и статистика"
emulate --vfs build/deep.zip </dev/null

title "Стартовый скрипт этапа 3 (в конце vfs-init)"
emulate --vfs build/deep.zip --script startup/stage3.txt </dev/null

title "Повторный запуск: архив очищен командой vfs-init"
emulate --vfs build/deep.zip </dev/null
