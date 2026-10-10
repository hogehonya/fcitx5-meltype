// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Yukishiro; adapted from Meltype Exports.cs.
#pragma once
#ifdef __cplusplus
extern "C" {
#endif
/* UTF-8 NUL strings; callbacks return malloc memory freed by core.
 * Core results must be released by meltype_free. Serialized Fcitx thread only.
 * Session handles belong to core; destroy once, never use after destruction. */
int meltype_init(char *(*clauses)(const char *, const char *), char *(*candidates)(const char *), int (*is_word)(const char *));
void meltype_set_prediction_callback(char *(*predictions)(const char *));
int meltype_init_mozc(const char *helper, const char *profile);
int meltype_set_data_directory(const char *absolute_path);
void *meltype_create(void);
void meltype_destroy(void *session);
char *meltype_handle_key(void *session, int vk, int ch, int modifiers, const char *before, const char *after);
char *meltype_commit(void *session);
char *meltype_select_candidate(void *session, int index);
void meltype_set_direct(void *session, int direct);
char *meltype_data_directory(void);
char *meltype_report_url(const char *platform);
void meltype_free(void *result);
#ifdef __cplusplus
}
#endif
