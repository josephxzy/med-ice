#!/usr/bin/env python3
"""Patch rime_api_console.cc to use process_key instead of simulate_key_sequence.

simulate_key_sequence is deprecated and broken in librime >= 1.16.
This script replaces it with a custom key sequence parser that calls
process_key for each key event.
"""
import sys


PATCH_FUNC = r"""static bool process_key_sequence(RimeApi* rime, RimeSessionId session_id, const char* seq) {
  const char* p = seq;
  while (*p) {
    int keycode = 0, mask = 0;
    if (*p == '{') {
      const char* end = strchr(++p, '}');
      if (!end) { fprintf(stderr, "unmatched '}'\n"); return false; }
      char buf[256];
      size_t len = end - p;
      if (len >= sizeof(buf)) len = sizeof(buf) - 1;
      memcpy(buf, p, len);
      buf[len] = '\0';
      char* keyname = buf;
      char* plus;
      while ((plus = strchr(keyname, '+'))) {
        *plus = '\0';
        int m = RimeGetModifierByName(keyname);
        if (!m) { fprintf(stderr, "unknown modifier '%s'\n", keyname); return false; }
        mask |= m;
        keyname = plus + 1;
      }
      keycode = RimeGetKeycodeByName(keyname);
      if (!keycode) { fprintf(stderr, "unknown key '%s'\n", keyname); return false; }
      p = end + 1;
    } else {
      keycode = (unsigned char)*p;
      p++;
    }
    if (!rime->process_key(session_id, keycode, mask))
      return false;
  }
  return true;
}

"""


def main():
    if len(sys.argv) < 2:
        print("Usage: patch_api_console.py <rime_api_console.cc>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, 'r') as f:
        content = f.read()

    # add include
    content = content.replace(
        '#include "line_editor.h"',
        '#include "line_editor.h"\n#include "rime/key_table.h"'
    )

    # insert new function before main
    content = content.replace(
        'int main(int argc, char* argv[]) {',
        PATCH_FUNC + 'int main(int argc, char* argv[]) {'
    )

    # replace call site
    content = content.replace(
        'rime->simulate_key_sequence(session_id, line.c_str())',
        'process_key_sequence(rime, session_id, line.c_str())'
    )

    with open(path, 'w') as f:
        f.write(content)

    print("Patched rime_api_console.cc: simulate_key_sequence -> process_key")


if __name__ == '__main__':
    main()
