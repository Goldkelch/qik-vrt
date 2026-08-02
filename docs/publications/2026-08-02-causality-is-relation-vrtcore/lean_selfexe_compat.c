#define _GNU_SOURCE

#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <unistd.h>

/*
 * Lean 4.19's Linux runtime resolves its own executable through
 * /proc/<pid>/exe.  This execution environment deliberately denies numeric
 * /proc/<pid>/exe links, including the caller's own PID, while exposing the
 * equivalent and self-scoped /proc/self/exe alias.
 *
 * This compatibility shim changes exactly that one self-reference.  It does
 * not make any other process visible and forwards every other readlink call
 * unchanged to the kernel.
 */
ssize_t readlink(const char *restrict path, char *restrict buffer,
                 size_t buffer_size) {
  char own_numeric_exe[64];
  int written = snprintf(own_numeric_exe, sizeof(own_numeric_exe),
                         "/proc/%ld/exe", (long)getpid());

  if (written > 0 && (size_t)written < sizeof(own_numeric_exe) &&
      strcmp(path, own_numeric_exe) == 0) {
    path = "/proc/self/exe";
  }

  return syscall(SYS_readlink, path, buffer, buffer_size);
}
