// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Yukishiro; adapted from Meltype Mozc helper.
#pragma once
#ifdef __cplusplus
extern "C" {
#endif
/* Serialized calls on the Fcitx event thread. Absolute writable private profile.
 * Repeated init with same profile succeeds; a different profile fails until shutdown.
 * Result strings are UTF-8 NUL and malloc-owned; caller/core frees them.
 * NULL indicates failure/empty input/uninitialized state. No exceptions escape.
 * Mozc learning is not exposed by the existing core callbacks. */
int meltype_mozc_bridge_init(const char *profile_absolute);
void meltype_mozc_bridge_shutdown(void);
char *meltype_mozc_clauses(const char *reading, const char *context);
char *meltype_mozc_candidates(const char *reading);
char *meltype_mozc_predictions(const char *reading);
#ifdef __cplusplus
}
#endif
