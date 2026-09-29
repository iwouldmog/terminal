#!/bin/sh
# Этап 2: выполнение стартовых скриптов с разными VFS.
. "$(dirname "$0")/common.sh"
for name in minimal multi deep; do build_vfs "$name"; done

title "Скрипт с ошибками выполняется полностью, затем диалог"
printf 'exit 0\n' | emulate --vfs build/minimal.zip \
    --script startup/stage2.txt

title "Команда exit в скрипте завершает эмулятор с кодом 42"
emulate --vfs build/deep.zip --script startup/stage2_exit.txt </dev/null

title "Скрипт без exit: конец ввода завершает эмулятор"
emulate --vfs build/multi.zip --script startup/stage2.txt </dev/null
